# Copyright (c) 2025, Government Agency and contributors
# For license information, please see license.txt

import frappe
import json
from frappe import _
from frappe.utils import now, getdate, add_days
from frappe.model.document import Document
from pwp_project.pwp_project.doctype.document.document import Document
from pwp_project.pwp_project.doctype.document_version.document_version import DocumentVersion

@frappe.whitelist()
def get_document(document_name):
    """
    Get a document by name with permissions check
    """
    # Check if user has permission to read this document
    if not frappe.has_permission("Document", "read", document_name):
        frappe.throw(_("Not permitted to read document: {0}").format(document_name))

    # Get the document
    doc = frappe.get_doc("Document", document_name)

    # Get document versions
    versions = frappe.get_all("Document Version",
        filters={"document": document_name},
        fields=["name", "version_number", "version_notes", "created_by", "created_on", "is_current"],
        order_by="version_number desc"
    )

    # Get audit log
    audit_logs = frappe.get_all("Audit Log",
        filters={"document": document_name},
        fields=["name", "action", "performed_by", "performed_on", "details"],
        order_by="performed_on desc",
        limit=20
    )

    # Prepare response
    response = {
        "document": doc.as_dict(),
        "versions": versions,
        "audit_logs": audit_logs
    }

    return response

@frappe.whitelist()
def create_document(**kwargs):
    """
    Create a new document with validation and initial version creation
    """
    # Check if user has permission to create documents
    if not frappe.has_permission("Document", "create"):
        frappe.throw(_("Not permitted to create documents"))

    # Extract document data from kwargs
    doc_data = {
        "doctype": "Document",
        "title": kwargs.get("title"),
        "description": kwargs.get("description"),
        "document_type": kwargs.get("document_type"),
        "security_level": kwargs.get("security_level", "Internal"),
        "tags": kwargs.get("tags", []),
        "status": "Draft"
    }

    # Validate required fields
    if not doc_data.get("title"):
        frappe.throw(_("Title is required"))

    # Create the document
    doc = frappe.get_doc(doc_data)
    doc.insert()

    # Create initial version
    version_notes = kwargs.get("version_notes", "Initial version")
    doc.create_version(version_notes)

    # Log the creation
    frappe.get_doc("Audit Log").log_action(
        document_name=doc.name,
        action="Created",
        details=f"Document '{doc.title}' created with initial version"
    )

    # Send notification to relevant users
    send_document_notification(doc.name, "created")

    return {
        "status": "success",
        "message": _("Document created successfully"),
        "document": doc.name
    }

@frappe.whitelist()
def update_document(document_name, **kwargs):
    """
    Update a document with version tracking and change logging
    """
    # Check if user has permission to write this document
    if not frappe.has_permission("Document", "write", document_name):
        frappe.throw(_("Not permitted to update document: {0}").format(document_name))

    # Get the document
    doc = frappe.get_doc("Document", document_name)

    # Store old values for change tracking
    old_values = {
        "title": doc.title,
        "description": doc.description,
        "document_type": doc.document_type,
        "security_level": doc.security_level,
        "status": doc.status,
        "tags": doc.tags
    }

    # Update fields
    if "title" in kwargs:
        doc.title = kwargs.get("title")
    if "description" in kwargs:
        doc.description = kwargs.get("description")
    if "document_type" in kwargs:
        doc.document_type = kwargs.get("document_type")
    if "security_level" in kwargs:
        doc.security_level = kwargs.get("security_level")
    if "status" in kwargs:
        doc.status = kwargs.get("status")
    if "tags" in kwargs:
        doc.tags = kwargs.get("tags")

    # Validate status transitions
    validate_status_transition(old_values["status"], doc.status)

    # Save the document
    doc.save()

    # Check if significant changes were made to create a new version
    if should_create_version(old_values, doc.as_dict()):
        version_notes = kwargs.get("version_notes", "Updated document")
        doc.create_version(version_notes)

    # Log the update
    frappe.get_doc("Audit Log").log_action(
        document_name=doc.name,
        action="Updated",
        details=f"Document '{doc.title}' updated"
    )

    # Send notifications based on status changes
    if old_values["status"] != doc.status:
        send_document_notification(doc.name, f"status_changed_to_{doc.status.lower()}")

    return {
        "status": "success",
        "message": _("Document updated successfully"),
        "document": doc.name
    }

