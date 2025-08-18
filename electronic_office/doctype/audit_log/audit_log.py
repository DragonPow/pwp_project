# Copyright (c) 2025, Government Agency and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import json

class AuditLog(Document):
    def validate(self):
        self.set_performed_fields()
        self.capture_request_info()
        
    def set_performed_fields(self):
        if not self.performed_by:
            self.performed_by = frappe.session.user
        if not self.performed_on:
            self.performed_on = frappe.utils.now()
            
    def capture_request_info(self):
        # Capture IP address and user agent from request
        if hasattr(frappe.local, 'request_ip') and frappe.local.request_ip:
            self.ip_address = frappe.local.request_ip
            
        if hasattr(frappe.local, 'request') and hasattr(frappe.local.request, 'headers'):
            user_agent = frappe.local.request.headers.get('User-Agent')
            if user_agent:
                self.user_agent = user_agent[:140]  # Limit to 140 characters
                
    def get_document_info(self):
        if self.document:
            return frappe.get_doc("Document", self.document)
        return None
        
    def get_user_info(self):
        if self.performed_by:
            return frappe.get_doc("User", self.performed_by)
        return None
        
    @staticmethod
    def log_action(document_name, action, details="", performed_by=None, performed_on=None):
        """
        Static method to create audit log entries
        """
        if not performed_by:
            performed_by = frappe.session.user
        if not performed_on:
            performed_on = frappe.utils.now()
            
        audit_log = frappe.get_doc({
            "doctype": "Audit Log",
            "document": document_name,
            "action": action,
            "performed_by": performed_by,
            "performed_on": performed_on,
            "details": details,
            "ip_address": frappe.local.request_ip if hasattr(frappe.local, 'request_ip') else "",
            "user_agent": frappe.local.request.headers.get('User-Agent') if hasattr(frappe.local, 'request') and hasattr(frappe.local.request, 'headers') else ""
        })
        audit_log.insert(ignore_permissions=True)
        return audit_log.name
        
    @staticmethod
    def get_document_history(document_name, limit=50):
        """
        Get audit log history for a specific document
        """
        return frappe.get_all("Audit Log",
            filters={"document": document_name},
            fields=["name", "action", "performed_by", "performed_on", "details", "ip_address"],
            order_by="performed_on desc",
            limit=limit
        )
        
    @staticmethod
    def get_user_activity(user, limit=50):
        """
        Get audit log entries for a specific user
        """
        return frappe.get_all("Audit Log",
            filters={"performed_by": user},
            fields=["name", "document", "action", "performed_on", "details", "ip_address"],
            order_by="performed_on desc",
            limit=limit
        )
        
    @staticmethod
    def get_activity_by_date_range(start_date, end_date, limit=100):
        """
        Get audit log entries within a date range
        """
        return frappe.get_all("Audit Log",
            filters={
                "performed_on": [">=", start_date],
                "performed_on": ["<=", end_date]
            },
            fields=["name", "document", "action", "performed_by", "performed_on", "details"],
            order_by="performed_on desc",
            limit=limit
        )
        
    @staticmethod
    def get_security_events(limit=50):
        """
        Get security-related audit events
        """
        security_actions = [
            "Login Failed",
            "Password Changed",
            "User Created",
            "User Deleted",
            "Role Changed",
            "Permission Changed",
            "Document Access Denied",
            "Signature Verification Failed",
            "Document Version Reverted"
        ]
        
        return frappe.get_all("Audit Log",
            filters={"action": ["in", security_actions]},
            fields=["name", "document", "action", "performed_by", "performed_on", "details", "ip_address"],
            order_by="performed_on desc",
            limit=limit
        )
        
    @staticmethod
    def export_audit_log(filters=None, format="csv"):
        """
        Export audit log data with optional filters
        """
        if not filters:
            filters = {}
            
        fields = ["name", "document", "action", "performed_by", "performed_on", "details", "ip_address", "user_agent"]
        data = frappe.get_all("Audit Log", filters=filters, fields=fields, order_by="performed_on desc")
        
        if format == "csv":
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(fields)
            
            for row in data:
                writer.writerow([row[field] for field in fields])
                
            return output.getvalue()
        elif format == "json":
            return json.dumps(data, indent=2, default=str)
        else:
            frappe.throw("Unsupported export format")