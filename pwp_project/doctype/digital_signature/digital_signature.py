# Copyright (c) 2025, Government Agency and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import json
import base64
import hashlib
import os
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import utils
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import binascii
import datetime

class DigitalSignature(Document):
    def validate(self):
        self.set_signed_fields()
        self.validate_document_version()
        self.validate_signature_data()

    def before_save(self):
        self.auto_verify_signature()

    def on_update(self):
        self.create_audit_log("Updated")
        self.update_document_status()

    def on_trash(self):
        self.create_audit_log("Deleted")

    @staticmethod
    def generate_rsa_key_pair(key_size=2048):
        """
        Generate RSA key pair for digital signatures
        Returns: tuple (private_key_pem, public_key_pem)
        """
        try:
            # Generate private key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=key_size,
                backend=default_backend()
            )

            # Serialize private key to PEM format
            private_key_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )

            # Serialize public key to PEM format
            public_key_pem = private_key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )

            return private_key_pem.decode('utf-8'), public_key_pem.decode('utf-8')

        except Exception as e:
            frappe.log_error(f"RSA key pair generation failed: {str(e)}", "Digital Signature Key Generation")
            raise frappe.ValidationError(f"Failed to generate RSA key pair: {str(e)}")

    @staticmethod
    def generate_ecdsa_key_pair(curve='secp256r1'):
        """
        Generate ECDSA key pair for digital signatures
        Returns: tuple (private_key_pem, public_key_pem)
        """
        try:
            from cryptography.hazmat.primitives.asymmetric import ec

            # Map curve names to cryptography curve objects
            curve_map = {
                'secp256r1': ec.SECP256R1(),
                'secp384r1': ec.SECP384R1(),
                'secp521r1': ec.SECP521R1(),
                'secp256k1': ec.SECP256K1()
            }

            if curve not in curve_map:
                raise ValueError(f"Unsupported curve: {curve}")

            # Generate private key
            private_key = ec.generate_private_key(
                curve_map[curve],
                default_backend()
            )

            # Serialize private key to PEM format
            private_key_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )

            # Serialize public key to PEM format
            public_key_pem = private_key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )

            return private_key_pem.decode('utf-8'), public_key_pem.decode('utf-8')

        except Exception as e:
            frappe.log_error(f"ECDSA key pair generation failed: {str(e)}", "Digital Signature Key Generation")
            raise frappe.ValidationError(f"Failed to generate ECDSA key pair: {str(e)}")

    @staticmethod
    def load_private_key(private_key_pem, password=None):
        """
        Load private key from PEM format
        """
        try:
            if password:
                password = password.encode('utf-8')

            private_key = serialization.load_pem_private_key(
                private_key_pem.encode('utf-8'),
                password=password,
                backend=default_backend()
            )
            return private_key
        except Exception as e:
            frappe.log_error(f"Private key loading failed: {str(e)}", "Digital Signature Key Loading")
            raise frappe.ValidationError(f"Failed to load private key: {str(e)}")

    @staticmethod
    def load_public_key(public_key_pem):
        """
        Load public key from PEM format
        """
        try:
            public_key = serialization.load_pem_public_key(
                public_key_pem.encode('utf-8'),
                backend=default_backend()
            )
            return public_key
        except Exception as e:
            frappe.log_error(f"Public key loading failed: {str(e)}", "Digital Signature Key Loading")
            raise frappe.ValidationError(f"Failed to load public key: {str(e)}")

    @staticmethod
    def sign_data_rsa(private_key_pem, data, password=None):
        """
        Sign data using RSA private key
        Returns: base64 encoded signature
        """
        try:
            private_key = DigitalSignature.load_private_key(private_key_pem, password)

            # Convert data to bytes if it's a string
            if isinstance(data, str):
                data = data.encode('utf-8')

            # Create signature
            signature = private_key.sign(
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )

            # Return base64 encoded signature
            return base64.b64encode(signature).decode('utf-8')

        except Exception as e:
            frappe.log_error(f"RSA signing failed: {str(e)}", "Digital Signature Signing")
            raise frappe.ValidationError(f"Failed to sign data with RSA: {str(e)}")

    @staticmethod
    def sign_data_ecdsa(private_key_pem, data, password=None):
        """
        Sign data using ECDSA private key
        Returns: base64 encoded signature
        """
        try:
            from cryptography.hazmat.primitives.asymmetric import ec
            private_key = DigitalSignature.load_private_key(private_key_pem, password)

            # Convert data to bytes if it's a string
            if isinstance(data, str):
                data = data.encode('utf-8')

            # Create signature
            signature = private_key.sign(
                data,
                ec.ECDSA(hashes.SHA256())
            )

            # Return base64 encoded signature
            return base64.b64encode(signature).decode('utf-8')

        except Exception as e:
            frappe.log_error(f"ECDSA signing failed: {str(e)}", "Digital Signature Signing")
            raise frappe.ValidationError(f"Failed to sign data with ECDSA: {str(e)}")

    @staticmethod
    def create_document_signature(private_key_pem, document_content, algorithm='RSA', password=None):
        """
        Create a digital signature for document content
        Returns: dict with signature and metadata
        """
        try:
            # Generate document hash
            if isinstance(document_content, str):
                document_hash = hashlib.sha256(document_content.encode('utf-8')).hexdigest()
            else:
                document_hash = hashlib.sha256(document_content).hexdigest()

            # Create signature based on algorithm
            if algorithm.upper() == 'RSA':
                signature = DigitalSignature.sign_data_rsa(private_key_pem, document_hash, password)
            elif algorithm.upper() == 'ECDSA':
                signature = DigitalSignature.sign_data_ecdsa(private_key_pem, document_hash, password)
            else:
                raise ValueError(f"Unsupported algorithm: {algorithm}")

            # Create signature metadata
            signature_metadata = {
                "algorithm": algorithm,
                "document_hash": document_hash,
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "signature": signature
            }

            return signature_metadata

        except Exception as e:
            frappe.log_error(f"Document signature creation failed: {str(e)}", "Digital Signature Creation")
            raise frappe.ValidationError(f"Failed to create document signature: {str(e)}")

    @staticmethod
    def verify_signature_rsa(public_key_pem, data, signature_b64):
        """
        Verify RSA signature
        Returns: boolean (True if valid, False otherwise)
        """
        try:
            public_key = DigitalSignature.load_public_key(public_key_pem)

            # Convert data to bytes if it's a string
            if isinstance(data, str):
                data = data.encode('utf-8')

            # Decode signature from base64
            signature = base64.b64decode(signature_b64)

            # Verify signature
            public_key.verify(
                signature,
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )

            return True

        except InvalidSignature:
            return False
        except Exception as e:
            frappe.log_error(f"RSA signature verification failed: {str(e)}", "Digital Signature Verification")
            raise frappe.ValidationError(f"Failed to verify RSA signature: {str(e)}")

    @staticmethod
    def verify_signature_ecdsa(public_key_pem, data, signature_b64):
        """
        Verify ECDSA signature
        Returns: boolean (True if valid, False otherwise)
        """
        try:
            from cryptography.hazmat.primitives.asymmetric import ec
            public_key = DigitalSignature.load_public_key(public_key_pem)

            # Convert data to bytes if it's a string
            if isinstance(data, str):
                data = data.encode('utf-8')

            # Decode signature from base64
            signature = base64.b64decode(signature_b64)

            # Verify signature
            public_key.verify(
                signature,
                data,
                ec.ECDSA(hashes.SHA256())
            )

            return True

        except InvalidSignature:
            return False
        except Exception as e:
            frappe.log_error(f"ECDSA signature verification failed: {str(e)}", "Digital Signature Verification")
            raise frappe.ValidationError(f"Failed to verify ECDSA signature: {str(e)}")

    @staticmethod
    def verify_document_signature(public_key_pem, document_content, signature_metadata):
        """
        Verify a document signature
        Returns: boolean (True if valid, False otherwise)
        """
        try:
            # Extract signature data
            algorithm = signature_metadata.get("algorithm")
            document_hash = signature_metadata.get("document_hash")
            signature = signature_metadata.get("signature")

            if not all([algorithm, document_hash, signature]):
                raise ValueError("Invalid signature metadata")

            # Verify document hash matches
            if isinstance(document_content, str):
                current_hash = hashlib.sha256(document_content.encode('utf-8')).hexdigest()
            else:
                current_hash = hashlib.sha256(document_content).hexdigest()

            if current_hash != document_hash:
                return False

            # Verify signature based on algorithm
            if algorithm.upper() == 'RSA':
                return DigitalSignature.verify_signature_rsa(public_key_pem, document_hash, signature)
            elif algorithm.upper() == 'ECDSA':
                return DigitalSignature.verify_signature_ecdsa(public_key_pem, document_hash, signature)
            else:
                raise ValueError(f"Unsupported algorithm: {algorithm}")

        except Exception as e:
            frappe.log_error(f"Document signature verification failed: {str(e)}", "Digital Signature Verification")
            raise frappe.ValidationError(f"Failed to verify document signature: {str(e)}")

    def set_signed_fields(self):
        if not self.signed_by:
            self.signed_by = frappe.session.user
        if not self.signed_on:
            self.signed_on = frappe.utils.now()

    def validate_document_version(self):
        if self.document and self.document_version:
            # Verify that the document version belongs to the document
            version_doc = frappe.get_doc("Document Version", self.document_version)
            if version_doc.document != self.document:
                frappe.throw("Document Version does not belong to the specified Document")

    def validate_signature_data(self):
        if self.signature_data:
            try:
                # Try to decode the signature data to ensure it's valid
                if self.signature_provider == "Internal":
                    # For internal signatures, data should be base64 encoded
                    decoded = base64.b64decode(self.signature_data)
                    if not decoded:
                        frappe.throw("Invalid signature data format")
            except Exception as e:
                frappe.throw(f"Invalid signature data: {str(e)}")

    def auto_verify_signature(self):
        if self.verification_status == "Pending" and self.signature_provider == "Internal":
            # Auto-verify internal signatures
            self.verify_signature()

    def verify_signature(self):
        """
        Verify the digital signature using proper cryptographic verification
        """
        try:
            # Get the document and its content
            document = frappe.get_doc("Document", self.document)
            document_content = document.get_file_content() if hasattr(document, 'get_file_content') else str(document)

            # Parse signature data
            try:
                signature_metadata = json.loads(self.signature_data)
            except json.JSONDecodeError:
                # If signature_data is not JSON, try to decode as base64
                try:
                    decoded_signature = base64.b64decode(self.signature_data).decode('utf-8')
                    signature_metadata = json.loads(decoded_signature)
                except:
                    # If all parsing fails, create a simple metadata structure
                    signature_metadata = {
                        "algorithm": "RSA",
                        "document_hash": hashlib.sha256(document_content.encode('utf-8')).hexdigest(),
                        "signature": self.signature_data
                    }

            # Get the public key for verification
            public_key = None
            if self.signature_provider == "Internal":
                # For internal signatures, get the public key from the user's crypto keys
                from pwp_project.pwp_project.doctype.user_crypto_keys.user_crypto_keys import UserCryptoKeys
                public_key = UserCryptoKeys.get_user_public_key(self.signed_by)
                if not public_key:
                    frappe.throw("Public key not found for user")
            elif self.signature_provider == "External":
                # For external signatures, extract public key from certificate info
                if self.certificate_info:
                    try:
                        cert_info = json.loads(self.certificate_info)
                        if 'public_key' in cert_info:
                            public_key = cert_info['public_key']
                    except:
                        pass

                if not public_key:
                    frappe.throw("Public key not found in certificate info")
            else:
                frappe.throw(f"Unsupported signature provider: {self.signature_provider}")

            # Verify the signature
            is_valid = DigitalSignature.verify_document_signature(
                public_key,
                document_content,
                signature_metadata
            )

            if is_valid:
                self.verification_status = "Verified"

                # Update certificate info if needed
                if self.signature_provider == "External" and not self.certificate_info:
                    self.certificate_info = self.extract_certificate_info()
            else:
                self.verification_status = "Failed"

            self.save()

        except Exception as e:
            frappe.log_error(f"Signature verification failed: {str(e)}", "Digital Signature Verification")
            self.verification_status = "Failed"
            self.save()

    def extract_certificate_info(self):
        """
        Extract certificate information from signature data
        """
        try:
            # Try to parse signature data as JSON first
            try:
                signature_metadata = json.loads(self.signature_data)

                # If it contains certificate info, return it
                if 'certificate_info' in signature_metadata:
                    return json.dumps(signature_metadata['certificate_info'])
            except json.JSONDecodeError:
                pass

            # For external signatures, try to extract certificate info
            if self.signature_provider == "External":
                # In a real implementation, this would parse X.509 certificates
                # For now, we'll return a structured certificate info
                return json.dumps({
                    "issuer": "Government Certificate Authority",
                    "subject": self.signed_by,
                    "valid_from": "2025-01-01",
                    "valid_to": "2030-12-31",
                    "serial_number": binascii.hexlify(os.urandom(8)).decode('utf-8'),
                    "signature_algorithm": "SHA256withRSA",
                    "public_key": ""  # Would be extracted from actual certificate
                })
            else:
                # For internal signatures, return minimal info
                return json.dumps({
                    "issuer": "Internal System",
                    "subject": self.signed_by,
                    "valid_from": datetime.datetime.now().strftime("%Y-%m-%d"),
                    "valid_to": (datetime.datetime.now() + datetime.timedelta(days=365)).strftime("%Y-%m-%d"),
                    "serial_number": binascii.hexlify(os.urandom(8)).decode('utf-8')
                })

        except Exception as e:
            frappe.log_error(f"Certificate extraction failed: {str(e)}", "Digital Signature Certificate")
            return ""

    def sign_document(self, private_key_pem, algorithm='RSA', password=None):
        """
        Create a digital signature for the associated document
        Returns: dict with signature metadata
        """
        try:
            # Get the document content
            document = frappe.get_doc("Document", self.document)
            document_content = document.get_file_content() if hasattr(document, 'get_file_content') else str(document)

            # Create the signature
            signature_metadata = DigitalSignature.create_document_signature(
                private_key_pem,
                document_content,
                algorithm,
                password
            )

            # Store the signature data as JSON
            self.signature_data = json.dumps(signature_metadata)

            # Update verification status
            self.verification_status = "Verified"

            # Update certificate info
            if self.signature_provider == "Internal":
                # For internal signatures, store minimal certificate info
                from pwp_project.pwp_project.doctype.user_crypto_keys.user_crypto_keys import UserCryptoKeys
                user_keys = UserCryptoKeys.get_user_keys(self.signed_by)
                key_fingerprint = user_keys.key_fingerprint if user_keys else ""

                self.certificate_info = json.dumps({
                    "issuer": "Internal System",
                    "subject": self.signed_by,
                    "valid_from": datetime.datetime.now().strftime("%Y-%m-%d"),
                    "valid_to": (datetime.datetime.now() + datetime.timedelta(days=365)).strftime("%Y-%m-%d"),
                    "serial_number": binascii.hexlify(os.urandom(8)).decode('utf-8'),
                    "key_fingerprint": key_fingerprint,
                    "algorithm": algorithm
                })

            return signature_metadata

        except Exception as e:
            frappe.log_error(f"Document signing failed: {str(e)}", "Digital Signature Document Signing")
            raise frappe.ValidationError(f"Failed to sign document: {str(e)}")

    def create_audit_log(self, action):
        audit_log = frappe.get_doc({
            "doctype": "Audit Log",
            "document": self.document,
            "action": f"Digital Signature {action}",
            "performed_by": frappe.session.user,
            "performed_on": frappe.utils.now(),
            "details": f"Digital Signature for document {self.document} was {action.lower()} by {self.signed_by}",
            "ip_address": frappe.local.request_ip if hasattr(frappe.local, 'request_ip') else "",
            "user_agent": frappe.local.request.headers.get('User-Agent') if hasattr(frappe.local, 'request') and hasattr(frappe.local.request, 'headers') else ""
        })
        audit_log.insert(ignore_permissions=True)

    def update_document_status(self):
        if self.verification_status == "Verified":
            # Update document status to indicate it has been signed
            document = frappe.get_doc("Document", self.document)
            if document.status != "Published":
                document.status = "Approved"
                document.save()

    def get_document_info(self):
        if self.document:
            return frappe.get_doc("Document", self.document)
        return None

    def get_document_version_info(self):
        if self.document_version:
            return frappe.get_doc("Document Version", self.document_version)
        return None

    def is_valid(self):
        return self.verification_status == "Verified"

    def revoke_signature(self, reason=""):
        self.verification_status = "Failed"
        self.certificate_info = f"REVOKED: {reason}"
        self.save()

        # Create audit log for revocation
        self.create_audit_log("Revoked")

    @staticmethod
    def encrypt_private_key(private_key_pem, password):
        """
        Encrypt a private key with a password for secure storage
        Returns: encrypted private key (base64 encoded)
        """
        try:
            # Generate a random salt
            salt = os.urandom(16)

            # Generate key from password using PBKDF2
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=default_backend()
            )
            key = kdf.derive(password.encode('utf-8'))

            # Generate a random IV
            iv = os.urandom(16)

            # Encrypt the private key
            cipher = Cipher(
                algorithms.AES(key),
                modes.CFB(iv),
                backend=default_backend()
            )
            encryptor = cipher.encryptor()
            encrypted_private_key = encryptor.update(private_key_pem.encode('utf-8')) + encryptor.finalize()

            # Combine salt, IV, and encrypted key
            encrypted_data = salt + iv + encrypted_private_key

            # Return base64 encoded encrypted data
            return base64.b64encode(encrypted_data).decode('utf-8')

        except Exception as e:
            frappe.log_error(f"Private key encryption failed: {str(e)}", "Digital Signature Key Encryption")
            raise frappe.ValidationError(f"Failed to encrypt private key: {str(e)}")

    @staticmethod
    def decrypt_private_key(encrypted_private_key_b64, password):
        """
        Decrypt an encrypted private key
        Returns: decrypted private key (PEM format)
        """
        try:
            # Decode from base64
            encrypted_data = base64.b64decode(encrypted_private_key_b64)

            # Extract salt, IV, and encrypted key
            salt = encrypted_data[:16]
            iv = encrypted_data[16:32]
            encrypted_private_key = encrypted_data[32:]

            # Generate key from password using PBKDF2
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=default_backend()
            )
            key = kdf.derive(password.encode('utf-8'))

            # Decrypt the private key
            cipher = Cipher(
                algorithms.AES(key),
                modes.CFB(iv),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()
            private_key_pem = decryptor.update(encrypted_private_key) + decryptor.finalize()

            return private_key_pem.decode('utf-8')

        except Exception as e:
            frappe.log_error(f"Private key decryption failed: {str(e)}", "Digital Signature Key Decryption")
            raise frappe.ValidationError(f"Failed to decrypt private key: {str(e)}")

    @staticmethod
    def store_user_keys(user_id, private_key_pem, public_key_pem, password=None):
        """
        Store user's cryptographic keys securely
        """
        from pwp_project.pwp_project.doctype.user_crypto_keys.user_crypto_keys import UserCryptoKeys
        return UserCryptoKeys.store_user_keys(user_id, private_key_pem, public_key_pem, password)

    @staticmethod
    def get_user_private_key(user_id, password=None):
        """
        Retrieve user's private key, decrypting if necessary
        Returns: private key (PEM format)
        """
        from pwp_project.pwp_project.doctype.user_crypto_keys.user_crypto_keys import UserCryptoKeys
        return UserCryptoKeys.get_user_private_key(user_id, password)

    @staticmethod
    def get_user_public_key(user_id):
        """
        Retrieve user's public key
        Returns: public key (PEM format)
        """
        from pwp_project.pwp_project.doctype.user_crypto_keys.user_crypto_keys import UserCryptoKeys
        return UserCryptoKeys.get_user_public_key(user_id)
