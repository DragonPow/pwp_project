# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe

def before_uninstall():
    """
    Function to be executed before the app is uninstalled.
    This function performs cleanup operations before removing the Electronic Office System.
    """
    # Check if there are any active documents
    if has_active_documents():
        frappe.throw("Cannot uninstall Electronic Office System. There are active documents in the system.")
    
    # Check if there are any pending workflows
    if has_pending_workflows():
        frappe.throw("Cannot uninstall Electronic Office System. There are pending workflows in the system.")

def after_uninstall():
    """
    Function to be executed after the app is uninstalled.
    This function performs final cleanup operations after removing the Electronic Office System.
    """
    # Clean up any remaining data
    cleanup_remaining_data()
    
    frappe.msgprint("Electronic Office System has been uninstalled successfully!")

def has_active_documents():
    """Check if there are any active documents in the system"""
    # Check for active documents
    count = frappe.db.count("Document", {"docstatus": ["!=", 2]})
    return count > 0

def has_pending_workflows():
    """Check if there are any pending workflows in the system"""
    # Check for pending workflows
    count = frappe.db.count("Workflow Instance", {"status": ["in", ["Pending", "In Progress"]]})
    return count > 0

def cleanup_remaining_data():
    """Clean up any remaining data after uninstallation"""
    # This function will clean up any remaining data that might be left after uninstallation
    # Implementation will depend on the specific cleanup requirements
    pass