@frappe.whitelist()
def delete_document(document_name):
    """
    Delete a document with proper checks and archival
    """
    # Check if user has permission to delete this document
    if not frappe.has_permission("Document", "delete", document_name):
        frappe.throw(_("Not permitted to delete document: {0}").format(document_name))

    # Get the document
    doc = frappe.get_doc("Document", document_name)

    # Check if document can be deleted (not in certain states)
    if doc.status in ["Approved", "Published"]:
        frappe.throw(_("Cannot delete {0} documents").format(doc.status))

    # Log the deletion before actually deleting
    frappe.get_doc("Audit Log").log_action(
        document_name=doc.name,
        action="Deleted",
        details=f"Document '{doc.title}' deleted by {frappe.session.user}"
    )

    # Delete the document (this will trigger on_trash)
    doc.delete()

    return {
        "status": "success",
        "message": _("Document deleted successfully")
    }

@frappe.whitelist()
def list_documents(filters=None, fields=None, order_by="modified", order="desc", limit=20, page=1):
    """
    List documents with filtering and pagination
    """
    # Check if user has permission to read documents
    if not frappe.has_permission("Document", "read"):
        frappe.throw(_("Not permitted to read documents"))

    # Prepare filters
    if not filters:
        filters = {}

    # Apply security level filtering based on user role
    if not frappe.has_role("System Manager"):
        filters["security_level"] = ["in", ["Public", "Internal"]]

    # Prepare fields
    if not fields:
        fields = ["name", "title", "document_type", "status", "security_level", "owner", "creation_date", "last_modified"]

    # Calculate offset for pagination
    offset = (page - 1) * limit

    # Get documents
    documents = frappe.get_all("Document",
        filters=filters,
        fields=fields,
        order_by=f"{order_by} {order}",
        limit=limit,
        start=offset
    )

    # Get total count for pagination
    total_count = frappe.db.count("Document", filters=filters)

    return {
        "documents": documents,
        "total_count": total_count,
        "page": page,
        "limit": limit,
        "total_pages": (total_count + limit - 1) // limit
    }

@frappe.whitelist()
def search_documents(query, filters=None, fields=None, limit=20):
    """
    Search documents by text query with optional filters
    """
    # Check if user has permission to read documents
    if not frappe.has_permission("Document", "read"):
        frappe.throw(_("Not permitted to read documents"))

    # Prepare filters
    if not filters:
        filters = {}

    # Apply security level filtering based on user role
    if not frappe.has_role("System Manager"):
        filters["security_level"] = ["in", ["Public", "Internal"]]

    # Prepare fields
    if not fields:
        fields = ["name", "title", "document_type", "status", "security_level", "owner", "creation_date", "last_modified"]

    # Search in title and description
    or_filters = [
        ["Document", "title", "like", f"%{query}%"],
        ["Document", "description", "like", f"%{query}%"]
    ]

    # Get documents
    documents = frappe.get_all("Document",
        filters=filters,
        or_filters=or_filters,
        fields=fields,
        order_by="modified desc",
        limit=limit
    )

    return {
        "documents": documents,
        "query": query,
        "count": len(documents)
    }

@frappe.whitelist()
def upload_attachment(document_name, file_url, file_name=None):
    """
    Upload an attachment to a document
    """
    # Check if user has permission to write this document
    if not frappe.has_permission("Document", "write", document_name):
        frappe.throw(_("Not permitted to update document: {0}").format(document_name))

    # Get the document
    doc = frappe.get_doc("Document", document_name)

    # Create file record
    file_doc = frappe.get_doc({
        "doctype": "File",
        "file_url": file_url,
        "file_name": file_name or file_url.split("/")[-1],
        "attached_to_doctype": "Document",
        "attached_to_name": document_name,
        "is_private": 1 if doc.security_level in ["Confidential", "Secret"] else 0
    })
    file_doc.insert()

    # Log the attachment
    frappe.get_doc("Audit Log").log_action(
        document_name=doc.name,
        action="Attachment Added",
        details=f"File '{file_doc.file_name}' attached to document"
    )

    # Create a new version of the document with the attachment
    doc.create_version(f"Attachment added: {file_doc.file_name}")

    return {
        "status": "success",
        "message": _("File attached successfully"),
        "file": file_doc.name
    }

@frappe.whitelist()
def download_attachment(file_name):
    """
    Download an attachment from a document
    """
    # Get the file
    file_doc = frappe.get_doc("File", file_name)

    # Check if user has permission to read the document this file is attached to
    if not frappe.has_permission("Document", "read", file_doc.attached_to_name):
        frappe.throw(_("Not permitted to access this file"))

    # Get the document to check security level
    doc = frappe.get_doc("Document", file_doc.attached_to_name)

    # Log the download
    frappe.get_doc("Audit Log").log_action(
        document_name=doc.name,
        action="Attachment Downloaded",
        details=f"File '{file_doc.file_name}' downloaded by {frappe.session.user}"
    )

    return {
        "file_url": file_doc.file_url,
        "file_name": file_doc.file_name
    }

def validate_status_transition(old_status, new_status):
    """
    Validate that status transitions are allowed
    """
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

