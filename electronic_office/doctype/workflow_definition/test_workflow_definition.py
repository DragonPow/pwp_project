# Copyright (c) 2025, Government Agency and contributors
# For license information, please see license.txt

import frappe
import unittest
from electronic_office.electronic_office.doctype.workflow_definition.workflow_definition import WorkflowDefinition

class TestWorkflowDefinition(unittest.TestCase):
    def setUp(self):
        # Create a test document type
        if not frappe.db.exists("Document Type", "Test Document Type"):
            doc_type = frappe.get_doc({
                "doctype": "Document Type",
                "name": "Test Document Type",
                "description": "Test document type for workflow testing",
                "security_level": "Internal",
                "requires_approval": 1
            })
            doc_type.insert()
    
    def tearDown(self):
        # Clean up test data
        if frappe.db.exists("Workflow Definition", "Test Workflow"):
            frappe.delete_doc("Workflow Definition", "Test Workflow")
        
        if frappe.db.exists("Document Type", "Test Document Type"):
            frappe.delete_doc("Document Type", "Test Document Type")
    
    def test_workflow_definition_creation(self):
        """Test creating a Workflow Definition document"""
        workflow_doc = frappe.get_doc({
            "doctype": "Workflow Definition",
            "workflow_name": "Test Workflow",
            "document_type": "Test Document Type",
            "is_active": 1,
            "description": "Test workflow for testing purposes"
        })
        workflow_doc.insert()
        
        self.assertIsNotNone(workflow_doc.name)
        self.assertEqual(workflow_doc.workflow_name, "Test Workflow")
        self.assertEqual(workflow_doc.document_type, "Test Document Type")
        self.assertEqual(workflow_doc.is_active, 1)
    
    def test_workflow_definition_validation(self):
        """Test Workflow Definition validation"""
        # Test with missing required fields
        workflow_doc = frappe.get_doc({
            "doctype": "Workflow Definition",
            "workflow_name": "",
            "document_type": "",
            "is_active": 1
        })
        
        with self.assertRaises(frappe.ValidationError):
            workflow_doc.insert()
        
        # Test with valid fields
        workflow_doc.workflow_name = "Test Workflow"
        workflow_doc.document_type = "Test Document Type"
        workflow_doc.insert()
        
        self.assertIsNotNone(workflow_doc.name)
    
    def test_workflow_definition_uniqueness(self):
        """Test Workflow Definition name uniqueness"""
        # Create first workflow
        workflow_doc1 = frappe.get_doc({
            "doctype": "Workflow Definition",
            "workflow_name": "Test Workflow",
            "document_type": "Test Document Type",
            "is_active": 1
        })
        workflow_doc1.insert()
        
        # Try to create another workflow with the same name
        workflow_doc2 = frappe.get_doc({
            "doctype": "Workflow Definition",
            "workflow_name": "Test Workflow",
            "document_type": "Test Document Type",
            "is_active": 1
        })
        
        with self.assertRaises(frappe.DuplicateEntryError):
            workflow_doc2.insert()
    
    def test_workflow_definition_status_change(self):
        """Test Workflow Definition status change"""
        workflow_doc = frappe.get_doc({
            "doctype": "Workflow Definition",
            "workflow_name": "Test Workflow",
            "document_type": "Test Document Type",
            "is_active": 1
        })
        workflow_doc.insert()
        
        # Deactivate workflow
        workflow_doc.is_active = 0
        workflow_doc.save()
        
        # Reload document
        workflow_doc.reload()
        self.assertEqual(workflow_doc.is_active, 0)
        
        # Reactivate workflow
        workflow_doc.is_active = 1
        workflow_doc.save()
        
        # Reload document
        workflow_doc.reload()
        self.assertEqual(workflow_doc.is_active, 1)
    
    def test_workflow_definition_document_type_validation(self):
        """Test Workflow Definition document type validation"""
        # Test with non-existent document type
        workflow_doc = frappe.get_doc({
            "doctype": "Workflow Definition",
            "workflow_name": "Test Workflow",
            "document_type": "Non-existent Document Type",
            "is_active": 1
        })
        
        with self.assertRaises(frappe.ValidationError):
            workflow_doc.insert()
        
        # Test with valid document type
        workflow_doc.document_type = "Test Document Type"
        workflow_doc.insert()
        
        self.assertIsNotNone(workflow_doc.name)

def run_tests():
    """Run all tests"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestWorkflowDefinition)
    unittest.TextTestRunner(verbosity=2).run(suite)

if __name__ == '__main__':
    run_tests()