# Copyright (c) 2025, Government Agency and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, nowdate
from frappe.model.document import Document

@frappe.whitelist()
def get_documents(filters=None, order_by="modified desc", limit_start=0, limit_page_length=20):
    """
    Get documents with optional filtering and pagination
    
    Args:
        filters (dict): Dictionary of filters to apply
        order_by (str): Order by clause
        limit_start (int): Start offset for pagination
        limit_page_length (int): Number of records to return
        
    Returns:
        list: List of documents matching the criteria
    """
    # Build query conditions
    conditions = []
    values = {}
    
    if filters:
        # Title filter
        if filters.get('title'):
            conditions.append("doc.title LIKE %(title)s")
            values['title'] = f"%{filters['title']}%"
            
        # Document type filter
        if filters.get('document_type'):
            conditions.append("doc.document_type = %(document_type)s")
            values['document_type'] = filters['document_type']
            
        # Status filter
        if filters.get('status'):
            conditions.append("doc.status = %(status)s")
            values['status'] = filters['status']
            
        # Security level filter
        if filters.get('security_level'):
            conditions.append("doc.security_level = %(security_level)s")
            values['security_level'] = filters['security_level']
            
        # Owner filter
        if filters.get('owner'):
            conditions.append("doc.owner = %(owner)s")
            values['owner'] = filters['owner']
            
        # Date range filter
        if filters.get('from_date'):
            conditions.append("doc.document_date >= %(from_date)s")
            values['from_date'] = filters['from_date']
            
        if filters.get('to_date'):
            conditions.append("doc.document_date <= %(to_date)s")
            values['to_date'] = filters['to_date']
            
        # Expiry date filter
        if filters.get('expiry_before'):
            conditions.append("doc.expiry_date <= %(expiry_before)s")
            values['expiry_before'] = filters['expiry_before']
            
        if filters.get('expiry_after'):
            conditions.append("doc.expiry_date >= %(expiry_after)s")
            values['expiry_after'] = filters['expiry_after']
            
        # Tags filter
        if filters.get('tags'):
            conditions.append("doc.tags LIKE %(tags)s")
            values['tags'] = f"%{filters['tags']}%"
            
        # Content filter
        if filters.get('content'):
            conditions.append("(doc.content LIKE %(content)s OR doc.description LIKE %(content)s)")
            values['content'] = f"%{filters['content']}%"
            
        # Confidentiality flag filter
        if filters.get('confidentiality_flag') is not None:
            conditions.append("doc.confidentiality_flag = %(confidentiality_flag)s")
            values['confidentiality_flag'] = filters['confidentiality_flag']
    
    # Apply security filtering based on user permissions
    user = frappe.session.user
    if not frappe.has_role("System Manager", user):
        # Non-system managers can only see documents they own or have access to
        conditions.append("""
            (doc.owner = %(user)s 
            OR doc.security_level IN ('Public', 'Internal')
            OR EXISTS (
                SELECT 1 FROM `tabDocument Access Grant` dag 
                WHERE dag.document = doc.name 
                AND dag.user = %(user)s 
                AND dag.expires_on >= %(now)s
            ))
        """)
        values['user'] = user
        values['now'] = nowdate()
    
    # Build the query
    query = """
        SELECT 
            doc.name, doc.title, doc.document_type, doc.document_number, 
            doc.document_date, doc.status, doc.security_level, doc.owner,
            doc.creation_date, doc.last_modified, doc.confidentiality_flag,
            doc.expiry_date, dt.document_type_name
        FROM `tabDocument` doc
        LEFT JOIN `tabDocument Type` dt ON doc.document_type = dt.name
    """
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
        
    query += f" ORDER BY {order_by} LIMIT {limit_start}, {limit_page_length}"
    
    # Execute query
    documents = frappe.db.sql(query, values, as_dict=True)
    
    # Get count for pagination
    count_query = "SELECT COUNT(*) as count FROM `tabDocument` doc"
    if conditions:
        count_query += " WHERE " + " AND ".join(conditions)
        
    count = frappe.db.sql(count_query, values, as_dict=True)[0].count
    
    return {
        'documents': documents,
        'count': count
    }

