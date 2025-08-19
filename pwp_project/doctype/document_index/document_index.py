# Copyright (c) 2025, Government Agency and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now
from frappe import _

class DocumentIndex(Document):
    def validate(self):
        self.set_indexed_on()
        
    def set_indexed_on(self):
        if not self.indexed_on:
            self.indexed_on = now()
            
    @staticmethod
    def search_documents(query, filters=None, limit=20):
        """
        Search documents using the index
        """
        if not filters:
            filters = {}
            
        # Apply security level filtering based on user role
        if not frappe.has_role("System Manager"):
            filters["security_level"] = ["in", ["Public", "Internal"]]
            
        # Search in title and content
        or_conditions = []
        if query:
            or_conditions = [
                ["title", "like", f"%{query}%"],
                ["content", "like", f"%{query}%"],
                ["tags", "like", f"%{query}%"]
            ]
            
        # Get documents
        if or_conditions:
            documents = frappe.get_all("Document Index",
                filters=filters,
                or_filters=or_conditions,
                fields=["document", "title", "document_type", "status", "security_level", "owner", "indexed_on"],
                order_by="indexed_on desc",
                limit=limit
            )
        else:
            documents = frappe.get_all("Document Index",
                filters=filters,
                fields=["document", "title", "document_type", "status", "security_level", "owner", "indexed_on"],
                order_by="indexed_on desc",
                limit=limit
            )
            
        return documents
        
    @staticmethod
    def rebuild_index():
        """
        Rebuild the entire document index
        """
        # Get all documents
        documents = frappe.get_all("Document", fields=["name"])
        
        # Delete existing index
        frappe.db.delete("Document Index")
        
        # Rebuild index for each document
        for doc in documents:
            try:
                document = frappe.get_doc("Document", doc.name)
                document.update_index()
            except Exception as e:
                frappe.log_error(f"Error rebuilding index for document {doc.name}: {e}", "Document Index Rebuild")
                
        return len(documents)
        
    @staticmethod
    def get_document_suggestions(query, limit=10):
        """
        Get document title suggestions for autocomplete
        """
        if not query or len(query) < 2:
            return []
            
        return frappe.db.sql("""
            SELECT DISTINCT title, document
            FROM `tabDocument Index`
            WHERE title LIKE %s
            ORDER BY title
            LIMIT %s
        """, (f"%{query}%", limit), as_dict=True)
        
    @staticmethod
    def get_popular_tags(limit=20):
        """
        Get popular tags from document index
        """
        tags = {}
        
        # Get all tags
        index_records = frappe.get_all("Document Index", fields=["tags"])
        
        # Count tag occurrences
        for record in index_records:
            if record.tags:
                tag_list = record.tags.split(",")
                for tag in tag_list:
                    tag = tag.strip()
                    if tag:
                        tags[tag] = tags.get(tag, 0) + 1
                        
        # Sort by count and return top tags
        sorted_tags = sorted(tags.items(), key=lambda x: x[1], reverse=True)
        return [tag[0] for tag in sorted_tags[:limit]]
        
    @staticmethod
    def get_documents_by_tag(tag, filters=None, limit=20):
        """
        Get documents by tag
        """
        if not filters:
            filters = {}
            
        # Apply security level filtering based on user role
        if not frappe.has_role("System Manager"):
            filters["security_level"] = ["in", ["Public", "Internal"]]
            
        # Add tag filter
        filters["tags"] = ["like", f"%{tag}%"]
        
        return frappe.get_all("Document Index",
            filters=filters,
            fields=["document", "title", "document_type", "status", "security_level", "owner", "indexed_on"],
            order_by="indexed_on desc",
            limit=limit
        )
        
    @staticmethod
    def cleanup_old_index(days=30):
        """
        Clean up old index entries for documents that no longer exist
        """
        from frappe.utils import add_days
        
        # Get index entries older than specified days
        old_entries = frappe.get_all("Document Index",
            filters={"indexed_on": ["<", add_days(now(), -days)]},
            fields=["name", "document"]
        )
        
        cleaned_count = 0
        for entry in old_entries:
            # Check if document still exists
            if not frappe.db.exists("Document", entry.document):
                frappe.delete_doc("Document Index", entry.name)
                cleaned_count += 1
                
        return cleaned_count