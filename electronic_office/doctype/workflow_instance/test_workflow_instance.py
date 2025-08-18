# Copyright (c) 2025, Government Agency and contributors
# For license information, please see license.txt

import frappe
import unittest
from electronic_office.electronic_office.doctype.workflow_instance.workflow_instance import WorkflowInstance

class TestWorkflowInstance(unittest.TestCase):
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
        
        # Create a test workflow definition
        if not frappe.db.exists("Workflow Definition", "Test Workflow"):
            workflow_def = frappe.get_doc({
                "doctype": "Workflow Definition",
                "workflow_name": "Test Workflow",
                "document_type": "Test Document Type",
                "is_active": 1,
                "description": "Test workflow for testing purposes"
            })
            workflow_def.insert()
        
        # Create a test document
        if not frappe.db.exists("Document", "TEST-DOC-001"):
            doc = frappe.get_doc({
                "doctype": "Document",
                "title": "Test Document",
                "description": "This is a test document for workflow testing",
                "document_type": "Test Document Type",
                "security_level": "Internal",
                "status": "Draft"
            })
            doc.insert()
    
    def tearDown(self):
        # Clean up test data
        if frappe.db.exists("Workflow Instance", {"document": "TEST-DOC-001"}):
            instances = frappe.get_all("Workflow Instance", {"document": "TEST-DOC-001"})
            for instance in instances:
                frappe.delete_doc("Workflow Instance", instance.name)
        
        if frappe.db.exists("Workflow Definition", "Test Workflow"):
            frappe.delete_doc("Workflow Definition", "Test Workflow")
        
        if frappe.db.exists("Document", "TEST-DOC-001"):
            frappe.delete_doc("Document", "TEST-DOC-001")
        
        if frappe.db.exists("Document Type", "Test Document Type"):
            frappe.delete_doc("Document Type", "Test Document Type")
    
    def test_workflow_instance_creation(self):
        """Test creating a Workflow Instance document"""
        workflow_instance_doc = frappe.get_doc({
            "doctype": "Workflow Instance",
            "workflow_definition": "Test Workflow",
            "document": "TEST-DOC-001",
            "status": "Draft",
            "current_step": "Draft"
        })
        workflow_instance_doc.insert()
        
        self.assertIsNotNone(workflow_instance_doc.name)
        self.assertEqual(workflow_instance_doc.workflow_definition, "Test Workflow")
        self.assertEqual(workflow_instance_doc.document, "TEST-DOC-001")
        self.assertEqual(workflow_instance_doc.status, "Draft")
        self.assertEqual(workflow_instance_doc.current_step, "Draft")
    
    def test_workflow_instance_validation(self):
        """Test Workflow Instance validation"""
        # Test with missing required fields
        workflow_instance_doc = frappe.get_doc({
            "doctype": "Workflow Instance",
            "workflow_definition": "",
            "document": "",
            "status": "Draft",
            "current_step": "Draft"
        })
        
        with self.assertRaises(frappe.ValidationError):
            workflow_instance_doc.insert()
        
        # Test with valid fields
        workflow_instance_doc.workflow_definition = "Test Workflow"
        workflow_instance_doc.document = "TEST-DOC-001"
        workflow_instance_doc.insert()
        
        self.assertIsNotNone(workflow_instance_doc.name)
    
    def test_workflow_instance_workflow_definition_validation(self):
        """Test Workflow Instance workflow definition validation"""
        # Test with non-existent workflow definition
        workflow_instance_doc = frappe.get_doc({
            "doctype": "Workflow Instance",
            "workflow_definition": "Non-existent Workflow",
            "document": "TEST-DOC-001",
            "status": "Draft",
            "current_step": "Draft"
        })
        
        with self.assertRaises(frappe.ValidationError):
            workflow_instance_doc.insert()
        
        # Test with valid workflow definition
        workflow_instance_doc.workflow_definition = "Test Workflow"
        workflow_instance_doc.insert()
        
        self.assertIsNotNone(workflow_instance_doc.name)
    
    def test_workflow_instance_document_validation(self):
        """Test Workflow Instance document validation"""
        # Test with non-existent document
        workflow_instance_doc = frappe.get_doc({
            "doctype": "Workflow Instance",
            "workflow_definition": "Test Workflow",
            "document": "NON-EXISTENT-DOC",
            "status": "Draft",
            "current_step": "Draft"
        })
        
        with self.assertRaises(frappe.ValidationError):
            workflow_instance_doc.insert()
        
        # Test with valid document
        workflow_instance_doc.document = "TEST-DOC-001"
        workflow_instance_doc.insert()
        
        self.assertIsNotNone(workflow_instance_doc.name)
    
    def test_workflow_instance_status_change(self):
        """Test Workflow Instance status change"""
        workflow_instance_doc = frappe.get_doc({
            "doctype": "Workflow Instance",
            "workflow_definition": "Test Workflow",
            "document": "TEST-DOC-001",
            "status": "Draft",
            "current_step": "Draft"
        })
        workflow_instance_doc.insert()
        
        # Change status to In Progress
        workflow_instance_doc.status = "In Progress"
        workflow_instance_doc.current_step = "Review"
        workflow_instance_doc.save()
        
        # Reload document
        workflow_instance_doc.reload()
        self.assertEqual(workflow_instance_doc.status, "In Progress")
        self.assertEqual(workflow_instance_doc.current_step, "Review")
        
        # Change status to Completed
        workflow_instance_doc.status = "Completed"
        workflow_instance_doc.current_step = "Completed"
        workflow_instance_doc.save()
        
        # Reload document
        workflow_instance_doc.reload()
        self.assertEqual(workflow_instance_doc.status, "Completed")
        self.assertEqual(workflow_instance_doc.current_step, "Completed")
    
    def test_workflow_instance_uniqueness(self):
        """Test Workflow Instance uniqueness per document"""
        # Create first workflow instance
        workflow_instance_doc1 = frappe.get_doc({
            "doctype": "Workflow Instance",
            "workflow_definition": "Test Workflow",
            "document": "TEST-DOC-001",
            "status": "Draft",
            "current_step": "Draft"
        })
        workflow_instance_doc1.insert()
        
        # Try to create another workflow instance for the same document
        workflow_instance_doc2 = frappe.get_doc({
            "doctype": "Workflow Instance",
            "workflow_definition": "Test Workflow",
            "document": "TEST-DOC-001",
            "status": "Draft",
            "current_step": "Draft"
        })
        
        with self.assertRaises(frappe.DuplicateEntryError):
            workflow_instance_doc2.insert()
    
    def test_workflow_instance_workflow_definition_document_type_match(self):
        """Test that workflow definition document type matches document type"""
        # Create a different document type
        if not frappe.db.exists("Document Type", "Another Document Type"):
            doc_type = frappe.get_doc({
                "doctype": "Document Type",
                "name": "Another Document Type",
                "description": "Another test document type",
                "security_level": "Internal",
                "requires_approval": 1
            })
            doc_type.insert()
        
        # Create a document with the different type
        if not frappe.db.exists("Document", "TEST-DOC-002"):
            doc = frappe.get_doc({
                "doctype": "Document",
                "title": "Another Test Document",
                "description": "This is another test document",
                "document_type": "Another Document Type",
                "security_level": "Internal",
                "status": "Draft"
            })
            doc.insert()
        
        # Try to create workflow instance with mismatched document type
        workflow_instance_doc = frappe.get_doc({
            "doctype": "Workflow Instance",
            "workflow_definition": "Test Workflow",  # This is for "Test Document Type"
            "document": "TEST-DOC-002",  # This is "Another Document Type"
            "status": "Draft",
            "current_step": "Draft"
        })
        
        with self.assertRaises(frappe.ValidationError):
            workflow_instance_doc.insert()
        
        # Clean up
        frappe.delete_doc("Document", "TEST-DOC-002")
        frappe.delete_doc("Document Type", "Another Document Type")

def run_tests():
    """Run all tests"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestWorkflowInstance)
    unittest.TextTestRunner(verbosity=2).run(suite)

if __name__ == '__main__':
    run_tests()