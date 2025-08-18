# Copyright (c) 2025, Government Agency and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now, add_days
from frappe import _

class DocumentType(Document):
    def validate(self):
        self.validate_name()
        self.validate_file_types()
        
    def validate_name(self):
        """Validate that document type name is unique"""
        if self.is_new():
            existing = frappe.db.exists("Document Type", {"document_type_name": self.document_type_name})
            if existing:
                frappe.throw(_("Document Type with name {0} already exists").format(self.document_type_name))
                
    def validate_file_types(self):
        """Validate allowed file types format"""
        if self.allowed_file_types:
            # Check if it's a comma-separated list of file extensions
            file_types = [ft.strip() for ft in self.allowed_file_types.split(",")]
            for ft in file_types:
                if ft and not ft.startswith("."):
                    # Add dot if missing
                    pass
                    
    def get_reviewers(self):
        """Get list of reviewers for this document type"""
        if not self.reviewers:
            return []
            
        reviewers = []
        for reviewer in self.reviewers:
            if reviewer.reviewer:
                reviewers.append(reviewer.reviewer)
                
        return reviewers
        
    def get_approvers(self):
        """Get list of approvers for this document type"""
        if not self.approvers:
            return []
            
        approvers = []
        for approver in self.approvers:
            if approver.approver:
                approvers.append(approver.approver)
                
        return approvers
        
    @staticmethod
    def get_active_document_types():
        """Get all active document types"""
        return frappe.get_all("Document Type",
            filters={"is_active": 1},
            fields=["name", "document_type_name", "icon", "color", "default_security_level"],
            order_by="document_type_name"
        )
        
    @staticmethod
    def get_document_type_by_name(name):
        """Get document type by name"""
        return frappe.get_doc("Document Type", {"document_type_name": name})
        
    @staticmethod
    def auto_archive_documents():
        """Auto-archive documents based on document type settings"""
        document_types = frappe.get_all("Document Type",
            filters={"is_active": 1, "auto_archive_days": [">", 0]},
            fields=["name", "document_type_name", "auto_archive_days"]
        )
        
        archived_count = 0
        for doc_type in document_types:
            # Get documents that should be archived
            archive_date = add_days(now(), -doc_type.auto_archive_days)
            documents = frappe.get_all("Document",
                filters={
                    "document_type": doc_type.name,
                    "status": ["in", ["Approved", "Published"]],
                    "creation_date": ["<", archive_date]
                },
                fields=["name", "title"]
            )
            
            # Archive each document
            for doc in documents:
                try:
                    document = frappe.get_doc("Document", doc.name)
                    document.status = "Archived"
                    document.save()
                    
                    # Log the archival
                    frappe.get_doc("Audit Log").log_action(
                        document_name=doc.name,
                        action="Auto Archived",
                        details=f"Document '{doc.title}' was automatically archived after {doc_type.auto_archive_days} days"
                    )
                    
                    archived_count += 1
                except Exception as e:
                    frappe.log_error(f"Error auto-archiving document {doc.name}: {e}", "Document Auto Archive")
                    
        return archived_count
        
    @staticmethod
    def notify_reviewers(document_name):
        """Notify reviewers when a document is submitted for review"""
        doc = frappe.get_doc("Document", document_name)
        doc_type = frappe.get_doc("Document Type", doc.document_type)
        
        reviewers = doc_type.get_reviewers()
        for reviewer in reviewers:
            # Create notification
            notification = frappe.get_doc({
                "doctype": "Notification Log",
                "subject": _("Document Submitted for Review: {0}").format(doc.title),
                "for_user": reviewer,
                "type": "Alert",
                "document_type": "Document",
                "document_name": doc.name,
                "email_content": _("""
                    <p>A document has been submitted for your review:</p>
                    <p><strong>Title:</strong> {0}</p>
                    <p><strong>Type:</strong> {1}</p>
                    <p><strong>Owner:</strong> {2}</p>
                    <p><strong>Security Level:</strong> {3}</p>
                    <p>Please review the document <a href="/app/document/{4}">here</a>.</p>
                """).format(doc.title, doc.document_type, doc.owner, doc.security_level, doc.name)
            })
            notification.insert(ignore_permissions=True)
            
    @staticmethod
    def notify_approvers(document_name):
        """Notify approvers when a document is submitted for approval"""
        doc = frappe.get_doc("Document", document_name)
        doc_type = frappe.get_doc("Document Type", doc.document_type)
        
        approvers = doc_type.get_approvers()
        for approver in approvers:
            # Create notification
            notification = frappe.get_doc({
                "doctype": "Notification Log",
                "subject": _("Document Submitted for Approval: {0}").format(doc.title),
                "for_user": approver,
                "type": "Alert",
                "document_type": "Document",
                "document_name": doc.name,
                "email_content": _("""
                    <p>A document has been submitted for your approval:</p>
                    <p><strong>Title:</strong> {0}</p>
                    <p><strong>Type:</strong> {1}</p>
                    <p><strong>Owner:</strong> {2}</p>
                    <p><strong>Security Level:</strong> {3}</p>
                    <p>Please approve or reject the document <a href="/app/document/{4}">here</a>.</p>
                """).format(doc.title, doc.document_type, doc.owner, doc.security_level, doc.name)
            })
            notification.insert(ignore_permissions=True)