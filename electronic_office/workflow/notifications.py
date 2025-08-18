import frappe
from frappe import _
from frappe.model.document import Document
import json
from datetime import datetime, timedelta
from .state_machine import WorkflowStateMachine, WorkflowState
from .routing import WorkflowRouting
from .actions import WorkflowActions

class WorkflowNotifications:
    """
    Workflow notifications and alerts
    """
    
    @staticmethod
    def send_workflow_notification(workflow_instance, subject, message, recipients, notification_type="Info"):
        """
        Send a workflow notification
        """
        if not recipients:
            return
        
        # Send email notification
        frappe.sendmail(
            recipients=recipients,
            subject=subject,
            message=message,
            reference_doctype="Workflow Instance",
            reference_name=workflow_instance.name
        )
        
        # Create in-app notification
        for recipient in recipients:
            frappe.get_doc({
                "doctype": "Notification Log",
                "for_user": recipient,
                "type": notification_type,
                "subject": subject,
                "content": message,
                "reference_doctype": "Workflow Instance",
                "reference_name": workflow_instance.name
            }).insert()
    
    @staticmethod
    def notify_workflow_started(workflow_instance):
        """
        Notify users when a workflow is started
        """
        workflow_def = frappe.get_doc("Workflow Definition", workflow_instance.workflow_definition)
        start_step = workflow_def.get_start_step()
        
        if not start_step:
            return
        
        # Get assignees for the start step
        assignees = WorkflowRouting.get_step_assignees(start_step, workflow_instance.document)
        
        # Create notification message
        subject = f"Workflow Started: {workflow_instance.document}"
        message = f"A new workflow has been started for document {workflow_instance.document}.\n\n"
        message += f"Workflow: {workflow_def.workflow_name}\n"
        message += f"Started by: {workflow_instance.started_by}\n"
        message += f"Started on: {workflow_instance.started_on}\n\n"
        message += f"Please review and take necessary action."
        
        # Send notification
        WorkflowNotifications.send_workflow_notification(
            workflow_instance,
            subject,
            message,
            assignees,
            "Alert"
        )
    
    @staticmethod
    def notify_step_assigned(workflow_instance, step, assignees):
        """
        Notify users when they are assigned to a step
        """
        # Create notification message
        subject = f"Workflow Step Assigned: {step.step_name}"
        message = f"You have been assigned to the step '{step.step_name}' in the workflow for document {workflow_instance.document}.\n\n"
        message += f"Step Description: {step.description or 'No description provided'}\n"
        message += f"Step Type: {step.step_type}\n\n"
        
        if step.timeout_days:
            timeout_date = datetime.now() + timedelta(days=step.timeout_days)
            message += f"Please complete this step by {timeout_date.strftime('%Y-%m-%d %H:%M:%S')}.\n\n"
        
        message += f"Please review and take necessary action."
        
        # Send notification
        WorkflowNotifications.send_workflow_notification(
            workflow_instance,
            subject,
            message,
            assignees,
            "Alert"
        )
        
        # Schedule timeout notification if needed
        if step.timeout_days and step.notify_on_timeout:
            WorkflowNotifications.schedule_timeout_notification(workflow_instance, step)
    
    @staticmethod
    def notify_step_completed(workflow_instance, step, user, comment=None):
        """
        Notify users when a step is completed
        """
        # Get next step
        from .routing import WorkflowRouting
        next_step = WorkflowRouting.get_next_step(workflow_instance, step)
        
        if not next_step:
            # No next step, workflow is completed
            WorkflowNotifications.notify_workflow_completed(workflow_instance)
            return
        
        # Get assignees for the next step
        next_assignees = WorkflowRouting.get_step_assignees(next_step, workflow_instance.document)
        
        # Create notification message
        subject = f"Workflow Step Completed: {step.step_name}"
        message = f"The step '{step.step_name}' in the workflow for document {workflow_instance.document} has been completed by {user}.\n\n"
        
        if comment:
            message += f"Comment: {comment}\n\n"
        
        message += f"The next step '{next_step.step_name}' is now ready for your action."
        
        # Send notification
        WorkflowNotifications.send_workflow_notification(
            workflow_instance,
            subject,
            message,
            next_assignees,
            "Info"
        )
        
        # Notify workflow initiator
        if workflow_instance.started_by and workflow_instance.started_by != user:
            WorkflowNotifications.send_workflow_notification(
                workflow_instance,
                subject,
                message,
                [workflow_instance.started_by],
                "Info"
            )
    
    @staticmethod
    def notify_workflow_completed(workflow_instance):
        """
        Notify users when a workflow is completed
        """
        # Create notification message
        subject = f"Workflow Completed: {workflow_instance.document}"
        message = f"The workflow for document {workflow_instance.document} has been completed.\n\n"
        message += f"Completed by: {workflow_instance.completed_by}\n"
        message += f"Completed on: {workflow_instance.completed_on}\n\n"
        message += f"The document status has been updated to 'Approved'."
        
        # Notify workflow initiator
        if workflow_instance.started_by:
            WorkflowNotifications.send_workflow_notification(
                workflow_instance,
                subject,
                message,
                [workflow_instance.started_by],
                "Success"
            )
        
        # Notify all users who participated in the workflow
        participants = WorkflowNotifications.get_workflow_participants(workflow_instance)
        for participant in participants:
            if participant != workflow_instance.started_by:
                WorkflowNotifications.send_workflow_notification(
                    workflow_instance,
                    subject,
                    message,
                    [participant],
                    "Success"
                )
    
    @staticmethod
    def notify_workflow_rejected(workflow_instance, user, comment=None):
        """
        Notify users when a workflow is rejected
        """
        # Create notification message
        subject = f"Workflow Rejected: {workflow_instance.document}"
        message = f"The workflow for document {workflow_instance.document} has been rejected by {user}.\n\n"
        
        if comment:
            message += f"Reason: {comment}\n\n"
        
        message += f"The document status has been updated to 'Rejected'."
        
        # Notify workflow initiator
        if workflow_instance.started_by:
            WorkflowNotifications.send_workflow_notification(
                workflow_instance,
                subject,
                message,
                [workflow_instance.started_by],
                "Warning"
            )
        
        # Notify all users who participated in the workflow
        participants = WorkflowNotifications.get_workflow_participants(workflow_instance)
        for participant in participants:
            if participant != workflow_instance.started_by:
                WorkflowNotifications.send_workflow_notification(
                    workflow_instance,
                    subject,
                    message,
                    [participant],
                    "Warning"
                )
    
    @staticmethod
    def notify_workflow_cancelled(workflow_instance, user, comment=None):
        """
        Notify users when a workflow is cancelled
        """
        # Create notification message
        subject = f"Workflow Cancelled: {workflow_instance.document}"
        message = f"The workflow for document {workflow_instance.document} has been cancelled by {user}.\n\n"
        
        if comment:
            message += f"Reason: {comment}\n\n"
        
        message += f"The document status has been updated to 'Cancelled'."
        
        # Notify workflow initiator
        if workflow_instance.started_by:
            WorkflowNotifications.send_workflow_notification(
                workflow_instance,
                subject,
                message,
                [workflow_instance.started_by],
                "Warning"
            )
        
        # Notify all users who participated in the workflow
        participants = WorkflowNotifications.get_workflow_participants(workflow_instance)
        for participant in participants:
            if participant != workflow_instance.started_by:
                WorkflowNotifications.send_workflow_notification(
                    workflow_instance,
                    subject,
                    message,
                    [participant],
                    "Warning"
                )
    
    @staticmethod
    def notify_step_timeout(workflow_instance, step):
        """
        Notify users when a step times out
        """
        # Get assignees for the step
        assignees = WorkflowRouting.get_step_assignees(step, workflow_instance.document)
        
        # Create notification message
        subject = f"Workflow Step Timeout: {step.step_name}"
        message = f"The step '{step.step_name}' in the workflow for document {workflow_instance.document} has timed out.\n\n"
        message += f"Please complete this step as soon as possible or request an extension if needed."
        
        # Send notification
        WorkflowNotifications.send_workflow_notification(
            workflow_instance,
            subject,
            message,
            assignees,
            "Warning"
        )
        
        # Notify workflow initiator
        if workflow_instance.started_by:
            WorkflowNotifications.send_workflow_notification(
                workflow_instance,
                subject,
                message,
                [workflow_instance.started_by],
                "Warning"
            )
        
        # Escalate if needed
        if step.escalation_days:
            WorkflowNotifications.escalate_step(workflow_instance, step)
    
    @staticmethod
    def escalate_step(workflow_instance, step):
        """
        Escalate a step that has timed out
        """
        # Get escalation users (typically System Manager or a specific role)
        escalation_users = frappe.get_users_by_role("System Manager")
        
        # Create notification message
        subject = f"Workflow Step Escalation: {step.step_name}"
        message = f"The step '{step.step_name}' in the workflow for document {workflow_instance.document} requires escalation.\n\n"
        message += f"The step has timed out and needs immediate attention.\n\n"
        message += f"Please take appropriate action."
        
        # Send notification
        WorkflowNotifications.send_workflow_notification(
            workflow_instance,
            subject,
            message,
            [user.name for user in escalation_users],
            "Alert"
        )
    
    @staticmethod
    def schedule_timeout_notification(workflow_instance, step):
        """
        Schedule a timeout notification for a step
        """
        if not step.timeout_days:
            return
        
        timeout_date = datetime.now() + timedelta(days=step.timeout_days)
        
        frappe.enqueue(
            "electronic_office.electronic_office.workflow.notifications.check_step_timeout",
            workflow_instance=workflow_instance.name,
            step_name=step.step_name,
            timeout_date=timeout_date,
            queue="long",
            enqueue_after_minutes=step.timeout_days * 24 * 60
        )
    
    @staticmethod
    def check_step_timeout(workflow_instance, step_name, timeout_date):
        """
        Check if a step has timed out and send notification if needed
        """
        if datetime.now() < timeout_date:
            return
        
        wf_instance = frappe.get_doc("Workflow Instance", workflow_instance)
        
        if wf_instance.status not in ["Completed", "Rejected", "Cancelled"]:
            workflow_def = frappe.get_doc("Workflow Definition", wf_instance.workflow_definition)
            current_step = workflow_def.get_step_by_order(wf_instance.current_step)
            
            if current_step and current_step.step_name == step_name:
                WorkflowNotifications.notify_step_timeout(wf_instance, current_step)
    
    @staticmethod
    def get_workflow_participants(workflow_instance):
        """
        Get all users who participated in a workflow
        """
        participants = set()
        
        # Add workflow initiator
        if workflow_instance.started_by:
            participants.add(workflow_instance.started_by)
        
        # Add users from workflow history
        history = workflow_instance.history or "[]"
        try:
            history_data = json.loads(history)
            for entry in history_data:
                if entry.get("user"):
                    participants.add(entry.get("user"))
        except:
            pass
        
        # Add users who commented on the workflow
        comments = frappe.get_all("Comment", {
            "reference_doctype": "Workflow Instance",
            "reference_name": workflow_instance.name
        }, ["owner"])
        
        for comment in comments:
            participants.add(comment.owner)
        
        return list(participants)
    
    @staticmethod
    def send_workflow_reminder(workflow_instance, days_before=1):
        """
        Send a reminder for a workflow step that is about to timeout
        """
        workflow_def = frappe.get_doc("Workflow Definition", workflow_instance.workflow_definition)
        current_step = workflow_def.get_step_by_order(workflow_instance.current_step)
        
        if not current_step or not current_step.timeout_days:
            return
        
        # Calculate days until timeout
        # This is a simplified calculation - in a real implementation, you would track when the step was assigned
        days_until_timeout = current_step.timeout_days - days_before
        
        if days_until_timeout <= 0:
            return
        
        # Get assignees for the current step
        assignees = WorkflowRouting.get_step_assignees(current_step, workflow_instance.document)
        
        # Create notification message
        subject = f"Workflow Step Reminder: {current_step.step_name}"
        message = f"This is a reminder that the step '{current_step.step_name}' in the workflow for document {workflow_instance.document} will timeout in {days_until_timeout} days.\n\n"
        message += f"Please complete this step as soon as possible."
        
        # Send notification
        WorkflowNotifications.send_workflow_notification(
            workflow_instance,
            subject,
            message,
            assignees,
            "Info"
        )
    
    @staticmethod
    def send_daily_workflow_summary(user):
        """
        Send a daily summary of workflow activities to a user
        """
        # Get workflow instances where the user is involved
        pending_workflows = frappe.get_all("Workflow Instance", {
            "status": ["in", ["Pending", "In Progress"]]
        }, ["name", "document", "workflow_definition", "status", "current_step"])
        
        user_workflows = []
        
        for wf in pending_workflows:
            wf_instance = frappe.get_doc("Workflow Instance", wf.name)
            workflow_def = frappe.get_doc("Workflow Definition", wf.workflow_definition)
            current_step = workflow_def.get_step_by_order(wf.current_step)
            
            if current_step and WorkflowRouting.is_user_assigned_to_step(current_step, user, wf_instance.document):
                user_workflows.append({
                    "workflow_instance": wf.name,
                    "document": wf.document,
                    "workflow_name": workflow_def.workflow_name,
                    "current_step": current_step.step_name,
                    "status": wf.status
                })
        
        if not user_workflows:
            return
        
        # Create notification message
        subject = "Daily Workflow Summary"
        message = f"Here is your daily workflow summary:\n\n"
        
        for wf in user_workflows:
            message += f"• Document: {wf['document']}\n"
            message += f"  Workflow: {wf['workflow_name']}\n"
            message += f"  Current Step: {wf['current_step']}\n"
            message += f"  Status: {wf['status']}\n\n"
        
        message += f"Please review and take necessary action."
        
        # Send notification
        WorkflowNotifications.send_workflow_notification(
            None,  # No specific workflow instance
            subject,
            message,
            [user],
            "Info"
        )
    
    @staticmethod
    def send_workflow_digest(role, frequency="daily"):
        """
        Send a workflow digest to users with a specific role
        """
        # Get users with the specified role
        users = frappe.get_users_by_role(role)
        
        for user in users:
            # Get workflow statistics
            stats = WorkflowStateMachine.get_workflow_statistics()
            
            # Create notification message
            subject = f"{frequency.capitalize()} Workflow Digest"
            message = f"Here is your {frequency} workflow digest:\n\n"
            
            message += f"Total Workflows: {stats['total']}\n"
            message += f"Draft: {stats['draft']}\n"
            message += f"Pending: {stats['pending']}\n"
            message += f"In Progress: {stats['in_progress']}\n"
            message += f"Completed: {stats['completed']}\n"
            message += f"Rejected: {stats['rejected']}\n"
            message += f"Cancelled: {stats['cancelled']}\n"
            message += f"On Hold: {stats['on_hold']}\n\n"
            
            # Add workflow-specific statistics if the user has access to any
            for wf_name, wf_stats in stats['by_workflow_definition'].items():
                workflow_def = frappe.get_doc("Workflow Definition", wf_name)
                if frappe.has_role(workflow_def.document_type, user.name):
                    message += f"\n{workflow_def.workflow_name}:\n"
                    message += f"  Total: {wf_stats['total']}\n"
                    message += f"  In Progress: {wf_stats['in_progress']}\n"
                    message += f"  Completed: {wf_stats['completed']}\n"
                    message += f"  Rejected: {wf_stats['rejected']}\n"
            
            # Send notification
            WorkflowNotifications.send_workflow_notification(
                None,  # No specific workflow instance
                subject,
                message,
                [user.name],
                "Info"
            )
    
    @staticmethod
    def notify_workflow_action(workflow_instance, action, user, comment=None):
        """
        Notify users when a workflow action is taken
        """
        # Get current step
        workflow_def = frappe.get_doc("Workflow Definition", workflow_instance.workflow_definition)
        current_step = workflow_def.get_step_by_order(workflow_instance.current_step)
        
        if not current_step:
            return
        
        # Get recipients based on action
        recipients = WorkflowActions.get_action_recipients(workflow_instance, action, user)
        
        if not recipients:
            return
        
        # Create notification message
        subject = f"Workflow Action: {action}"
        message = f"The action '{action}' has been taken on the workflow for document {workflow_instance.document} by {user}.\n\n"
        
        if comment:
            message += f"Comment: {comment}\n\n"
        
        message += f"Current Step: {current_step.step_name}"
        
        # Send notification
        WorkflowNotifications.send_workflow_notification(
            workflow_instance,
            subject,
            message,
            recipients,
            "Info"
        )