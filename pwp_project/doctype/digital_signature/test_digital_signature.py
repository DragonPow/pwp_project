# Copyright (c) 2025, Government Agency and contributors
# For license information, please see license.txt

import frappe
import unittest
import json
import base64
from pwp_project.pwp_project.doctype.digital_signature.digital_signature import DigitalSignature
from pwp_project.pwp_project.doctype.user_crypto_keys.user_crypto_keys import UserCryptoKeys

class TestDigitalSignature(unittest.TestCase):
    def setUp(self):
        # Create a test user
        if not frappe.db.exists("User", "test@example.com"):
            user = frappe.get_doc({
                "doctype": "User",
                "email": "test@example.com",
                "first_name": "Test",
                "last_name": "User",
                "username": "testuser",
                "enabled": 1
            })
            user.insert()

        # Create a test document
        if not frappe.db.exists("Document", "TEST-DOC-001"):
            doc = frappe.get_doc({
                "doctype": "Document",
                "title": "Test Document",
                "description": "This is a test document for digital signature testing",
                "document_type": "Test",
                "security_level": "Internal",
                "status": "Draft"
            })
            doc.insert()

    def tearDown(self):
        # Clean up test data
        if frappe.db.exists("Digital Signature", {"document": "TEST-DOC-001"}):
            signatures = frappe.get_all("Digital Signature", {"document": "TEST-DOC-001"})
            for sig in signatures:
                frappe.delete_doc("Digital Signature", sig.name)

        if frappe.db.exists("User Crypto Keys", "test@example.com"):
            frappe.delete_doc("User Crypto Keys", "test@example.com")

        if frappe.db.exists("Document", "TEST-DOC-001"):
            frappe.delete_doc("Document", "TEST-DOC-001")

        if frappe.db.exists("User", "test@example.com"):
            frappe.delete_doc("User", "test@example.com")

    def test_generate_rsa_key_pair(self):
        """Test RSA key pair generation"""
        private_key_pem, public_key_pem = DigitalSignature.generate_rsa_key_pair()

        self.assertIsNotNone(private_key_pem)
        self.assertIsNotNone(public_key_pem)
        self.assertIn("-----BEGIN PRIVATE KEY-----", private_key_pem)
        self.assertIn("-----BEGIN PUBLIC KEY-----", public_key_pem)

    def test_generate_ecdsa_key_pair(self):
        """Test ECDSA key pair generation"""
        private_key_pem, public_key_pem = DigitalSignature.generate_ecdsa_key_pair()

        self.assertIsNotNone(private_key_pem)
        self.assertIsNotNone(public_key_pem)
        self.assertIn("-----BEGIN PRIVATE KEY-----", private_key_pem)
        self.assertIn("-----BEGIN PUBLIC KEY-----", public_key_pem)

    def test_sign_and_verify_rsa(self):
        """Test RSA signing and verification"""
        # Generate key pair
        private_key_pem, public_key_pem = DigitalSignature.generate_rsa_key_pair()

        # Test data
        test_data = "This is a test message for RSA signing"

        # Sign the data
        signature = DigitalSignature.sign_data_rsa(private_key_pem, test_data)

        # Verify the signature
        is_valid = DigitalSignature.verify_signature_rsa(public_key_pem, test_data, signature)

        self.assertTrue(is_valid)

        # Test with wrong data
        wrong_data = "This is a wrong message"
        is_valid_wrong = DigitalSignature.verify_signature_rsa(public_key_pem, wrong_data, signature)
        self.assertFalse(is_valid_wrong)

    def test_sign_and_verify_ecdsa(self):
        """Test ECDSA signing and verification"""
        # Generate key pair
        private_key_pem, public_key_pem = DigitalSignature.generate_ecdsa_key_pair()

        # Test data
        test_data = "This is a test message for ECDSA signing"

        # Sign the data
        signature = DigitalSignature.sign_data_ecdsa(private_key_pem, test_data)

        # Verify the signature
        is_valid = DigitalSignature.verify_signature_ecdsa(public_key_pem, test_data, signature)

        self.assertTrue(is_valid)

        # Test with wrong data
        wrong_data = "This is a wrong message"
        is_valid_wrong = DigitalSignature.verify_signature_ecdsa(public_key_pem, wrong_data, signature)
        self.assertFalse(is_valid_wrong)

    def test_create_and_verify_document_signature_rsa(self):
        """Test creating and verifying document signature with RSA"""
        # Generate key pair
        private_key_pem, public_key_pem = DigitalSignature.generate_rsa_key_pair()

        # Test document content
        document_content = "This is a test document content for RSA digital signature"

        # Create document signature
        signature_metadata = DigitalSignature.create_document_signature(
            private_key_pem, document_content, 'RSA'
        )

        # Verify document signature
        is_valid = DigitalSignature.verify_document_signature(
            public_key_pem, document_content, signature_metadata
        )

        self.assertTrue(is_valid)
        self.assertEqual(signature_metadata['algorithm'], 'RSA')
        self.assertIn('document_hash', signature_metadata)
        self.assertIn('signature', signature_metadata)

    def test_create_and_verify_document_signature_ecdsa(self):
        """Test creating and verifying document signature with ECDSA"""
        # Generate key pair
        private_key_pem, public_key_pem = DigitalSignature.generate_ecdsa_key_pair()

        # Test document content
        document_content = "This is a test document content for ECDSA digital signature"

        # Create document signature
        signature_metadata = DigitalSignature.create_document_signature(
            private_key_pem, document_content, 'ECDSA'
        )

        # Verify document signature
        is_valid = DigitalSignature.verify_document_signature(
            public_key_pem, document_content, signature_metadata
        )

        self.assertTrue(is_valid)
        self.assertEqual(signature_metadata['algorithm'], 'ECDSA')
        self.assertIn('document_hash', signature_metadata)
        self.assertIn('signature', signature_metadata)

    def test_encrypt_and_decrypt_private_key(self):
        """Test private key encryption and decryption"""
        # Generate key pair
        private_key_pem, public_key_pem = DigitalSignature.generate_rsa_key_pair()

        # Password for encryption
        password = "test_password_123"

        # Encrypt private key
        encrypted_key = DigitalSignature.encrypt_private_key(private_key_pem, password)

        # Decrypt private key
        decrypted_key = DigitalSignature.decrypt_private_key(encrypted_key, password)

        self.assertEqual(private_key_pem, decrypted_key)

        # Test with wrong password
        with self.assertRaises(Exception):
            DigitalSignature.decrypt_private_key(encrypted_key, "wrong_password")

    def test_user_crypto_keys_storage(self):
        """Test storing and retrieving user cryptographic keys"""
        # Generate key pair
        private_key_pem, public_key_pem = DigitalSignature.generate_rsa_key_pair()

        # Store user keys
        UserCryptoKeys.store_user_keys("test@example.com", private_key_pem, public_key_pem)

        # Retrieve user keys
        retrieved_public_key = UserCryptoKeys.get_user_public_key("test@example.com")
        retrieved_private_key = UserCryptoKeys.get_user_private_key("test@example.com")

        self.assertEqual(public_key_pem, retrieved_public_key)
        self.assertEqual(private_key_pem, retrieved_private_key)

    def test_user_crypto_keys_with_password(self):
        """Test storing and retrieving user cryptographic keys with password protection"""
        # Generate key pair
        private_key_pem, public_key_pem = DigitalSignature.generate_rsa_key_pair()

        # Password for encryption
        password = "test_password_123"

        # Store user keys with password
        UserCryptoKeys.store_user_keys("test@example.com", private_key_pem, public_key_pem, password)

        # Retrieve user keys
        retrieved_public_key = UserCryptoKeys.get_user_public_key("test@example.com")
        retrieved_private_key = UserCryptoKeys.get_user_private_key("test@example.com", password)

        self.assertEqual(public_key_pem, retrieved_public_key)
        self.assertEqual(private_key_pem, retrieved_private_key)

        # Test retrieval without password
        with self.assertRaises(ValueError):
            UserCryptoKeys.get_user_private_key("test@example.com")

    def test_digital_signature_doc_creation(self):
        """Test creating a Digital Signature document"""
        # Generate and store user keys
        private_key_pem, public_key_pem = DigitalSignature.generate_rsa_key_pair()
        UserCryptoKeys.store_user_keys("test@example.com", private_key_pem, public_key_pem)

        # Create digital signature document
        signature_doc = frappe.get_doc({
            "doctype": "Digital Signature",
            "document": "TEST-DOC-001",
            "signature_provider": "Internal",
            "verification_status": "Pending"
        })
        signature_doc.insert()

        self.assertIsNotNone(signature_doc.name)
        self.assertEqual(signature_doc.document, "TEST-DOC-001")
        self.assertEqual(signature_doc.signature_provider, "Internal")
        self.assertEqual(signature_doc.verification_status, "Pending")

    def test_digital_signature_doc_signing(self):
        """Test signing a document with Digital Signature document"""
        # Generate and store user keys
        private_key_pem, public_key_pem = DigitalSignature.generate_rsa_key_pair()
        UserCryptoKeys.store_user_keys("test@example.com", private_key_pem, public_key_pem)

        # Create digital signature document
        signature_doc = frappe.get_doc({
            "doctype": "Digital Signature",
            "document": "TEST-DOC-001",
            "signature_provider": "Internal",
            "verification_status": "Pending"
        })
        signature_doc.insert()

        # Sign the document
        signature_metadata = signature_doc.sign_document(private_key_pem, 'RSA')

        self.assertIsNotNone(signature_metadata)
        self.assertIn('signature', signature_metadata)
        self.assertEqual(signature_doc.verification_status, "Verified")
        self.assertIsNotNone(signature_doc.signature_data)

    def test_digital_signature_doc_verification(self):
        """Test verifying a digital signature"""
        # Generate and store user keys
        private_key_pem, public_key_pem = DigitalSignature.generate_rsa_key_pair()
        UserCryptoKeys.store_user_keys("test@example.com", private_key_pem, public_key_pem)

        # Create digital signature document
        signature_doc = frappe.get_doc({
            "doctype": "Digital Signature",
            "document": "TEST-DOC-001",
            "signature_provider": "Internal",
            "verification_status": "Pending"
        })
        signature_doc.insert()

        # Sign the document
        signature_doc.sign_document(private_key_pem, 'RSA')

        # Verify the signature
        signature_doc.verify_signature()

        self.assertEqual(signature_doc.verification_status, "Verified")

def run_tests():
    """Run all tests"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDigitalSignature)
    unittest.TextTestRunner(verbosity=2).run(suite)

if __name__ == '__main__':
    run_tests()
