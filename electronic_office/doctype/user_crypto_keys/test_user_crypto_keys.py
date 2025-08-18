# Copyright (c) 2025, Government Agency and contributors
# For license information, please see license.txt

import frappe
import unittest
import json
from datetime import datetime, timedelta
from electronic_office.electronic_office.doctype.user_crypto_keys.user_crypto_keys import UserCryptoKeys
from electronic_office.electronic_office.doctype.digital_signature.digital_signature import DigitalSignature

class TestUserCryptoKeys(unittest.TestCase):
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
    
    def tearDown(self):
        # Clean up test data
        if frappe.db.exists("User Crypto Keys", "test@example.com"):
            frappe.delete_doc("User Crypto Keys", "test@example.com")
        
        if frappe.db.exists("User", "test@example.com"):
            frappe.delete_doc("User", "test@example.com")
    
    def test_user_crypto_keys_creation(self):
        """Test creating User Crypto Keys document"""
        # Generate key pair
        private_key_pem, public_key_pem = DigitalSignature.generate_rsa_key_pair()
        
        # Create user crypto keys document
        keys_doc = frappe.get_doc({
            "doctype": "User Crypto Keys",
            "user": "test@example.com",
            "public_key": public_key_pem,
            "private_key": private_key_pem,
            "key_algorithm": "RSA",
            "key_size": 2048,
            "key_status": "Active"
        })
        keys_doc.insert()
        
        self.assertIsNotNone(keys_doc.name)
        self.assertEqual(keys_doc.user, "test@example.com")
        self.assertEqual(keys_doc.key_algorithm, "RSA")
        self.assertEqual(keys_doc.key_size, 2048)
        self.assertEqual(keys_doc.key_status, "Active")
        self.assertIsNotNone(keys_doc.key_generation_date)
        self.assertIsNotNone(keys_doc.key_fingerprint)
    
    def test_user_crypto_keys_creation_ecdsa(self):
        """Test creating User Crypto Keys document with ECDSA"""
        # Generate key pair
        private_key_pem, public_key_pem = DigitalSignature.generate_ecdsa_key_pair()
        
        # Create user crypto keys document
        keys_doc = frappe.get_doc({
            "doctype": "User Crypto Keys",
            "user": "test@example.com",
            "public_key": public_key_pem,
            "private_key": private_key_pem,
            "key_algorithm": "ECDSA",
            "curve": "secp256r1",
            "key_status": "Active"
        })
        keys_doc.insert()
        
        self.assertIsNotNone(keys_doc.name)
        self.assertEqual(keys_doc.user, "test@example.com")
        self.assertEqual(keys_doc.key_algorithm, "ECDSA")
        self.assertEqual(keys_doc.curve, "secp256r1")
        self.assertEqual(keys_doc.key_status, "Active")
        self.assertIsNotNone(keys_doc.key_generation_date)
        self.assertIsNotNone(keys_doc.key_fingerprint)
    
    def test_key_fingerprint_calculation(self):
        """Test key fingerprint calculation"""
        # Generate key pair
        private_key_pem, public_key_pem = DigitalSignature.generate_rsa_key_pair()
        
        # Create user crypto keys document
        keys_doc = frappe.get_doc({
            "doctype": "User Crypto Keys",
            "user": "test@example.com",
            "public_key": public_key_pem,
            "private_key": private_key_pem,
            "key_algorithm": "RSA",
            "key_size": 2048,
            "key_status": "Active"
        })
        keys_doc.insert()
        
        self.assertIsNotNone(keys_doc.key_fingerprint)
        self.assertIn(':', keys_doc.key_fingerprint)
        
        # Verify fingerprint is consistent
        fingerprint1 = keys_doc.key_fingerprint
        
        # Create another document with same key
        keys_doc2 = frappe.get_doc({
            "doctype": "User Crypto Keys",
            "user": "test2@example.com",
            "public_key": public_key_pem,
            "private_key": private_key_pem,
            "key_algorithm": "RSA",
            "key_size": 2048,
            "key_status": "Active"
        })
        keys_doc2.insert()
        
        self.assertEqual(fingerprint1, keys_doc2.key_fingerprint)
        
        # Clean up
        frappe.delete_doc("User Crypto Keys", "test2@example.com")
    
    def test_key_expiration_validation(self):
        """Test key expiration validation"""
        # Generate key pair
        private_key_pem, public_key_pem = DigitalSignature.generate_rsa_key_pair()
        
        # Create user crypto keys document with past expiration date
        past_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        keys_doc = frappe.get_doc({
            "doctype": "User Crypto Keys",
            "user": "test@example.com",
            "public_key": public_key_pem,
            "private_key": private_key_pem,
            "key_algorithm": "RSA",
            "key_size": 2048,
            "key_expiration_date": past_date,
            "key_status": "Active"
        })
        keys_doc.insert()
        
        # Key status should be updated to Expired
        self.assertEqual(keys_doc.key_status, "Expired")
    
    def test_key_revocation(self):
        """Test key revocation"""
        # Generate key pair
        private_key_pem, public_key_pem = DigitalSignature.generate_rsa_key_pair()
        
        # Create user crypto keys document
        keys_doc = frappe.get_doc({
            "doctype": "User Crypto Keys",
            "user": "test@example.com",
            "public_key": public_key_pem,
            "private_key": private_key_pem,
            "key_algorithm": "RSA",
            "key_size": 2048,
            "key_status": "Active"
        })
        keys_doc.insert()
        
        # Revoke keys
        keys_doc.revoke_keys("Test revocation")
        
        self.assertEqual(keys_doc.key_status, "Revoked")
    
    def test_key_rotation(self):
        """Test key rotation"""
        # Generate key pair
        private_key_pem, public_key_pem = DigitalSignature.generate_rsa_key_pair()
        
        # Create user crypto keys document
        keys_doc = frappe.get_doc({
            "doctype": "User Crypto Keys",
            "user": "test@example.com",
            "public_key": public_key_pem,
            "private_key": private_key_pem,
            "key_algorithm": "RSA",
            "key_size": 2048,
            "key_status": "Active"
        })
        keys_doc.insert()
        
        # Store original keys
        original_public_key = keys_doc.public_key
        original_private_key = keys_doc.private_key
        original_generation_date = keys_doc.key_generation_date
        
        # Rotate keys
        keys_doc.rotate_keys(new_key_size=4096)
        
        # Verify keys have changed
        self.assertNotEqual(original_public_key, keys_doc.public_key)
        self.assertNotEqual(original_private_key, keys_doc.private_key)
        self.assertNotEqual(original_generation_date, keys_doc.key_generation_date)
        self.assertEqual(keys_doc.key_size, 4096)
        self.assertEqual(keys_doc.key_status, "Active")
    
    def test_key_rotation_algorithm_change(self):
        """Test key rotation with algorithm change"""
        # Generate RSA key pair
        private_key_pem, public_key_pem = DigitalSignature.generate_rsa_key_pair()
        
        # Create user crypto keys document
        keys_doc = frappe.get_doc({
            "doctype": "User Crypto Keys",
            "user": "test@example.com",
            "public_key": public_key_pem,
            "private_key": private_key_pem,
            "key_algorithm": "RSA",
            "key_size": 2048,
            "key_status": "Active"
        })
        keys_doc.insert()
        
        # Rotate keys to ECDSA
        keys_doc.rotate_keys(new_key_algorithm="ECDSA", new_curve="secp384r1")
        
        # Verify algorithm has changed
        self.assertEqual(keys_doc.key_algorithm, "ECDSA")
        self.assertEqual(keys_doc.curve, "secp384r1")
        self.assertIsNone(keys_doc.key_size)
        self.assertEqual(keys_doc.key_status, "Active")
    
    def test_get_user_keys(self):
        """Test getting user keys"""
        # Generate key pair
        private_key_pem, public_key_pem = DigitalSignature.generate_rsa_key_pair()
        
        # Create user crypto keys document
        keys_doc = frappe.get_doc({
            "doctype": "User Crypto Keys",
            "user": "test@example.com",
            "public_key": public_key_pem,
            "private_key": private_key_pem,
            "key_algorithm": "RSA",
            "key_size": 2048,
            "key_status": "Active"
        })
        keys_doc.insert()
        
        # Get user keys
        retrieved_keys = UserCryptoKeys.get_user_keys("test@example.com")
        
        self.assertIsNotNone(retrieved_keys)
        self.assertEqual(retrieved_keys.user, "test@example.com")
        self.assertEqual(retrieved_keys.public_key, public_key_pem)
        self.assertEqual(retrieved_keys.private_key, private_key_pem)
    
    def test_get_user_public_key(self):
        """Test getting user public key"""
        # Generate key pair
        private_key_pem, public_key_pem = DigitalSignature.generate_rsa_key_pair()
        
        # Create user crypto keys document
        keys_doc = frappe.get_doc({
            "doctype": "User Crypto Keys",
            "user": "test@example.com",
            "public_key": public_key_pem,
            "private_key": private_key_pem,
            "key_algorithm": "RSA",
            "key_size": 2048,
            "key_status": "Active"
        })
        keys_doc.insert()
        
        # Get user public key
        retrieved_public_key = UserCryptoKeys.get_user_public_key("test@example.com")
        
        self.assertEqual(retrieved_public_key, public_key_pem)
    
    def test_get_user_private_key(self):
        """Test getting user private key"""
        # Generate key pair
        private_key_pem, public_key_pem = DigitalSignature.generate_rsa_key_pair()
        
        # Create user crypto keys document
        keys_doc = frappe.get_doc({
            "doctype": "User Crypto Keys",
            "user": "test@example.com",
            "public_key": public_key_pem,
            "private_key": private_key_pem,
            "key_algorithm": "RSA",
            "key_size": 2048,
            "key_status": "Active"
        })
        keys_doc.insert()
        
        # Get user private key
        retrieved_private_key = UserCryptoKeys.get_user_private_key("test@example.com")
        
        self.assertEqual(retrieved_private_key, private_key_pem)
    
    def test_store_user_keys(self):
        """Test storing user keys"""
        # Generate key pair
        private_key_pem, public_key_pem = DigitalSignature.generate_rsa_key_pair()
        
        # Store user keys
        result = UserCryptoKeys.store_user_keys("test@example.com", private_key_pem, public_key_pem)
        
        self.assertTrue(result)
        
        # Verify keys were stored
        retrieved_keys = UserCryptoKeys.get_user_keys("test@example.com")
        self.assertIsNotNone(retrieved_keys)
        self.assertEqual(retrieved_keys.public_key, public_key_pem)
        self.assertEqual(retrieved_keys.private_key, private_key_pem)
    
    def test_store_user_keys_with_password(self):
        """Test storing user keys with password protection"""
        # Generate key pair
        private_key_pem, public_key_pem = DigitalSignature.generate_rsa_key_pair()
        
        # Store user keys with password
        password = "test_password_123"
        result = UserCryptoKeys.store_user_keys("test@example.com", private_key_pem, public_key_pem, password)
        
        self.assertTrue(result)
        
        # Verify keys were stored
        retrieved_keys = UserCryptoKeys.get_user_keys("test@example.com")
        self.assertIsNotNone(retrieved_keys)
        self.assertEqual(retrieved_keys.public_key, public_key_pem)
        self.assertEqual(retrieved_keys.private_key_encrypted, 1)
        
        # Test private key retrieval with password
        retrieved_private_key = UserCryptoKeys.get_user_private_key("test@example.com", password)
        self.assertEqual(retrieved_private_key, private_key_pem)
        
        # Test private key retrieval without password
        with self.assertRaises(ValueError):
            UserCryptoKeys.get_user_private_key("test@example.com")
    
    def test_generate_and_store_user_keys(self):
        """Test generating and storing user keys"""
        # Generate and store user keys
        result = UserCryptoKeys.generate_and_store_user_keys("test@example.com", "RSA", 2048)
        
        self.assertTrue(result)
        
        # Verify keys were generated and stored
        retrieved_keys = UserCryptoKeys.get_user_keys("test@example.com")
        self.assertIsNotNone(retrieved_keys)
        self.assertEqual(retrieved_keys.key_algorithm, "RSA")
        self.assertEqual(retrieved_keys.key_size, 2048)
        self.assertIsNotNone(retrieved_keys.public_key)
        self.assertIsNotNone(retrieved_keys.private_key)
        self.assertEqual(retrieved_keys.key_status, "Active")
    
    def test_generate_and_store_user_keys_ecdsa(self):
        """Test generating and storing user keys with ECDSA"""
        # Generate and store user keys
        result = UserCryptoKeys.generate_and_store_user_keys("test@example.com", "ECDSA", None, "secp384r1")
        
        self.assertTrue(result)
        
        # Verify keys were generated and stored
        retrieved_keys = UserCryptoKeys.get_user_keys("test@example.com")
        self.assertIsNotNone(retrieved_keys)
        self.assertEqual(retrieved_keys.key_algorithm, "ECDSA")
        self.assertEqual(retrieved_keys.curve, "secp384r1")
        self.assertIsNone(retrieved_keys.key_size)
        self.assertIsNotNone(retrieved_keys.public_key)
        self.assertIsNotNone(retrieved_keys.private_key)
        self.assertEqual(retrieved_keys.key_status, "Active")

def run_tests():
    """Run all tests"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestUserCryptoKeys)
    unittest.TextTestRunner(verbosity=2).run(suite)

if __name__ == '__main__':
    run_tests()