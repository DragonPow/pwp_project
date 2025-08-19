# Copyright (c) 2025, Government Agency and contributors
# For license information, please see license.txt

import frappe
from pwp_project.pwp_project.doctype.digital_signature.digital_signature import DigitalSignature
from pwp_project.pwp_project.doctype.user_crypto_keys.user_crypto_keys import UserCryptoKeys

@frappe.whitelist()
def generate_rsa_key_pair(key_size=2048):
    """
    Generate RSA key pair for digital signatures
    """
    return DigitalSignature.generate_rsa_key_pair(key_size)

@frappe.whitelist()
def generate_ecdsa_key_pair(curve='secp256r1'):
    """
    Generate ECDSA key pair for digital signatures
    """
    return DigitalSignature.generate_ecdsa_key_pair(curve)

@frappe.whitelist()
def sign_data_rsa(private_key_pem, data, password=None):
    """
    Sign data using RSA private key
    """
    return DigitalSignature.sign_data_rsa(private_key_pem, data, password)

@frappe.whitelist()
def sign_data_ecdsa(private_key_pem, data, password=None):
    """
    Sign data using ECDSA private key
    """
    return DigitalSignature.sign_data_ecdsa(private_key_pem, data, password)

@frappe.whitelist()
def verify_signature_rsa(public_key_pem, data, signature_b64):
    """
    Verify RSA signature
    """
    return DigitalSignature.verify_signature_rsa(public_key_pem, data, signature_b64)

@frappe.whitelist()
def verify_signature_ecdsa(public_key_pem, data, signature_b64):
    """
    Verify ECDSA signature
    """
    return DigitalSignature.verify_signature_ecdsa(public_key_pem, data, signature_b64)

@frappe.whitelist()
def create_document_signature(private_key_pem, document_content, algorithm='RSA', password=None):
    """
    Create a digital signature for document content
    """
    return DigitalSignature.create_document_signature(private_key_pem, document_content, algorithm, password)

@frappe.whitelist()
def verify_document_signature(public_key_pem, document_content, signature_metadata):
    """
    Verify a document signature
    """
    return DigitalSignature.verify_document_signature(public_key_pem, document_content, signature_metadata)

@frappe.whitelist()
def get_user_public_key(user_id=None):
    """
    Get a user's public key
    """
    if not user_id:
        user_id = frappe.session.user

    # Check if user has permission to read user profiles
    if user_id != frappe.session.user and not frappe.has_role("System Manager"):
        frappe.throw(_("Not permitted to access other users' public keys"))

    public_key = UserCryptoKeys.get_user_public_key(user_id)

    if not public_key:
        frappe.throw(_("Public key not found for user {0}").format(user_id))

    return {
        "status": "success",
        "public_key": public_key
    }

@frappe.whitelist()
def generate_and_store_user_keys(user_id=None, algorithm='RSA', key_size=2048, curve='secp256r1', password=None):
    """
    Generate and store cryptographic keys for a user
    """
    if not user_id:
        user_id = frappe.session.user

    # Check if user has permission to manage keys
    if user_id != frappe.session.user and not frappe.has_role("System Manager"):
        frappe.throw(_("Not permitted to manage keys for other users"))

    UserCryptoKeys.generate_and_store_user_keys(user_id, algorithm, key_size, curve, password)

    return {
        "status": "success",
        "message": _("Keys generated and stored successfully")
    }