def should_create_version(old_values, new_values):
    """
    Check if changes are significant enough to create a new version
    """
    significant_fields = ["title", "description", "document_type"]

    for field in significant_fields:
        if old_values.get(field) != new_values.get(field):
            return True

    return False

def send_document_notification(document_name, event):
    """
    Send notifications based on document events
    """
    doc = frappe.get_doc("Document", document_name)

    # Get recipients based on event
    recipients = []

    if event == "created":
        # Notify document owner
        recipients.append(doc.owner)

        # Notify system managers
        system_managers = frappe.get_all("User",
            filters={"role_profile_name": "System Manager"},
            fields=["name"]
        )
        recipients.extend([sm.name for sm in system_managers])

    elif event == "status_changed_to_in_review":
        # Notify reviewers based on document type
        # This would be configured in Document Type doctype
        pass

    elif event == "status_changed_to_approved":
        # Notify document owner
        recipients.append(doc.owner)

    elif event == "status_changed_to_rejected":
        # Notify document owner
        recipients.append(doc.owner)

    # Remove duplicates
    recipients = list(set(recipients))

    # Send notifications
    for recipient in recipients:
        # Create notification
        notification = frappe.get_doc({
            "doctype": "Notification Log",
            "subject": get_notification_subject(doc, event),
            "for_user": recipient,
            "type": "Alert",
            "document_type": "Document",
            "document_name": doc.name,
            "email_content": get_notification_content(doc, event)
        })
        notification.insert(ignore_permissions=True)

def get_notification_subject(doc, event):
    """
    Get notification subject based on event
    """
    subjects = {
        "created": _("New Document Created: {0}").format(doc.title),
        "status_changed_to_in_review": _("Document Submitted for Review: {0}").format(doc.title),
        "status_changed_to_approved": _("Document Approved: {0}").format(doc.title),
        "status_changed_to_rejected": _("Document Rejected: {0}").format(doc.title),
        "status_changed_to_published": _("Document Published: {0}").format(doc.title),
        "status_changed_to_archived": _("Document Archived: {0}").format(doc.title)
    }

    return subjects.get(event, _("Document Update: {0}").format(doc.title))

def get_notification_content(doc, event):
    """
    Get notification content based on event
    """
    contents = {
        "created": _("""
            <p>A new document has been created:</p>
            <p><strong>Title:</strong> {0}</p>
            <p><strong>Type:</strong> {1}</p>
            <p><strong>Owner:</strong> {2}</p>
            <p><strong>Security Level:</strong> {3}</p>
            <p>You can view the document <a href="/app/document/{4}">here</a>.</p>
        """).format(doc.title, doc.document_type, doc.owner, doc.security_level, doc.name),

        "status_changed_to_in_review": _("""
            <p>A document has been submitted for review:</p>
            <p><strong>Title:</strong> {0}</p>
            <p><strong>Type:</strong> {1}</p>
            <p><strong>Owner:</strong> {2}</p>
            <p><strong>Security Level:</strong> {3}</p>
            <p>Please review the document <a href="/app/document/{4}">here</a>.</p>
        """).format(doc.title, doc.document_type, doc.owner, doc.security_level, doc.name),

        "status_changed_to_approved": _("""
            <p>Your document has been approved:</p>
            <p><strong>Title:</strong> {0}</p>
            <p><strong>Type:</strong> {1}</p>
            <p>You can view the document <a href="/app/document/{2}">here</a>.</p>
        """).format(doc.title, doc.document_type, doc.name),

        "status_changed_to_rejected": _("""
            <p>Your document has been rejected:</p>
            <p><strong>Title:</strong> {0}</p>
            <p><strong>Type:</strong> {1}</p>
            <p>Please review and make necessary changes. You can view the document <a href="/app/document/{2}">here</a>.</p>
        """).format(doc.title, doc.document_type, doc.name),

        "status_changed_to_published": _("""
            <p>A document has been published:</p>
            <p><strong>Title:</strong> {0}</p>
            <p><strong>Type:</strong> {1}</p>
            <p><strong>Owner:</strong> {2}</p>
            <p>You can view the document <a href="/app/document/{3}">here</a>.</p>
        """).format(doc.title, doc.document_type, doc.owner, doc.name),

        "status_changed_to_archived": _("""
            <p>A document has been archived:</p>
            <p><strong>Title:</strong> {0}</p>
            <p><strong>Type:</strong> {1}</p>
            <p><strong>Owner:</strong> {2}</p>
            <p>You can view the document <a href="/app/document/{3}">here</a>.</p>
        """).format(doc.title, doc.document_type, doc.owner, doc.name)
    }

    return contents.get(event, _("Document {0} has been updated. You can view it <a href='/app/document/{1}'>here</a>.").format(doc.title, doc.name))
