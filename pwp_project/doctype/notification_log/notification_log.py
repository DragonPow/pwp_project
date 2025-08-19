# Copyright (c) 2025, Government Agency and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now
from frappe import _

class NotificationLog(Document):
    def validate(self):
        self.set_defaults()
        
    def set_defaults(self):
        """Set default values"""
        if not self.sent:
            self.sent = 0
            
    @staticmethod
    def get_notifications_for_user(user, limit=20):
        """Get notifications for a user"""
        return frappe.get_all("Notification Log",
            filters={"for_user": user},
            fields=["name", "subject", "type", "document_type", "document_name", "read", "sent", "creation"],
            order_by="creation desc",
            limit=limit
        )
        
    @staticmethod
    def get_unread_notifications_for_user(user, limit=20):
        """Get unread notifications for a user"""
        return frappe.get_all("Notification Log",
            filters={"for_user": user, "read": 0},
            fields=["name", "subject", "type", "document_type", "document_name", "creation"],
            order_by="creation desc",
            limit=limit
        )
        
    @staticmethod
    def mark_notification_as_read(notification_name):
        """Mark a notification as read"""
        frappe.db.set_value("Notification Log", notification_name, "read", 1)
        
    @staticmethod
    def mark_all_notifications_as_read(user):
        """Mark all notifications for a user as read"""
        frappe.db.set_value("Notification Log", {"for_user": user, "read": 0}, "read", 1)
        
    @staticmethod
    def send_notification_email(notification_name):
        """Send notification email"""
        notification = frappe.get_doc("Notification Log", notification_name)
        
        if notification.sent:
            return
            
        # Get user email
        user = frappe.get_doc("User", notification.for_user)
        
        # Send email
        frappe.sendmail(
            recipients=user.email,
            subject=notification.subject,
            message=notification.email_content,
            reference_doctype=notification.document_type,
            reference_name=notification.document_name
        )
        
        # Mark as sent
        notification.sent = 1
        notification.save()
        
    @staticmethod
    def cleanup_old_notifications(days=30):
        """Clean up old notifications"""
        from frappe.utils import add_days
        
        # Get notifications older than specified days
        old_notifications = frappe.get_all("Notification Log",
            filters={"creation": ["<", add_days(now(), -days)]},
            fields=["name"]
        )
        
        count = 0
        for notification in old_notifications:
            frappe.delete_doc("Notification Log", notification.name)
            count += 1
            
        return count