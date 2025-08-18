# Copyright (c) 2025, Government Agency and contributors
# For license information, please see license.txt

import frappe
import unittest
import json
from electronic_office.electronic_office.doctype.document_version.document_version import DocumentVersion

class TestDocumentVersion(unittest.TestCase):
    def setUp(self):
        # Create a test document type
        if not frappe.db.exists("Document Type", "Test Document Type"):
            doc_type = frappe.get_doc({
                "doctype": "Document Type",
                "name": "Test Document Type",
                "description": "Test document type for version testing",
                "security_level": "Internal",
                "requires_approval": 1
            })
            doc_type.insert()
        
        # Create a test document
        if not frappe.db.exists("Document", "TEST-DOC-001"):
            doc = frappe.get_doc({
                "doctype": "Document",
                "title": "Test Document",
                "description": "This is a test document for version testing",
                "document_type": "Test Document Type",
                "security_level": "Internal",
                "status": "Draft"
            })
            doc.insert()
    
    def tearDown(self):
        # Clean up test data
        if frappe.db.exists("Document Version", {"document": "TEST-DOC-001"}):
            versions = frappe.get_all("Document Version", {"document": "TEST-DOC-001"})
            for version in versions:
                frappe.delete_doc("Document Version", version.name)
        
        if frappe.db.exists("Document", "TEST-DOC-001"):
            frappe.delete_doc("Document", "TEST-DOC-001")
        
        if frappe.db.exists("Document Type", "Test Document Type"):
            frappe.delete_doc("Document Type", "Test Document Type")
    
    def test_document_version_creation(self):
        """Test creating a Document Version document"""
        version_doc = frappe.get_doc({
            "doctype": "Document Version",
            "document": "TEST-DOC-001",
            "version_number": 1,
            "version_name": "Initial Version",
            "content": "This is the initial content of the document",
            "status": "Draft"
        })
        version_doc.insert()
        
        self.assertIsNotNone(version_doc.name)
        self.assertEqual(version_doc.document, "TEST-DOC-001")
        self.assertEqual(version_doc.version_number, 1)
        self.assertEqual(version_doc.version_name, "Initial Version")
        self.assertEqual(version_doc.content, "This is the initial content of the document")
        self.assertEqual(version_doc.status, "Draft")
    
    def test_document_version_validation(self):
        """Test Document Version validation"""
        # Test with missing required fields
        version_doc = frappe.get_doc({
            "doctype": "Document Version",
            "document": "",
            "version_number": 1,
            "version_name": "Initial Version",
            "content": "This is the initial content of the document",
            "status": "Draft"
        })
        
        with self.assertRaises(frappe.ValidationError):
            version_doc.insert()
        
        # Test with valid fields
        version_doc.document = "TEST-DOC-001"
        version_doc.insert()
        
        self.assertIsNotNone(version_doc.name)
    
    def test_document_version_document_validation(self):
        """Test Document Version document validation"""
        # Test with non-existent document
        version_doc = frappe.get_doc({
            "doctype": "Document Version",
            "document": "NON-EXISTENT-DOC",
            "version_number": 1,
            "version_name": "Initial Version",
            "content": "This is the initial content of the document",
            "status": "Draft"
        })
        
        with self.assertRaises(frappe.ValidationError):
            version_doc.insert()
        
        # Test with valid document
        version_doc.document = "TEST-DOC-001"
        version_doc.insert()
        
        self.assertIsNotNone(version_doc.name)
    
    def test_document_version_number_uniqueness(self):
        """Test Document Version number uniqueness per document"""
        # Create first version
        version_doc1 = frappe.get_doc({
            "doctype": "Document Version",
            "document": "TEST-DOC-001",
            "version_number": 1,
            "version_name": "Initial Version",
            "content": "This is the initial content of the document",
            "status": "Draft"
        })
        version_doc1.insert()
        
        # Try to create another version with the same number for the same document
        version_doc2 = frappe.get_doc({
            "doctype": "Document Version",
            "document": "TEST-DOC-001",
            "version_number": 1,
            "version_name": "Duplicate Version",
            "content": "This is a duplicate version",
            "status": "Draft"
        })
        
        with self.assertRaises(frappe.DuplicateEntryError):
            version_doc2.insert()
    
    def test_document_version_status_change(self):
        """Test Document Version status change"""
        version_doc = frappe.get_doc({
            "doctype": "Document Version",
            "document": "TEST-DOC-001",
            "version_number": 1,
            "version_name": "Initial Version",
            "content": "This is the initial content of the document",
            "status": "Draft"
        })
        version_doc.insert()
        
        # Change status to Active
        version_doc.status = "Active"
        version_doc.save()
        
        # Reload document
        version_doc.reload()
        self.assertEqual(version_doc.status, "Active")
        
        # Change status to Archived
        version_doc.status = "Archived"
        version_doc.save()
        
        # Reload document
        version_doc.reload()
        self.assertEqual(version_doc.status, "Archived")
    
    def test_document_version_auto_increment(self):
        """Test Document Version auto-increment of version numbers"""
        # Create first version
        version_doc1 = frappe.get_doc({
            "doctype": "Document Version",
            "document": "TEST-DOC-001",
            "version_number": 1,
            "version_name": "Initial Version",
            "content": "This is the initial content of the document",
            "status": "Draft"
        })
        version_doc1.insert()
        
        # Create second version without specifying version number
        version_doc2 = frappe.get_doc({
            "doctype": "Document Version",
            "document": "TEST-DOC-001",
            "version_name": "Second Version",
            "content": "This is the second version of the document",
            "status": "Draft"
        })
        version_doc2.insert()
        
        # Verify version number was auto-incremented
        self.assertEqual(version_doc2.version_number, 2)
        
        # Create third version without specifying version number
        version_doc3 = frappe.get_doc({
            "doctype": "Document Version",
            "document": "TEST-DOC-001",
            "version_name": "Third Version",
            "content": "This is the third version of the document",
            "status": "Draft"
        })
        version_doc3.insert()
        
        # Verify version number was auto-incremented
        self.assertEqual(version_doc3.version_number, 3)
    
    def test_document_version_content_hash(self):
        """Test Document Version content hash generation"""
        version_doc = frappe.get_doc({
            "doctype": "Document Version",
            "document": "TEST-DOC-001",
            "version_number": 1,
            "version_name": "Initial Version",
            "content": "This is the initial content of the document",
            "status": "Draft"
        })
        version_doc.insert()
        
        # Verify content hash was generated
        self.assertIsNotNone(version_doc.content_hash)
        self.assertEqual(len(version_doc.content_hash), 64)  # SHA-256 hash length
        
        # Verify hash is consistent for same content
        hash1 = version_doc.content_hash
        
        # Create another version with same content
        version_doc2 = frappe.get_doc({
            "doctype": "Document Version",
            "document": "TEST-DOC-001",
            "version_number": 2,
            "version_name": "Duplicate Content Version",
            "content": "This is the initial content of the document",
            "status": "Draft"
        })
        version_doc2.insert()
        
        self.assertEqual(hash1, version_doc2.content_hash)
        
        # Verify hash is different for different content
        version_doc3 = frappe.get_doc({
            "doctype": "Document Version",
            "document": "TEST-DOC-001",
            "version_number": 3,
            "version_name": "Different Content Version",
            "content": "This is different content",
            "status": "Draft"
        })
        version_doc3.insert()
        
        self.assertNotEqual(hash1, version_doc3.content_hash)
    
    def test_document_version_restore_to_document(self):
        """Test Document Version restore to document functionality"""
        # Create initial version
        version_doc1 = frappe.get_doc({
            "doctype": "Document Version",
            "document": "TEST-DOC-001",
            "version_number": 1,
            "version_name": "Initial Version",
            "content": "This is the initial content of the document",
            "status": "Active"
        })
        version_doc1.insert()
        
        # Create second version
        version_doc2 = frappe.get_doc({
            "doctype": "Document Version",
            "document": "TEST-DOC-001",
            "version_number": 2,
            "version_name": "Updated Version",
            "content": "This is the updated content of the document",
            "status": "Active"
        })
        version_doc2.insert()
        
        # Restore first version to document
        result = version_doc1.restore_to_document()
        
        self.assertTrue(result)
        
        # Verify document content was updated
        document = frappe.get_doc("Document", "TEST-DOC-001")
        self.assertEqual(document.content, "This is the initial content of the document")
    
    def test_document_version_compare_with_version(self):
        """Test Document Version compare with version functionality"""
        # Create initial version
        version_doc1 = frappe.get_doc({
            "doctype": "Document Version",
            "document": "TEST-DOC-001",
            "version_number": 1,
            "version_name": "Initial Version",
            "content": "This is the initial content of the document",
            "status": "Active"
        })
        version_doc1.insert()
        
        # Create second version with different content
        version_doc2 = frappe.get_doc({
            "doctype": "Document Version",
            "document": "TEST-DOC-001",
            "version_number": 2,
            "version_name": "Updated Version",
            "content": "This is the updated content of the document with additional text",
            "status": "Active"
        })
        version_doc2.insert()
        
        # Compare versions
        comparison = version_doc1.compare_with_version(version_doc2.name)
        
        self.assertIsNotNone(comparison)
        self.assertIn("differences", comparison)
        self.assertTrue(len(comparison["differences"]) > 0)
    
    def test_document_version_get_version_info(self):
        """Test Document Version get version info functionality"""
        version_doc = frappe.get_doc({
            "doctype": "Document Version",
            "document": "TEST-DOC-001",
            "version_number": 1,
            "version_name": "Initial Version",
            "content": "This is the initial content of the document",
            "status": "Active"
        })
        version_doc.insert()
        
        # Get version info
        version_info = version_doc.get_version_info()
        
        self.assertIsNotNone(version_info)
        self.assertEqual(version_info["name"], version_doc.name)
        self.assertEqual(version_info["document"], version_doc.document)
        self.assertEqual(version_info["version_number"], version_doc.version_number)
        self.assertEqual(version_info["version_name"], version_doc.version_name)
        self.assertEqual(version_info["status"], version_doc.status)
        self.assertEqual(version_info["content"], version_doc.content)
        self.assertEqual(version_info["content_hash"], version_doc.content_hash)

def run_tests():
    """Run all tests"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDocumentVersion)
    unittest.TextTestRunner(verbosity=2).run(suite)

if __name__ == '__main__':
    run_tests()