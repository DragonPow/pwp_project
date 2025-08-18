# Copyright (c) 2025, Government Agency and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import hashlib
import binascii
from datetime import datetime, timedelta
from electronic_office.electronic_office.doctype.digital_signature.digital_signature import DigitalSignature

class UserCryptoKeys(Document):
    def validate(self):
        self.set_key_generation_date()
        self.calculate_key_fingerprint()
        self.validate_key_expiration()
        
    def before_save(self):
        self.update_key_status()
        
    def on_update(self):
        self.update_user_key_reference()
        
    def set_key_generation_date(self):
        if not self.key_generation_date:
            self.key_generation_date = frappe.utils.now()
            
    def calculate_key_fingerprint(self):
        if self.public_key and not self.key_fingerprint:
            try:
                # Calculate SHA-256 hash of the public key
                public_key_bytes = self.public_key.encode('utf-8')
                hash_object = hashlib.sha256(public_key_bytes)
                fingerprint = hash_object.hexdigest()
                
                # Format as colon-separated groups of 4 characters
                self.key_fingerprint = ':'.join([fingerprint[i:i+4] for i in range(0, len(fingerprint), 4)])
            except Exception as e:
                frappe.log_error(f"Key fingerprint calculation failed: {str(e)}", "User Crypto Keys")
                
    def validate_key_expiration(self):
        if self.key_expiration_date:
            expiration_date = frappe.utils.getdate(self.key_expiration_date)
            current_date = frappe.utils.getdate()
            
            if expiration_date < current_date:
                self.key_status = "Expired"
                
    def update_key_status(self):
        if self.key_status == "Active" and self.key_expiration_date:
            expiration_date = frappe.utils.getdate(self.key_expiration_date)
            current_date = frappe.utils.getdate()
            
            if expiration_date < current_date:
                self.key_status = "Expired"
                
    def update_user_key_reference(self):
        # Update the last used date
        self.last_used_date = frappe.utils.now()
        
    def revoke_keys(self, reason=""):
        """
        Revoke the cryptographic keys
        """
        self.key_status = "Revoked"
        self.save()
        
        # Log the revocation
        frappe.get_doc({
            "doctype": "Audit Log",
            "action": "Keys Revoked",
            "performed_by": frappe.session.user,
            "performed_on": frappe.utils.now(),
            "details": f"Cryptographic keys for user {self.user} were revoked. Reason: {reason}",
            "ip_address": frappe.local.request_ip if hasattr(frappe.local, 'request_ip') else "",
            "user_agent": frappe.local.request.headers.get('User-Agent') if hasattr(frappe.local, 'request') and hasattr(frappe.local.request, 'headers') else ""
        }).insert(ignore_permissions=True)
        
    def rotate_keys(self, new_key_algorithm=None, new_key_size=None, new_curve=None, password=None):
        """
        Rotate the cryptographic keys by generating new ones
        """
        try:
            # Determine algorithm parameters
            algorithm = new_key_algorithm or self.key_algorithm or "RSA"
            
            if algorithm == "RSA":
                key_size = new_key_size or self.key_size or 2048
                private_key_pem, public_key_pem = DigitalSignature.generate_rsa_key_pair(key_size)
            elif algorithm == "ECDSA":
                curve = new_curve or self.curve or "secp256r1"
                private_key_pem, public_key_pem = DigitalSignature.generate_ecdsa_key_pair(curve)
            else:
                raise ValueError(f"Unsupported algorithm: {algorithm}")
            
            # Encrypt private key if password is provided
            if password:
                private_key_pem = DigitalSignature.encrypt_private_key(private_key_pem, password)
                self.private_key_encrypted = 1
            else:
                self.private_key_encrypted = 0
            
            # Update keys
            self.private_key = private_key_pem
            self.public_key = public_key_pem
            self.key_algorithm = algorithm
            self.key_size = key_size if algorithm == "RSA" else None
            self.curve = curve if algorithm == "ECDSA" else None
            self.key_generation_date = frappe.utils.now()
            self.key_status = "Active"
            
            # Set expiration date (default to 2 years from now)
            if not self.key_expiration_date:
                self.key_expiration_date = (datetime.now() + timedelta(days=730)).strftime("%Y-%m-%d")
            
            self.save()
            
            # Log the key rotation
            frappe.get_doc({
                "doctype": "Audit Log",
                "action": "Keys Rotated",
                "performed_by": frappe.session.user,
                "performed_on": frappe.utils.now(),
                "details": f"Cryptographic keys for user {self.user} were rotated. New algorithm: {algorithm}",
                "ip_address": frappe.local.request_ip if hasattr(frappe.local, 'request_ip') else "",
                "user_agent": frappe.local.request.headers.get('User-Agent') if hasattr(frappe.local, 'request') and hasattr(frappe.local.request, 'headers') else ""
            }).insert(ignore_permissions=True)
            
            return True
            
        except Exception as e:
            frappe.log_error(f"Key rotation failed: {str(e)}", "User Crypto Keys")
            raise frappe.ValidationError(f"Failed to rotate keys: {str(e)}")
            
    @staticmethod
    def get_user_keys(user_id):
        """
        Get cryptographic keys for a user
        """
        try:
            keys = frappe.get_doc("User Crypto Keys", user_id)
            return keys
        except frappe.DoesNotExist:
            return None
            
    @staticmethod
    def get_user_public_key(user_id):
        """
        Get user's public key
        """
        keys = UserCryptoKeys.get_user_keys(user_id)
        if keys:
            return keys.public_key
        return None
        
    @staticmethod
    def get_user_private_key(user_id, password=None):
        """
        Get user's private key, decrypting if necessary
        """
        keys = UserCryptoKeys.get_user_keys(user_id)
        if not keys:
            raise ValueError("Cryptographic keys not found for user")
        
        if keys.private_key_encrypted and not password:
            raise ValueError("Password required to decrypt private key")
        
        if keys.private_key_encrypted:
            return DigitalSignature.decrypt_private_key(keys.private_key, password)
        else:
            return keys.private_key
            
    @staticmethod
    def store_user_keys(user_id, private_key_pem, public_key_pem, password=None):
        """
        Store user's cryptographic keys
        """
        try:
            # Check if keys already exist for the user
            if frappe.db.exists("User Crypto Keys", user_id):
                keys = frappe.get_doc("User Crypto Keys", user_id)
            else:
                keys = frappe.new_doc("User Crypto Keys")
                keys.user = user_id
            
            # Encrypt private key if password is provided
            if password:
                private_key_pem = DigitalSignature.encrypt_private_key(private_key_pem, password)
                keys.private_key_encrypted = 1
            else:
                keys.private_key_encrypted = 0
            
            # Store keys
            keys.private_key = private_key_pem
            keys.public_key = public_key_pem
            keys.key_generation_date = frappe.utils.now()
            keys.key_status = "Active"
            
            # Set expiration date (default to 2 years from now)
            if not keys.key_expiration_date:
                keys.key_expiration_date = (datetime.now() + timedelta(days=730)).strftime("%Y-%m-%d")
            
            keys.save()
            
            return True
            
        except Exception as e:
            frappe.log_error(f"User key storage failed: {str(e)}", "User Crypto Keys")
            raise frappe.ValidationError(f"Failed to store user keys: {str(e)}")
            
    @staticmethod
    def generate_and_store_user_keys(user_id, algorithm='RSA', key_size=2048, curve='secp256r1', password=None):
        """
        Generate and store cryptographic keys for a user
        """
        try:
            # Generate key pair
            if algorithm.upper() == 'RSA':
                private_key_pem, public_key_pem = DigitalSignature.generate_rsa_key_pair(key_size)
            elif algorithm.upper() == 'ECDSA':
                private_key_pem, public_key_pem = DigitalSignature.generate_ecdsa_key_pair(curve)
            else:
                raise ValueError(f"Unsupported algorithm: {algorithm}")
            
            # Store keys
            UserCryptoKeys.store_user_keys(user_id, private_key_pem, public_key_pem, password)
            
            return True
            
        except Exception as e:
            frappe.log_error(f"User key generation and storage failed: {str(e)}", "User Crypto Keys")
            raise frappe.ValidationError(f"Failed to generate and store user keys: {str(e)}")