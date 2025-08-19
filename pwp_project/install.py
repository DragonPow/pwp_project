# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe

def after_install():
    """
    Function to be executed after the app is installed.
    This function sets up the basic configuration and default data for the PWP Project System.
    """
    # Create default roles
    create_default_roles()

    # Create default document types
    create_default_document_types()

    # Create default workflow definitions
    create_default_workflows()

    # Set up default permissions
    setup_default_permissions()

    frappe.msgprint("PWP Project System has been installed successfully!")

def create_default_roles():
    """Create default roles for the PWP Project System"""
    roles = [
        {"role_name": "Document Manager", "desk_access": 1, "restrict_to_domain": "PWP Project"},
        {"role_name": "Workflow Manager", "desk_access": 1, "restrict_to_domain": "PWP Project"},
        {"role_name": "Document Approver", "desk_access": 1, "restrict_to_domain": "PWP Project"},
        {"role_name": "Document Reviewer", "desk_access": 1, "restrict_to_domain": "PWP Project"},
        {"role_name": "Digital Signature Authority", "desk_access": 1, "restrict_to_domain": "PWP Project"}
    ]

    for role in roles:
        if not frappe.db.exists("Role", role["role_name"]):
            doc = frappe.new_doc("Role")
            doc.update(role)
            doc.insert()

def create_default_document_types():
    """Create default document types for the PWP Project System"""
    document_types = [
        {"document_type_name": "Official Letter", "description": "Official correspondence letters"},
        {"document_type_name": "Memo", "description": "Internal memorandums"},
        {"document_type_name": "Report", "description": "Official reports"},
        {"document_type_name": "Certificate", "description": "Official certificates"},
        {"document_type_name": "Form", "description": "Standard forms"}
    ]

    for doc_type in document_types:
        if not frappe.db.exists("Document Type", doc_type["document_type_name"]):
            doc = frappe.new_doc("Document Type")
            doc.update(doc_type)
            doc.insert()

def create_default_workflows():
    """Create default workflow definitions for the PWP Project System"""
    workflows = [
        {
            "workflow_name": "Document Approval",
            "description": "Standard document approval workflow",
            "document_type": "Document",
            "is_active": 1
        },
        {
            "workflow_name": "Digital Signature",
            "description": "Digital signature approval workflow",
            "document_type": "Document",
            "is_active": 1
        }
    ]

    for workflow in workflows:
        if not frappe.db.exists("Workflow Definition", workflow["workflow_name"]):
            doc = frappe.new_doc("Workflow Definition")
            doc.update(workflow)
            doc.insert()

def setup_default_permissions():
    """Set up default permissions for the PWP Project System"""
    # This function will set up default permissions for different roles
    # Implementation will depend on the specific permission requirements
    pass
