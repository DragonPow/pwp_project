# Copyright (c) 2025, Government Agency and contributors
# For license information, please see license.txt

import frappe
import json
import os
from frappe.model.document import Document
from frappe.utils import now, getdate, add_days, cstr
from frappe import _

class Document(Document):
    def validate(self):
        self.update_last_modified()
        self.validate_security_level()
        self.validate_required_fields()
        self.validate_status_transition()
        self.validate_document_number()
        self.validate_expiry_date()
        self.extract_metadata()
        
    def before_save(self):
        self.update_last_modified()
        self.check_version_creation()
        
    def on_update(self):
        self.create_audit_log("Updated")
        self.update_index()
        self.handle_status_change()
        
    def on_trash(self):
        self.create_audit_log("Deleted")
        self.remove_from_index()
        
    def after_insert(self):
        # Create initial version
        self.create_version("Initial version")
        self.create_audit_log("Created")
        self.update_index()
        self.set_default_security_level()
        
    def update_last_modified(self):
        self.last_modified = frappe.utils.now()
        
    def validate_security_level(self):
        if self.security_level == "Secret" and not frappe.has_role("System Manager"):
            frappe.throw(_("Only System Managers can create Secret level documents"))
            
    def validate_required_fields(self):
        if not self.title:
            frappe.throw(_("Title is required"))
            
        if not self.document_type:
            frappe.throw(_("Document Type is required"))
            
        if not self.document_number:
            frappe.throw(_("Document Number is required"))
            
        # Validate document type specific requirements
        doc_type = frappe.get_doc("Document Type", self.document_type)
        if doc_type and doc_type.require_attachment and not self.attachments:
            frappe.throw(_("This document type requires an attachment"))
            
    def validate_status_transition(self):
        if not self.is_new():
            old_doc = self.get_doc_before_save()
            if old_doc and old_doc.status != self.status:
                self._validate_status_transition(old_doc.status, self.status)
                
    def _validate_status_transition(self, old_status, new_status):
        valid_transitions = {
            "Draft": ["In Review", "Archived"],
            "In Review": ["Approved", "Rejected", "Draft"],
            "Approved": ["Published", "Draft"],
            "Rejected": ["Draft", "Archived"],
            "Published": ["Archived"],
            "Archived": []
        }
        
        if new_status not in valid_transitions.get(old_status, []):
            frappe.throw(_("Cannot change status from {0} to {1}").format(old_status, new_status))
            
    def validate_document_number(self):
        """Validate document number uniqueness"""
        if not self.is_new() and self.has_value_changed("document_number"):
            # Check if document number already exists
            existing_doc = frappe.db.exists("Document", {"document_number": self.document_number})
            if existing_doc and existing_doc != self.name:
                frappe.throw(_("Document Number {0} already exists").format(self.document_number))
                
    def validate_expiry_date(self):
        """Validate expiry date if set"""
        if self.expiry_date and getdate(self.expiry_date) < getdate():
            frappe.throw(_("Expiry Date cannot be in the past"))
            
    def set_default_security_level(self):
        """Set default security level from document type"""
        if self.document_type and not self.security_level:
            doc_type = frappe.get_doc("Document Type", self.document_type)
            if doc_type and doc_type.default_security_level:
                self.security_level = doc_type.default_security_level
                
    def handle_status_change(self):
        """Handle actions when status changes"""
        if not self.is_new():
            old_doc = self.get_doc_before_save()
            if old_doc and old_doc.status != self.status:
                # Create version when status changes
                self.create_version(f"Status changed from {old_doc.status} to {self.status}")
                
                # Send notifications based on status change
                self.send_status_notifications(old_doc.status, self.status)
                
    def send_status_notifications(self, old_status, new_status):
        """Send notifications when status changes"""
        # Get document type to determine reviewers and approvers
        doc_type = frappe.get_doc("Document Type", self.document_type)
        
        if not doc_type:
            return
            
        # Notify reviewers when document moves to In Review
        if new_status == "In Review" and old_status == "Draft":
            self.notify_reviewers(doc_type)
            
        # Notify approvers when document moves to Approved
        elif new_status == "Approved" and old_status == "In Review":
            self.notify_approvers(doc_type)
            
    def notify_reviewers(self, doc_type):
        """Notify reviewers that document needs review"""
        reviewers = []
        
        # Get reviewers from document type
        if doc_type.reviewers:
            for reviewer in doc_type.reviewers:
                if reviewer.user:
                    reviewers.append(reviewer.user)
                    
        # Send notification to each reviewer
        for reviewer in reviewers:
            # Create notification log
            notification = frappe.get_doc({
                "doctype": "Notification Log",
                "for_user": reviewer,
                "subject": _("Document Ready for Review: {0}").format(self.title),
                "message": _(
                    "Document '{0}' (Number: {1}) is ready for your review. "
                    "Please review and take appropriate action."
                ).format(self.title, self.document_number),
                "document_type": "Document",
                "document_name": self.name
            })
            notification.insert(ignore_permissions=True)
            
    def notify_approvers(self, doc_type):
        """Notify approvers that document needs approval"""
        approvers = []
        
        # Get approvers from document type
        if doc_type.approvers:
            for approver in doc_type.approvers:
                if approver.user:
                    approvers.append(approver.user)
                    
        # Send notification to each approver
        for approver in approvers:
            # Create notification log
            notification = frappe.get_doc({
                "doctype": "Notification Log",
                "for_user": approver,
                "subject": _("Document Ready for Approval: {0}").format(self.title),
                "message": _(
                    "Document '{0}' (Number: {1}) has been reviewed and is ready for your approval. "
                    "Please review and take appropriate action."
                ).format(self.title, self.document_number),
                "document_type": "Document",
                "document_name": self.name
            })
            notification.insert(ignore_permissions=True)
            
    def extract_metadata(self):
        """Extract and store metadata from document content and attachments"""
        if not self.meta_data:
            self.meta_data = {}
            
        # Extract text content for indexing
        text_content = self.title
        if self.description:
            text_content += " " + frappe.utils.strip_html(cstr(self.description))
            
        # Store metadata
        self.meta_data.update({
            "word_count": len(text_content.split()),
            "character_count": len(text_content),
            "has_attachment": bool(self.attachments),
            "last_indexed": frappe.utils.now()
        })
        
        # Extract metadata from attachments if available
        if self.attachments:
            self._extract_attachment_metadata()
            
    def _extract_attachment_metadata(self):
        """Extract metadata from attached files"""
        try:
            # This is a placeholder for attachment metadata extraction
            # In a real implementation, this would use libraries like PyPDF, python-docx, etc.
            attachment_metadata = {
                "file_count": 1,  # Simplified for now
                "file_types": ["unknown"],
                "total_size": 0
            }
            
            if isinstance(self.meta_data, str):
                self.meta_data = json.loads(self.meta_data)
                
            self.meta_data.update(attachment_metadata)
        except Exception as e:
            frappe.log_error(f"Error extracting attachment metadata: {e}", "Document Metadata Extraction")
            
    def check_version_creation(self):
        """Check if a new version should be created based on changes"""
        if not self.is_new():
            old_doc = self.get_doc_before_save()
            if old_doc:
                significant_fields = ["title", "description", "document_type"]
                for field in significant_fields:
                    if getattr(old_doc, field) != getattr(self, field):
                        # Will create version after save
                        self._create_version_after_save = True
                        return
                        
    def on_update_after_submit(self):
        """Handle version creation after submit"""
        if hasattr(self, '_create_version_after_save') and self._create_version_after_save:
            self.create_version("Auto-version after significant changes")
            delattr(self, '_create_version_after_save')
            
    def create_audit_log(self, action):
        audit_log = frappe.get_doc({
            "doctype": "Audit Log",
            "document": self.name,
            "action": action,
            "performed_by": frappe.session.user,
            "performed_on": frappe.utils.now(),
            "details": f"Document {self.name} was {action.lower()}",
            "ip_address": frappe.local.request_ip if hasattr(frappe.local, 'request_ip') else "",
            "user_agent": frappe.local.request.headers.get('User-Agent') if hasattr(frappe.local, 'request') and hasattr(frappe.local.request, 'headers') else ""
        })
        audit_log.insert(ignore_permissions=True)
        
    def get_versions(self):
        return frappe.get_all("Document Version",
            filters={"document": self.name},
            fields=["name", "version_number", "version_notes", "created_by", "created_on", "is_current"],
            order_by="version_number desc"
        )
        
    def get_latest_version(self):
        versions = self.get_versions()
        return versions[0] if versions else None
        
    def create_version(self, version_notes=""):
        latest_version = self.get_latest_version()
        version_number = (latest_version.version_number + 1) if latest_version else 1
        
        # Set all previous versions as not current
        frappe.db.set_value("Document Version", {"document": self.name}, "is_current", 0)
        
        # Create content snapshot
        content_snapshot = self.create_content_snapshot()
        
        version = frappe.get_doc({
            "doctype": "Document Version",
            "document": self.name,
            "version_number": version_number,
            "version_description": version_notes,
            "version_date": frappe.utils.now(),
            "created_by": frappe.session.user,
            "content_snapshot": content_snapshot,
            "status": self.status,
            "file_hash": self.generate_file_hash(),
            "is_current": 1
        })
        version.insert()
        return version
        
    def create_content_snapshot(self):
        """Create a snapshot of the document content for versioning"""
        import json
        
        snapshot = {
            "title": self.title,
            "content": self.content,
            "description": self.description,
            "document_type": self.document_type,
            "document_number": self.document_number,
            "document_date": self.document_date,
            "status": self.status,
            "security_level": self.security_level,
            "confidentiality_flag": self.confidentiality_flag,
            "expiry_date": self.expiry_date,
            "tags": self.tags,
            "related_documents": self.related_documents,
            "snapshot_time": frappe.utils.now()
        }
        
        return json.dumps(snapshot, default=str)
        
    def generate_file_hash(self):
        # This is a placeholder for file hash generation
        # In a real implementation, this would calculate a hash of the document content
        import hashlib
        content = f"{self.title}{self.description}{self.document_type}"
        return hashlib.md5(content.encode()).hexdigest()
        
    def update_index(self):
        """Update search index for the document"""
        try:
            # Create or update document index record
            index_name = f"idx-{self.name}"
            
            # Check if index exists
            if frappe.db.exists("Document Index", index_name):
                index_doc = frappe.get_doc("Document Index", index_name)
            else:
                index_doc = frappe.new_doc("Document Index")
                index_doc.name = index_name
                
            # Update index data
            text_content = self.title
            if self.description:
                text_content += " " + frappe.utils.strip_html(cstr(self.description))
                
            index_doc.update({
                "document": self.name,
                "title": self.title,
                "content": text_content,
                "document_type": self.document_type,
                "status": self.status,
                "security_level": self.security_level,
                "owner": self.owner,
                "tags": self.tags,
                "indexed_on": frappe.utils.now()
            })
            
            index_doc.save(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(f"Error updating document index: {e}", "Document Indexing")
            
    def remove_from_index(self):
        """Remove document from search index"""
        try:
            index_name = f"idx-{self.name}"
            if frappe.db.exists("Document Index", index_name):
                frappe.delete_doc("Document Index", index_name)
        except Exception as e:
            frappe.log_error(f"Error removing document from index: {e}", "Document Indexing")
            
    def get_attachments(self):
        """Get all attachments for this document"""
        return frappe.get_all("File",
            filters={
                "attached_to_doctype": "Document",
                "attached_to_name": self.name
            },
            fields=["name", "file_name", "file_url", "file_size", "creation", "file_type"]
        )
        
    def add_attachment(self, file_url, file_name=None, file_size=None, file_type=None):
        """Add an attachment to the document"""
        if not file_name and file_url:
            file_name = file_url.split("/")[-1]
            
        # Create file record
        file_doc = frappe.get_doc({
            "doctype": "File",
            "file_url": file_url,
            "file_name": file_name,
            "attached_to_doctype": "Document",
            "attached_to_name": self.name,
            "is_private": 1 if self.security_level in ["Confidential", "Secret"] else 0
        })
        
        if file_size:
            file_doc.file_size = file_size
            
        if file_type:
            file_doc.file_type = file_type
            
        file_doc.insert()
        
        # Update document metadata
        self.extract_metadata()
        self.save()
        
        return file_doc.name
        
    def remove_attachment(self, attachment_name):
        """Remove an attachment from the document"""
        if frappe.db.exists("File", attachment_name):
            frappe.delete_doc("File", attachment_name)
            
            # Update document metadata
            self.extract_metadata()
            self.save()
            
            return True
        return False
        
    def validate_attachment(self, file_url, file_name=None, file_size=None):
        """Validate attachment against document type restrictions"""
        doc_type = frappe.get_doc("Document Type", self.document_type)
        
        if not doc_type:
            return True
            
        # Check file size
        if doc_type.max_file_size and file_size:
            max_size_bytes = doc_type.max_file_size * 1024 * 1024  # Convert MB to bytes
            if file_size > max_size_bytes:
                frappe.throw(_("File size exceeds maximum allowed size of {0} MB").format(doc_type.max_file_size))
                
        # Check file type
        if doc_type.allowed_file_types and file_name:
            allowed_types = [t.strip().lower() for t in doc_type.allowed_file_types.split(",")]
            file_ext = file_name.split(".")[-1].lower() if "." in file_name else ""
            
            if file_ext and file_ext not in allowed_types:
                frappe.throw(_("File type {0} is not allowed. Allowed types: {1}").format(
                    file_ext, ", ".join(allowed_types)
                ))
                
        return True
        
    def compare_versions(self, version1_name, version2_name):
        """Compare two versions of the document"""
        version1 = frappe.get_doc("Document Version", version1_name)
        version2 = frappe.get_doc("Document Version", version2_name)
        
        # Get document snapshots for each version
        # This is a simplified implementation
        # In a real system, you would store document snapshots with each version
        
        return {
            "version1": {
                "name": version1.name,
                "version_number": version1.version_number,
                "version_notes": version1.version_notes,
                "created_by": version1.created_by,
                "created_on": version1.created_on,
                "file_hash": version1.file_hash
            },
            "version2": {
                "name": version2.name,
                "version_number": version2.version_number,
                "version_notes": version2.version_notes,
                "created_by": version2.created_by,
                "created_on": version2.created_on,
                "file_hash": version2.file_hash
            },
            "differences": {
                "content_changed": version1.file_hash != version2.file_hash,
                "notes_different": version1.version_notes != version2.version_notes
            }
        }
        
    def export_document(self, format="pdf"):
        """Export document in various formats"""
        if format.lower() == "pdf":
            return self._export_as_pdf()
        elif format.lower() == "json":
            return self._export_as_json()
        elif format.lower() == "docx":
            return self._export_as_docx()
        else:
            frappe.throw(_("Unsupported export format: {0}").format(format))
            
    def _export_as_pdf(self):
        """Export document as PDF"""
        # This is a placeholder for PDF export
        # In a real implementation, this would use a PDF generation library
        frappe.msgprint(_("PDF export functionality would be implemented here"))
        return None
        
    def _export_as_json(self):
        """Export document as JSON"""
        doc_data = self.as_dict()
        
        # Add versions
        doc_data["versions"] = self.get_versions()
        
        # Add attachments
        doc_data["attachments"] = self.get_attachments()
        
        # Add audit log
        doc_data["audit_log"] = frappe.get_all("Audit Log",
            filters={"document": self.name},
            fields=["action", "performed_by", "performed_on", "details"],
            order_by="performed_on desc"
        )
        
        return json.dumps(doc_data, indent=2, default=str)
        
    def _export_as_docx(self):
        """Export document as DOCX"""
        # This is a placeholder for DOCX export
        # In a real implementation, this would use python-docx library
        frappe.msgprint(_("DOCX export functionality would be implemented here"))
        return None
        
    def grant_temporary_access(self, user, expiry_hours=24):
        """Grant temporary access to a user"""
        expiry_date = add_days(frappe.utils.now(), expiry_hours/24)
        
        access_grant = frappe.get_doc({
            "doctype": "Document Access Grant",
            "document": self.name,
            "user": user,
            "granted_by": frappe.session.user,
            "granted_on": frappe.utils.now(),
            "expires_on": expiry_date
        })
        access_grant.insert()
        
        # Log the access grant
        self.create_audit_log(f"Temporary Access Granted to {user}")
        
        return access_grant.name
        
    def check_access_permission(self, user=None):
        """Check if a user has permission to access this document"""
        if not user:
            user = frappe.session.user
            
        # System managers have access to everything
        if frappe.has_role("System Manager", user):
            return True
            
        # Document owners have access to their own documents
        if self.owner == user:
            return True
            
        # Check security level
        if self.security_level == "Secret":
            return False
            
        if self.security_level == "Confidential" and not frappe.has_role("System Manager", user):
            return False
            
        # Check for temporary access grants
        active_grants = frappe.get_all("Document Access Grant",
            filters={
                "document": self.name,
                "user": user,
                "expires_on": [">=", frappe.utils.now()]
            }
        )
        
        if active_grants:
            return True
            
        # Default access check
        return frappe.has_permission("Document", "read", user=user)

# Whitelisted methods for client-side calls
@frappe.whitelist()
def create_version(docname, version_notes=""):
    """Create a new version of the document"""
    doc = frappe.get_doc("Document", docname)
    return doc.create_version(version_notes)

@frappe.whitelist()
def get_versions(docname):
    """Get all versions of a document"""
    doc = frappe.get_doc("Document", docname)
    return doc.get_versions()

@frappe.whitelist()
def export_document(docname, format="pdf"):
    """Export document in specified format"""
    doc = frappe.get_doc("Document", docname)
    return doc.export_document(format)

@frappe.whitelist()
def grant_temporary_access(docname, user, expiry_hours=24):
    """Grant temporary access to a user"""
    doc = frappe.get_doc("Document", docname)
    return doc.grant_temporary_access(user, expiry_hours)

@frappe.whitelist()
def add_attachment(docname, file_url, file_name=None, file_size=None, file_type=None):
    """Add an attachment to the document"""
    doc = frappe.get_doc("Document", docname)
    return doc.add_attachment(file_url, file_name, file_size, file_type)

@frappe.whitelist()
def remove_attachment(docname, attachment_name):
    """Remove an attachment from the document"""
    doc = frappe.get_doc("Document", docname)
    return doc.remove_attachment(attachment_name)

@frappe.whitelist()
def get_attachments(docname):
    """Get all attachments for a document"""
    doc = frappe.get_doc("Document", docname)
    return doc.get_attachments()

@frappe.whitelist()
def compare_versions(docname, version1_name, version2_name):
    """Compare two versions of a document"""
    doc = frappe.get_doc("Document", docname)
    return doc.compare_versions(version1_name, version2_name)