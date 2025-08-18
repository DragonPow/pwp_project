# Copyright (c) 2025, Government Agency and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class Tag(Document):
    def validate(self):
        self.validate_name()
        
    def validate_name(self):
        """Validate that tag name is unique"""
        if self.is_new():
            existing = frappe.db.exists("Tag", {"tag": self.tag})
            if existing:
                frappe.throw(_("Tag with name {0} already exists").format(self.tag))
                
    @staticmethod
    def get_active_tags():
        """Get all active tags"""
        return frappe.get_all("Tag",
            filters={"is_active": 1},
            fields=["name", "tag", "description", "color"],
            order_by="tag"
        )
        
    @staticmethod
    def get_popular_tags(limit=20):
        """Get popular tags based on usage in documents"""
        # This is a simplified implementation
        # In a real system, you would count tag usage in documents
        return frappe.get_all("Tag",
            filters={"is_active": 1},
            fields=["name", "tag", "description", "color"],
            order_by="tag",
            limit=limit
        )
        
    @staticmethod
    def get_documents_by_tag(tag_name, limit=20):
        """Get documents by tag"""
        # This is a simplified implementation
        # In a real system, you would query documents with this tag
        return frappe.get_all("Document",
            filters={"tags": ["like", f"%{tag_name}%"]},
            fields=["name", "title", "document_type", "status", "security_level", "owner"],
            order_by="modified desc",
            limit=limit
        )