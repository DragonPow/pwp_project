# Copyright (c) 2025, Government Agency and contributors
# For license information, please see license.txt

import frappe
from electronic_office.electronic_office.doctype.user_crypto_keys.user_crypto_keys import UserCryptoKeys

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
        
        public_key = UserCryptoKeys.get_user_public_key(user_id)
        
        if not public_key:
            frappe.throw(_("Public key not found for user {0}").format(user_id))
        
        return {
            "status": "success",
            "public_key": public_key
        }
        
    except Exception as e:
        frappe.log_error(f"Public key retrieval failed: {str(e)}", "User Crypto Keys API")
        frappe.throw(_("Failed to retrieve public key: {0}").format(str(e)))

@frappe.whitelist()
def generate_and_store_user_keys(user_id=None, algorithm='RSA', key_size=2048, curve='secp256r1', password=None):
    """
    Generate and store cryptographic keys for a user
    """
    try:
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
        
    except Exception as e:
        frappe.log_error(f"Key generation and storage failed: {str(e)}", "User Crypto Keys API")
        frappe.throw(_("Failed to generate and store keys: {0}").format(str(e)))

@frappe.whitelist()
def rotate_user_keys(user_id=None, new_key_algorithm=None, new_key_size=None, new_curve=None, password=None):
    """
    Rotate a user's cryptographic keys
    """
    try:
        if not user_id:
            user_id = frappe.session.user
        
        # Check if user has permission to manage keys
        if user_id != frappe.session.user and not frappe.has_role("System Manager"):
            frappe.throw(_("Not permitted to manage keys for other users"))
        
        keys = UserCryptoKeys.get_user_keys(user_id)
        if not keys:
            frappe.throw(_("Cryptographic keys not found for user {0}").format(user_id))
        
        keys.rotate_keys(new_key_algorithm, new_key_size, new_curve, password)
        
        return {
            "status": "success",
            "message": _("Keys rotated successfully")
        }
        
    except Exception as e:
        frappe.log_error(f"Key rotation failed: {str(e)}", "User Crypto Keys API")
        frappe.throw(_("Failed to rotate keys: {0}").format(str(e)))

@frappe.whitelist()
def revoke_user_keys(user_id=None, reason=""):
    """
    Revoke a user's cryptographic keys
    """
    try:
        if not user_id:
            user_id = frappe.session.user
        
        # Check if user has permission to manage keys
        if user_id != frappe.session.user and not frappe.has_role("System Manager"):
            frappe.throw(_("Not permitted to manage keys for other users"))
        
        keys = UserCryptoKeys.get_user_keys(user_id)
        if not keys:
            frappe.throw(_("Cryptographic keys not found for user {0}").format(user_id))
        
        keys.revoke_keys(reason)
        
        return {
            "status": "success",
            "message": _("Keys revoked successfully")
        }
        
    except Exception as e:
        frappe.log_error(f"Key revocation failed: {str(e)}", "User Crypto Keys API")
        frappe.throw(_("Failed to revoke keys: {0}").format(str(e)))