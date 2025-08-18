# Copyright (c) 2025, Government Agency and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class DocumentVersion(Document):
    def validate(self):
        self.validate_version_number()
        self.set_created_fields()
        self.validate_content_snapshot()
        
    def before_save(self):
        self.ensure_only_one_current_version()
        
    def on_update(self):
        self.create_audit_log("Updated")
        
    def on_trash(self):
        self.create_audit_log("Deleted")
        
    def validate_version_number(self):
        if not self.version_number:
            # Get the highest version number for this document
            latest_version = frappe.db.get_value("Document Version",
                {"document": self.document},
                "MAX(version_number)")
            self.version_number = (latest_version or 0) + 1
            
    def set_created_fields(self):
        if not self.created_by:
            self.created_by = frappe.session.user
        if not self.created_on:
            self.created_on = frappe.utils.now()
        if not self.version_date:
            self.version_date = frappe.utils.now()
            
    def validate_content_snapshot(self):
        """Validate content snapshot if provided"""
        if self.content_snapshot:
            try:
                import json
                snapshot = json.loads(self.content_snapshot)
                
                # Validate required fields in snapshot
                required_fields = ["title", "content", "document_type", "document_number"]
                for field in required_fields:
                    if field not in snapshot:
                        frappe.throw(_("Content snapshot is missing required field: {0}").format(field))
                        
            except json.JSONDecodeError:
                frappe.throw(_("Invalid JSON in content snapshot"))
            
    def ensure_only_one_current_version(self):
        if self.is_current:
            # Set all other versions of this document as not current
            frappe.db.set_value("Document Version", 
                {"document": self.document, "name": ["!=", self.name]}, 
                "is_current", 0)
                
    def create_audit_log(self, action):
        audit_log = frappe.get_doc({
            "doctype": "Audit Log",
            "document": self.document,
            "action": f"Document Version {action}",
            "performed_by": frappe.session.user,
            "performed_on": frappe.utils.now(),
            "details": f"Document Version {self.name} (Version {self.version_number}) was {action.lower()}",
            "ip_address": frappe.local.request_ip if hasattr(frappe.local, 'request_ip') else "",
            "user_agent": frappe.local.request.headers.get('User-Agent') if hasattr(frappe.local, 'request') and hasattr(frappe.local.request, 'headers') else ""
        })
        audit_log.insert(ignore_permissions=True)
        
    def set_as_current(self):
        # Set all other versions as not current
        frappe.db.set_value("Document Version",
            {"document": self.document, "name": ["!=", self.name]},
            "is_current", 0)
        
        # Set this version as current
        self.is_current = 1
        self.save()
        
        # Update document status to match this version
        if self.status:
            doc = frappe.get_doc("Document", self.document)
            doc.status = self.status
            doc.save()
        
    def get_document_info(self):
        return frappe.get_doc("Document", self.document)
        
    def get_previous_version(self):
        return frappe.get_value("Document Version",
            {"document": self.document, "version_number": self.version_number - 1},
            ["name", "version_number", "version_description", "created_by", "created_on"])
            
    def get_next_version(self):
        return frappe.get_value("Document Version",
            {"document": self.document, "version_number": self.version_number + 1},
            ["name", "version_number", "version_description", "created_by", "created_on"])
            
    def restore_to_document(self):
        """Restore this version to the parent document"""
        if not self.content_snapshot:
            frappe.throw(_("This version does not have a content snapshot"))
            
        try:
            import json
            snapshot = json.loads(self.content_snapshot)
            
            # Get the parent document
            doc = frappe.get_doc("Document", self.document)
            
            # Update document fields from snapshot
            doc.title = snapshot.get("title", doc.title)
            doc.content = snapshot.get("content", doc.content)
            doc.description = snapshot.get("description", doc.description)
            doc.document_type = snapshot.get("document_type", doc.document_type)
            doc.document_number = snapshot.get("document_number", doc.document_number)
            doc.document_date = snapshot.get("document_date", doc.document_date)
            doc.status = snapshot.get("status", doc.status)
            doc.security_level = snapshot.get("security_level", doc.security_level)
            doc.confidentiality_flag = snapshot.get("confidentiality_flag", doc.confidentiality_flag)
            doc.expiry_date = snapshot.get("expiry_date", doc.expiry_date)
            doc.tags = snapshot.get("tags", doc.tags)
            doc.related_documents = snapshot.get("related_documents", doc.related_documents)
            
            # Save the document
            doc.save()
            
            # Create a new version to track the restoration
            doc.create_version(f"Restored from version {self.version_number}")
            
            # Set this version as current
            self.set_as_current()
            
            return doc.name
            
        except json.JSONDecodeError:
            frappe.throw(_("Invalid JSON in content snapshot"))
        except Exception as e:
            frappe.log_error(f"Error restoring version: {e}", "Document Version Restore")
            frappe.throw(_("Error restoring version: {0}").format(str(e)))
            
    def compare_with_version(self, other_version_name):
        """Compare this version with another version"""
        other_version = frappe.get_doc("Document Version", other_version_name)
        
        if not self.content_snapshot or not other_version.content_snapshot:
            frappe.throw(_("Both versions must have content snapshots to compare"))
            
        try:
            import json
            this_snapshot = json.loads(self.content_snapshot)
            other_snapshot = json.loads(other_version.content_snapshot)
            
            # Compare fields
            differences = {}
            
            for field in ["title", "content", "description", "document_type",
                         "document_number", "document_date", "status", "security_level"]:
                if this_snapshot.get(field) != other_snapshot.get(field):
                    differences[field] = {
                        "this_version": this_snapshot.get(field),
                        "other_version": other_snapshot.get(field)
                    }
                    
            return {
                "version1": {
                    "name": self.name,
                    "version_number": self.version_number,
                    "version_description": self.version_description,
                    "created_by": self.created_by,
                    "created_on": self.created_on
                },
                "version2": {
                    "name": other_version.name,
                    "version_number": other_version.version_number,
                    "version_description": other_version.version_description,
                    "created_by": other_version.created_by,
                    "created_on": other_version.created_on
                },
                "differences": differences
            }
            
        except json.JSONDecodeError:
            frappe.throw(_("Invalid JSON in content snapshot"))
        except Exception as e:
            frappe.log_error(f"Error comparing versions: {e}", "Document Version Compare")
            frappe.throw(_("Error comparing versions: {0}").format(str(e)))

# Whitelisted methods for client-side calls
@frappe.whitelist()
def set_as_current(docname):
    """Set a version as the current version"""
    version = frappe.get_doc("Document Version", docname)
    version.set_as_current()
    return True

@frappe.whitelist()
def get_previous_version(docname):
    """Get the previous version of a document version"""
    version = frappe.get_doc("Document Version", docname)
    return version.get_previous_version()

@frappe.whitelist()
def get_next_version(docname):
    """Get the next version of a document version"""
    version = frappe.get_doc("Document Version", docname)
    return version.get_next_version()

@frappe.whitelist()
def restore_to_document(docname):
    """Restore a version to the parent document"""
    version = frappe.get_doc("Document Version", docname)
    return version.restore_to_document()

@frappe.whitelist()
def compare_with_version(docname, other_version_name):
    """Compare this version with another version"""
    version = frappe.get_doc("Document Version", docname)
    return version.compare_with_version(other_version_name)