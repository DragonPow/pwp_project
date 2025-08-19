# Copyright (c) 2025, Government Agency and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now, add_days
from frappe import _

class DocumentAccessGrant(Document):
    def validate(self):
        self.validate_expiry()
        self.validate_permissions()
        self.set_active_status()
        
    def before_save(self):
        self.notify_user()
        
    def validate_expiry(self):
        """Validate that expiry date is in the future"""
        if self.expires_on and self.expires_on < now():
            frappe.throw(_("Expiry date must be in the future"))
            
    def validate_permissions(self):
        """Validate that the user granting access has permission to do so"""
        if self.granted_by != frappe.session.user and not frappe.has_role("System Manager"):
            frappe.throw(_("You can only create access grants for yourself"))
            
        # Check if user has permission to the document
        doc = frappe.get_doc("Document", self.document)
        if not doc.check_access_permission(self.granted_by):
            frappe.throw(_("You do not have permission to grant access to this document"))
            
    def set_active_status(self):
        """Set active status based on expiry date"""
        if self.expires_on and self.expires_on < now():
            self.is_active = 0
        else:
            self.is_active = 1
            
    def notify_user(self):
        """Notify the user about the access grant"""
        if self.is_new():
            # Get document details
            doc = frappe.get_doc("Document", self.document)
            
            # Create notification
            notification = frappe.get_doc({
                "doctype": "Notification Log",
                "subject": _("Access Granted to Document: {0}").format(doc.title),
                "for_user": self.user,
                "type": "Alert",
                "document_type": "Document",
                "document_name": self.document,
                "email_content": _("""
                    <p>You have been granted temporary access to a document:</p>
                    <p><strong>Title:</strong> {0}</p>
                    <p><strong>Type:</strong> {1}</p>
                    <p><strong>Granted By:</strong> {2}</p>
                    <p><strong>Expires On:</strong> {3}</p>
                    <p><strong>Reason:</strong> {4}</p>
                    <p>You can access the document <a href="/app/document/{5}">here</a>.</p>
                """).format(
                    doc.title, 
                    doc.document_type, 
                    self.granted_by, 
                    self.expires_on, 
                    self.reason or _("Not specified"),
                    self.document
                )
            })
            notification.insert(ignore_permissions=True)
            
    @staticmethod
    def get_active_grants_for_user(user):
        """Get all active access grants for a user"""
        return frappe.get_all("Document Access Grant",
            filters={
                "user": user,
                "is_active": 1,
                "expires_on": [">=", now()]
            },
            fields=["name", "document", "granted_by", "granted_on", "expires_on", "reason"]
        )
        
    @staticmethod
    def get_grants_for_document(document):
        """Get all access grants for a document"""
        return frappe.get_all("Document Access Grant",
            filters={"document": document},
            fields=["name", "user", "granted_by", "granted_on", "expires_on", "reason", "is_active"]
        )
        
    @staticmethod
    def check_access_permission(document, user):
        """Check if a user has access to a document through grants"""
        active_grants = frappe.get_all("Document Access Grant",
            filters={
                "document": document,
                "user": user,
                "is_active": 1,
                "expires_on": [">=", now()]
            }
        )
        
        return len(active_grants) > 0
        
    @staticmethod
    def cleanup_expired_grants():
        """Clean up expired access grants"""
        expired_grants = frappe.get_all("Document Access Grant",
            filters={"expires_on": ["<", now()]},
            fields=["name"]
        )
        
        count = 0
        for grant in expired_grants:
            frappe.delete_doc("Document Access Grant", grant.name)
            count += 1
            
        return count
        
    @staticmethod
    def revoke_grant(grant_name, reason=""):
        """Revoke an access grant"""
        grant = frappe.get_doc("Document Access Grant", grant_name)
        
        # Log the revocation
        frappe.get_doc("Audit Log").log_action(
            document_name=grant.document,
            action="Access Revoked",
            details=f"Access grant for user {grant.user} was revoked by {frappe.session.user}. Reason: {reason}"
        )
        
        # Delete the grant
        grant.delete()
        
        return True