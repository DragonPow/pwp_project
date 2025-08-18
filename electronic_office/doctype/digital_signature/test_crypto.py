#!/usr/bin/env python3
# Test script for digital signature cryptographic functionality

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from digital_signature import DigitalSignature
import json

def test_rsa_key_generation():
    """Test RSA key pair generation"""
    print("Testing RSA key pair generation...")
    try:
        private_key, public_key = DigitalSignature.generate_rsa_key_pair()
        print(f"✓ RSA key pair generated successfully")
        print(f"  Private key length: {len(private_key)}")
        print(f"  Public key length: {len(public_key)}")
        return private_key, public_key
    except Exception as e:
        print(f"✗ RSA key generation failed: {str(e)}")
        return None, None

def test_ecdsa_key_generation():
    """Test ECDSA key pair generation"""
    print("\nTesting ECDSA key pair generation...")
    try:
        private_key, public_key = DigitalSignature.generate_ecdsa_key_pair()
        print(f"✓ ECDSA key pair generated successfully")
        print(f"  Private key length: {len(private_key)}")
        print(f"  Public key length: {len(public_key)}")
        return private_key, public_key
    except Exception as e:
        print(f"✗ ECDSA key generation failed: {str(e)}")
        return None, None

def test_rsa_signing(private_key, public_key):
    """Test RSA signing and verification"""
    print("\nTesting RSA signing and verification...")
    try:
        test_data = "This is a test document for RSA digital signature"
        
        # Sign the data
        signature = DigitalSignature.sign_data_rsa(private_key, test_data)
        print(f"✓ Data signed successfully with RSA")
        print(f"  Signature length: {len(signature)}")
        
        # Verify the signature
        is_valid = DigitalSignature.verify_signature_rsa(public_key, test_data, signature)
        if is_valid:
            print("✓ RSA signature verified successfully")
        else:
            print("✗ RSA signature verification failed")
            
        # Test with wrong data
        wrong_data = "This is wrong data"
        is_valid_wrong = DigitalSignature.verify_signature_rsa(public_key, wrong_data, signature)
        if not is_valid_wrong:
            print("✓ RSA signature correctly rejected wrong data")
        else:
            print("✗ RSA signature incorrectly verified wrong data")
            
        return True
    except Exception as e:
        print(f"✗ RSA signing/verification failed: {str(e)}")
        return False

def test_ecdsa_signing(private_key, public_key):
    """Test ECDSA signing and verification"""
    print("\nTesting ECDSA signing and verification...")
    try:
        test_data = "This is a test document for ECDSA digital signature"
        
        # Sign the data
        signature = DigitalSignature.sign_data_ecdsa(private_key, test_data)
        print(f"✓ Data signed successfully with ECDSA")
        print(f"  Signature length: {len(signature)}")
        
        # Verify the signature
        is_valid = DigitalSignature.verify_signature_ecdsa(public_key, test_data, signature)
        if is_valid:
            print("✓ ECDSA signature verified successfully")
        else:
            print("✗ ECDSA signature verification failed")
            
        # Test with wrong data
        wrong_data = "This is wrong data"
        is_valid_wrong = DigitalSignature.verify_signature_ecdsa(public_key, wrong_data, signature)
        if not is_valid_wrong:
            print("✓ ECDSA signature correctly rejected wrong data")
        else:
            print("✗ ECDSA signature incorrectly verified wrong data")
            
        return True
    except Exception as e:
        print(f"✗ ECDSA signing/verification failed: {str(e)}")
        return False

