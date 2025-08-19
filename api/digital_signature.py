# Copyright (c) 2025, Government Agency and contributors
# For license information, please see license.txt

import frappe
import json
import base64
from frappe import _
from pwp_project.pwp_project.doctype.digital_signature.digital_signature import DigitalSignature

@frappe.whitelist()
def generate_key_pair(algorithm='RSA', key_size=2048, curve='secp256r1', password=None):
    """
    Generate a new key pair for digital signatures
    """
    try:
        from pwp_project.pwp_project.doctype.user_crypto_keys.user_crypto_keys import UserCryptoKeys

        if algorithm.upper() == 'RSA':
            private_key_pem, public_key_pem = DigitalSignature.generate_rsa_key_pair(key_size)
        elif algorithm.upper() == 'ECDSA':
            private_key_pem, public_key_pem = DigitalSignature.generate_ecdsa_key_pair(curve)
        else:
            frappe.throw(_("Unsupported algorithm: {0}").format(algorithm))

        # Store keys for the current user
        user_id = frappe.session.user
        UserCryptoKeys.store_user_keys(user_id, private_key_pem, public_key_pem, password)

        return {
            "status": "success",
            "message": _("Key pair generated successfully"),
            "public_key": public_key_pem
        }

    except Exception as e:
        frappe.log_error(f"Key pair generation failed: {str(e)}", "Digital Signature API")
        frappe.throw(_("Failed to generate key pair: {0}").format(str(e)))

@frappe.whitelist()
def sign_document(document_name, document_version=None, algorithm='RSA', password=None):
    """
    Sign a document with the user's private key
    """
    try:
        # Check if user has permission to read this document
        if not frappe.has_permission("Document", "read", document_name):
            frappe.throw(_("Not permitted to read document: {0}").format(document_name))

        # Get user's private key
        user_id = frappe.session.user
        from pwp_project.pwp_project.doctype.user_crypto_keys.user_crypto_keys import UserCryptoKeys
        private_key_pem = UserCryptoKeys.get_user_private_key(user_id, password)

        # Create digital signature record
        signature_doc = frappe.get_doc({
            "doctype": "Digital Signature",
            "document": document_name,
            "document_version": document_version,
            "signature_provider": "Internal",
            "verification_status": "Pending"
        })
        signature_doc.insert()

        # Sign the document
        signature_metadata = signature_doc.sign_document(private_key_pem, algorithm, password)

        # Save the signature
        signature_doc.save()

        return {
            "status": "success",
            "message": _("Document signed successfully"),
            "signature": signature_doc.name,
            "signature_metadata": signature_metadata
        }

    except Exception as e:
        frappe.log_error(f"Document signing failed: {str(e)}", "Digital Signature API")
        frappe.throw(_("Failed to sign document: {0}").format(str(e)))

@frappe.whitelist()
def verify_signature(signature_name):
    """
    Verify a digital signature
    """
    try:
        # Get the signature document
        signature_doc = frappe.get_doc("Digital Signature", signature_name)

        # Check if user has permission to read this document
        if not frappe.has_permission("Document", "read", signature_doc.document):
            frappe.throw(_("Not permitted to read document: {0}").format(signature_doc.document))

        # Verify the signature
        signature_doc.verify_signature()

        return {
            "status": "success",
            "message": _("Signature verification completed"),
            "verification_status": signature_doc.verification_status
        }

    except Exception as e:
        frappe.log_error(f"Signature verification failed: {str(e)}", "Digital Signature API")
        frappe.throw(_("Failed to verify signature: {0}").format(str(e)))

@frappe.whitelist()
def get_user_public_key(user_id=None):
    """
    Get a user's public key
    """
    try:
        if not user_id:
            user_id = frappe.session.user

        # Check if user has permission to read user profiles
        if user_id != frappe.session.user and not frappe.has_role("System Manager"):
            frappe.throw(_("Not permitted to access other users' public keys"))

        from pwp_project.pwp_project.doctype.user_crypto_keys.user_crypto_keys import UserCryptoKeys
        public_key_pem = UserCryptoKeys.get_user_public_key(user_id)

        return {
            "status": "success",
            "public_key": public_key_pem
        }

    except Exception as e:
        frappe.log_error(f"Public key retrieval failed: {str(e)}", "Digital Signature API")
        frappe.throw(_("Failed to retrieve public key: {0}").format(str(e)))

@frappe.whitelist()
def get_document_signatures(document_name):
    """
    Get all signatures for a document
    """
    try:
        # Check if user has permission to read this document
        if not frappe.has_permission("Document", "read", document_name):
            frappe.throw(_("Not permitted to read document: {0}").format(document_name))

        # Get all signatures for the document
        signatures = frappe.get_all("Digital Signature",
            filters={"document": document_name},
            fields=["name", "signed_by", "signed_on", "verification_status", "signature_provider"],
            order_by="signed_on desc"
        )

        return {
            "status": "success",
            "signatures": signatures
        }

    except Exception as e:
        frappe.log_error(f"Signature retrieval failed: {str(e)}", "Digital Signature API")
        frappe.throw(_("Failed to retrieve signatures: {0}").format(str(e)))

@frappe.whitelist()
def revoke_signature(signature_name, reason=""):
    """
    Revoke a digital signature
    """
    try:
        # Get the signature document
        signature_doc = frappe.get_doc("Digital Signature", signature_name)

        # Check if user has permission to write this document
        if not frappe.has_permission("Document", "write", signature_doc.document):
            frappe.throw(_("Not permitted to update document: {0}").format(signature_doc.document))

        # Only the signer or a system manager can revoke a signature
        if signature_doc.signed_by != frappe.session.user and not frappe.has_role("System Manager"):
            frappe.throw(_("Not permitted to revoke this signature"))

        # Revoke the signature
        signature_doc.revoke_signature(reason)

        return {
            "status": "success",
            "message": _("Signature revoked successfully")
        }

    except Exception as e:
        frappe.log_error(f"Signature revocation failed: {str(e)}", "Digital Signature API")
        frappe.throw(_("Failed to revoke signature: {0}").format(str(e)))

@frappe.whitelist()
def verify_external_signature(document_name, signature_data, certificate_info):
    """
    Verify an external digital signature
    """
    try:
        # Check if user has permission to read this document
        if not frappe.has_permission("Document", "read", document_name):
            frappe.throw(_("Not permitted to read document: {0}").format(document_name))

        # Create digital signature record for external signature
        signature_doc = frappe.get_doc({
            "doctype": "Digital Signature",
            "document": document_name,
            "signature_provider": "External",
            "signature_data": signature_data,
            "certificate_info": certificate_info,
            "verification_status": "Pending"
        })
        signature_doc.insert()

        # Verify the signature
        signature_doc.verify_signature()

        return {
            "status": "success",
            "message": _("External signature verification completed"),
            "signature": signature_doc.name,
            "verification_status": signature_doc.verification_status
        }

    except Exception as e:
        frappe.log_error(f"External signature verification failed: {str(e)}", "Digital Signature API")
        frappe.throw(_("Failed to verify external signature: {0}").format(str(e)))
