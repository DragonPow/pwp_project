# Copyright (c) 2025, Government Agency and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import nowdate, add_days, getdate

class Task(Document):
    def validate(self):
        self.set_assigned_fields()
        self.validate_due_date()
        self.update_status_based_on_completion()
        
    def before_save(self):
        self.check_overdue()
        
    def on_update(self):
        self.create_audit_log("Updated")
        self.notify_assignment()
        
    def on_trash(self):
        self.create_audit_log("Deleted")
        
    def set_assigned_fields(self):
        if not self.assigned_by:
            self.assigned_by = frappe.session.user
        if not self.assigned_on:
            self.assigned_on = frappe.utils.now()
            
    def validate_due_date(self):
        if self.due_date and getdate(self.due_date) < getdate(nowdate()):
            if self.status not in ["Completed", "Cancelled"]:
                frappe.msgprint("Due date is in the past", alert=True)
                
    def update_status_based_on_completion(self):
        if self.status == "Completed" and not self.completed_on:
            self.completed_on = frappe.utils.now()
        elif self.status != "Completed" and self.completed_on:
            self.completed_on = None
            
    def check_overdue(self):
        if self.due_date and getdate(self.due_date) < getdate(nowdate()):
            if self.status not in ["Completed", "Cancelled"]:
                self.add_comment("Info", "Task is overdue")
                
    def create_audit_log(self, action):
        doc_name = self.document if self.document else "N/A"
        audit_log = frappe.get_doc({
            "doctype": "Audit Log",
            "document": doc_name,
            "action": f"Task {action}",
            "performed_by": frappe.session.user,
            "performed_on": frappe.utils.now(),
            "details": f"Task '{self.title}' was {action.lower()}",
            "ip_address": frappe.local.request_ip if hasattr(frappe.local, 'request_ip') else "",
            "user_agent": frappe.local.request.headers.get('User-Agent') if hasattr(frappe.local, 'request') and hasattr(frappe.local.request, 'headers') else ""
        })
        audit_log.insert(ignore_permissions=True)
        
    def notify_assignment(self):
        if self.assigned_to and self.assigned_to != frappe.session.user:
            # Send notification to assigned user
            subject = f"Task Assigned: {self.title}"
            message = f"""
            You have been assigned a new task:
            
            Title: {self.title}
            Description: {self.description}
            Priority: {self.priority}
            Due Date: {self.due_date or 'Not set'}
            Task Type: {self.task_type}
            
            Please log in to the system to view and complete this task.
            """
            
            frappe.sendmail(
                recipients=self.assigned_to,
                subject=subject,
                message=message,
                reference_doctype=self.doctype,
                reference_name=self.name
            )
            
    def start_task(self):
        self.status = "In Progress"
        self.save()
        
    def complete_task(self):
        self.status = "Completed"
        self.completed_on = frappe.utils.now()
        
        # Update document status if task is related to approval
        if self.document and self.task_type == "Approval":
            doc = frappe.get_doc("Document", self.document)
            if doc.status != "Approved":
                doc.status = "In Review"
                doc.save()
                
        self.save()
        
    def cancel_task(self, reason=""):
        self.status = "Cancelled"
        self.save()
        
    def reassign_task(self, new_assignee):
        old_assignee = self.assigned_to
        self.assigned_to = new_assignee
        self.assigned_on = frappe.utils.now()
        self.save()
        
        # Notify new assignee
        subject = f"Task Reassigned: {self.title}"
        message = f"""
        This task has been reassigned to you:
        
        Title: {self.title}
        Description: {self.description}
        Priority: {self.priority}
        Due Date: {self.due_date or 'Not set'}
        Task Type: {self.task_type}
        
        Previously assigned to: {old_assignee}
        
        Please log in to the system to view and complete this task.
        """
        
        frappe.sendmail(
            recipients=new_assignee,
            subject=subject,
            message=message,
            reference_doctype=self.doctype,
            reference_name=self.name
        )
        
    def get_document_info(self):
        if self.document:
            return frappe.get_doc("Document", self.document)
        return None
        
    def is_overdue(self):
        if self.due_date and self.status not in ["Completed", "Cancelled"]:
            return getdate(self.due_date) < getdate(nowdate())
        return False
        
    def get_days_until_due(self):
        if self.due_date and self.status not in ["Completed", "Cancelled"]:
            return (getdate(self.due_date) - getdate(nowdate())).days
        return None