@frappe.whitelist()
def get_document_filters():
    """
    Get available filter options for documents
    
    Returns:
        dict: Dictionary of available filter options
    """
    # Get document types
    document_types = frappe.get_all("Document Type", 
        filters={"is_active": 1},
        fields=["name", "document_type_name"],
        order_by="document_type_name"
    )
    
    # Get statuses
    statuses = [
        {"value": "Draft", "label": _("Draft")},
        {"value": "In Review", "label": _("In Review")},
        {"value": "Approved", "label": _("Approved")},
        {"value": "Published", "label": _("Published")},
        {"value": "Archived", "label": _("Archived")}
    ]
    
    # Get security levels
    security_levels = [
        {"value": "Public", "label": _("Public")},
        {"value": "Internal", "label": _("Internal")},
        {"value": "Confidential", "label": _("Confidential")},
        {"value": "Secret", "label": _("Secret")}
    ]
    
    # Get users
    users = frappe.get_all("User", 
        filters={"enabled": 1},
        fields=["name", "full_name", "email"],
        order_by="full_name"
    )
    
    return {
        "document_types": document_types,
        "statuses": statuses,
        "security_levels": security_levels,
        "users": users
    }

@frappe.whitelist()
def search_documents(search_text, limit=20):
    """
    Search documents by text in title, content, or tags
    
    Args:
        search_text (str): Text to search for
        limit (int): Maximum number of results to return
        
    Returns:
        list: List of matching documents
    """
    if not search_text:
        return []
    
    # Build search conditions
    conditions = []
    values = {"search_text": f"%{search_text}%", "limit": limit}
    
    # Search in title, content, description, and tags
    conditions.append("""
        (doc.title LIKE %(search_text)s 
        OR doc.content LIKE %(search_text)s 
        OR doc.description LIKE %(search_text)s 
        OR doc.tags LIKE %(search_text)s)
    """)
    
    # Apply security filtering
    user = frappe.session.user
    if not frappe.has_role("System Manager", user):
        conditions.append("""
            (doc.owner = %(user)s 
            OR doc.security_level IN ('Public', 'Internal')
            OR EXISTS (
                SELECT 1 FROM `tabDocument Access Grant` dag 
                WHERE dag.document = doc.name 
                AND dag.user = %(user)s 
                AND dag.expires_on >= %(now)s
            ))
        """)
        values['user'] = user
        values['now'] = nowdate()
    
    # Build query
    query = """
        SELECT 
            doc.name, doc.title, doc.document_type, doc.document_number, 
            doc.document_date, doc.status, doc.security_level, doc.owner,
            doc.creation_date, dt.document_type_name
        FROM `tabDocument` doc
        LEFT JOIN `tabDocument Type` dt ON doc.document_type = dt.name
        WHERE {conditions}
        ORDER BY 
            CASE 
                WHEN doc.title LIKE %(search_text)s THEN 1
                WHEN doc.content LIKE %(search_text)s THEN 2
                ELSE 3
            END,
            doc.modified DESC
        LIMIT %(limit)s
    """.format(conditions=" AND ".join(conditions))
    
    # Execute query
    documents = frappe.db.sql(query, values, as_dict=True)
    
    return documents

@frappe.whitelist()
def get_documents_by_type(document_type, status=None, limit=20):
    """
    Get documents by document type with optional status filter
    
    Args:
        document_type (str): Document type name
        status (str): Optional status filter
        limit (int): Maximum number of results to return
        
    Returns:
        list: List of matching documents
    """
    conditions = ["doc.document_type = %(document_type)s"]
    values = {"document_type": document_type, "limit": limit}
    
    if status:
        conditions.append("doc.status = %(status)s")
        values['status'] = status
    
    # Apply security filtering
    user = frappe.session.user
    if not frappe.has_role("System Manager", user):
        conditions.append("""
            (doc.owner = %(user)s 
            OR doc.security_level IN ('Public', 'Internal')
            OR EXISTS (
                SELECT 1 FROM `tabDocument Access Grant` dag 
                WHERE dag.document = doc.name 
                AND dag.user = %(user)s 
                AND dag.expires_on >= %(now)s
            ))
        """)
        values['user'] = user
        values['now'] = nowdate()
    
    # Build query
    query = """
        SELECT 
            doc.name, doc.title, doc.document_type, doc.document_number, 
            doc.document_date, doc.status, doc.security_level, doc.owner,
            doc.creation_date, dt.document_type_name
        FROM `tabDocument` doc
        LEFT JOIN `tabDocument Type` dt ON doc.document_type = dt.name
        WHERE {conditions}
        ORDER BY doc.modified DESC
        LIMIT %(limit)s
    """.format(conditions=" AND ".join(conditions))
    
    # Execute query
    documents = frappe.db.sql(query, values, as_dict=True)
    
    return documents