def test_document_signature():
    """Test document signature creation and verification"""
    print("\nTesting document signature creation and verification...")
    try:
        # Generate RSA key pair
        private_key, public_key = DigitalSignature.generate_rsa_key_pair()
        
        # Create a test document
        test_document = "This is a test document content for digital signature testing"
        
        # Create document signature
        signature_metadata = DigitalSignature.create_document_signature(
            private_key, test_document, 'RSA'
        )
        print(f"✓ Document signature created successfully")
        print(f"  Algorithm: {signature_metadata['algorithm']}")
        print(f"  Document hash: {signature_metadata['document_hash']}")
        
        # Verify document signature
        is_valid = DigitalSignature.verify_document_signature(
            public_key, test_document, signature_metadata
        )
        if is_valid:
            print("✓ Document signature verified successfully")
        else:
            print("✗ Document signature verification failed")
            
        # Test with wrong document
        wrong_document = "This is a wrong document"
        is_valid_wrong = DigitalSignature.verify_document_signature(
            public_key, wrong_document, signature_metadata
        )
        if not is_valid_wrong:
            print("✓ Document signature correctly rejected wrong document")
        else:
            print("✗ Document signature incorrectly verified wrong document")
            
        return True
    except Exception as e:
        print(f"✗ Document signature testing failed: {str(e)}")
        return False

def test_key_encryption():
    """Test private key encryption and decryption"""
    print("\nTesting private key encryption and decryption...")
    try:
        # Generate RSA key pair
        private_key, public_key = DigitalSignature.generate_rsa_key_pair()
        
        # Encrypt private key
        password = "test_password_123"
        encrypted_key = DigitalSignature.encrypt_private_key(private_key, password)
        print(f"✓ Private key encrypted successfully")
        print(f"  Encrypted key length: {len(encrypted_key)}")
        
        # Decrypt private key
        decrypted_key = DigitalSignature.decrypt_private_key(encrypted_key, password)
        print(f"✓ Private key decrypted successfully")
        
        # Verify decrypted key matches original
        if decrypted_key == private_key:
            print("✓ Decrypted key matches original key")
        else:
            print("✗ Decrypted key does not match original key")
            
        # Test with wrong password
        try:
            wrong_decrypted = DigitalSignature.decrypt_private_key(encrypted_key, "wrong_password")
            print("✗ Decryption with wrong password should have failed")
        except:
            print("✓ Decryption with wrong password correctly failed")
            
        return True
    except Exception as e:
        print(f"✗ Key encryption/decryption testing failed: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("=== Digital Signature Cryptographic Functionality Tests ===\n")
    
    # Test RSA key generation
    rsa_private, rsa_public = test_rsa_key_generation()
    if not rsa_private or not rsa_public:
        print("Cannot continue with RSA tests - key generation failed")
        return False
    
    # Test ECDSA key generation
    ecdsa_private, ecdsa_public = test_ecdsa_key_generation()
    if not ecdsa_private or not ecdsa_public:
        print("Cannot continue with ECDSA tests - key generation failed")
        return False
    
    # Test RSA signing and verification
    rsa_signing_success = test_rsa_signing(rsa_private, rsa_public)
    
    # Test ECDSA signing and verification
    ecdsa_signing_success = test_ecdsa_signing(ecdsa_private, ecdsa_public)
    
    # Test document signature
    document_signature_success = test_document_signature()
    
    # Test key encryption
    key_encryption_success = test_key_encryption()
    
    # Summary
    print("\n=== Test Summary ===")
    print(f"RSA Key Generation: {'✓ PASS' if rsa_private else '✗ FAIL'}")
    print(f"ECDSA Key Generation: {'✓ PASS' if ecdsa_private else '✗ FAIL'}")
    print(f"RSA Signing/Verification: {'✓ PASS' if rsa_signing_success else '✗ FAIL'}")
    print(f"ECDSA Signing/Verification: {'✓ PASS' if ecdsa_signing_success else '✗ FAIL'}")
    print(f"Document Signature: {'✓ PASS' if document_signature_success else '✗ FAIL'}")
    print(f"Key Encryption/Decryption: {'✓ PASS' if key_encryption_success else '✗ FAIL'}")
    
    all_passed = all([
        rsa_private, ecdsa_private, 
        rsa_signing_success, ecdsa_signing_success,
        document_signature_success, key_encryption_success
    ])
    
    print(f"\nOverall Result: {'✓ ALL TESTS PASSED' if all_passed else '✗ SOME TESTS FAILED'}")
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)