@frappe.whitelist()
def get_expired_documents():
    """
    Get documents that have expired or will expire soon
    
    Returns:
        list: List of expired or soon-to-expire documents
    """
    conditions = ["doc.expiry_date <= %(warning_date)s"]
    values = {"warning_date": getdate()}
    
    # Apply security filtering
    user = frappe.session.user
    if not frappe.has_role("System Manager", user):
        conditions.append("""
            (doc.owner = %(user)s 
            OR doc.security_level IN ('Public', 'Internal')
            OR EXISTS (
                SELECT 1 FROM `tabDocument Access Grant` dag 
                WHERE dag.document = doc.name 
                AND dag.user = %(user)s 
                AND dag.expires_on >= %(now)s
            ))
        """)
        values['user'] = user
        values['now'] = nowdate()
    
    # Build query
    query = """
        SELECT 
            doc.name, doc.title, doc.document_type, doc.document_number, 
            doc.document_date, doc.status, doc.security_level, doc.owner,
            doc.expiry_date, dt.document_type_name,
            DATEDIFF(doc.expiry_date, %(warning_date)s) as days_until_expiry
        FROM `tabDocument` doc
        LEFT JOIN `tabDocument Type` dt ON doc.document_type = dt.name
        WHERE {conditions}
        ORDER BY doc.expiry_date ASC
    """.format(conditions=" AND ".join(conditions))
    
    # Execute query
    documents = frappe.db.sql(query, values, as_dict=True)
    
    return documents

@frappe.whitelist()
def get_document_statistics():
    """
    Get document statistics for dashboard
    
    Returns:
        dict: Dictionary of document statistics
    """
    # Apply security filtering
    user = frappe.session.user
    security_condition = ""
    values = {}
    
    if not frappe.has_role("System Manager", user):
        security_condition = """
            WHERE (doc.owner = %(user)s 
            OR doc.security_level IN ('Public', 'Internal')
            OR EXISTS (
                SELECT 1 FROM `tabDocument Access Grant` dag 
                WHERE dag.document = doc.name 
                AND dag.user = %(user)s 
                AND dag.expires_on >= %(now)s
            ))
        """
        values['user'] = user
        values['now'] = nowdate()
    
    # Get total documents
    total_query = "SELECT COUNT(*) as count FROM `tabDocument` doc " + security_condition
    total_count = frappe.db.sql(total_query, values, as_dict=True)[0].count
    
    # Get documents by status
    status_query = """
        SELECT doc.status, COUNT(*) as count 
        FROM `tabDocument` doc 
        {security_condition}
        GROUP BY doc.status
    """.format(security_condition=security_condition)
    status_counts = frappe.db.sql(status_query, values, as_dict=True)
    
    # Get documents by security level
    security_query = """
        SELECT doc.security_level, COUNT(*) as count 
        FROM `tabDocument` doc 
        {security_condition}
        GROUP BY doc.security_level
    """.format(security_condition=security_condition)
    security_counts = frappe.db.sql(security_query, values, as_dict=True)
    
    # Get documents by type
    type_query = """
        SELECT dt.document_type_name, COUNT(doc.name) as count 
        FROM `tabDocument` doc
        LEFT JOIN `tabDocument Type` dt ON doc.document_type = dt.name
        {security_condition}
        GROUP BY dt.document_type_name
        ORDER BY count DESC
        LIMIT 10
    """.format(security_condition=security_condition)
    type_counts = frappe.db.sql(type_query, values, as_dict=True)
    
    # Get expired documents count
    expired_query = """
        SELECT COUNT(*) as count 
        FROM `tabDocument` doc 
        {security_condition}
        AND doc.expiry_date < %(now)s
    """.format(security_condition=security_condition)
    values['now'] = nowdate()
    expired_count = frappe.db.sql(expired_query, values, as_dict=True)[0].count
    
    return {
        "total_documents": total_count,
        "status_counts": status_counts,
        "security_counts": security_counts,
        "type_counts": type_counts,
        "expired_count": expired_count
    }