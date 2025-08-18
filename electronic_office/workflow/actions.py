import frappe
from frappe import _
from frappe.model.document import Document
import json
from datetime import datetime, timedelta
from .state_machine import WorkflowStateMachine, WorkflowState
from .routing import WorkflowRouting

class WorkflowActions:
    """
    Workflow approval and rejection actions
    """
    
    @staticmethod
    def approve_workflow(workflow_instance, user, comment=None):
        """
        Approve a workflow at the current step
        """
        # Check if user can approve
        if not WorkflowActions.can_approve(workflow_instance, user):
            frappe.throw(_("You are not allowed to approve this workflow"))
        
        # Get current step
        workflow_def = frappe.get_doc("Workflow Definition", workflow_instance.workflow_definition)
        current_step = workflow_def.get_step_by_order(workflow_instance.current_step)
        
        if not current_step:
            frappe.throw(_("Current step not found"))
        
        # Log the approval action
        WorkflowActions.log_action(workflow_instance, "Approve", current_step.step_name, user, comment)
        
        # Get the next step
        from .routing import WorkflowRouting
        next_step = WorkflowRouting.get_next_step(workflow_instance, current_step, "Approve")
        
        if next_step:
            # Move to next step
            workflow_instance.current_step = next_step.step_order
            
            if next_step.step_type == "End":
                # Complete the workflow
                WorkflowStateMachine.transition_to(workflow_instance, WorkflowState.COMPLETED, user, comment)
            else:
                # Process the next step
                workflow_instance.process_step(next_step)
        else:
            # No next step, complete the workflow
            WorkflowStateMachine.transition_to(workflow_instance, WorkflowState.COMPLETED, user, comment)
        
        workflow_instance.save()
        
        # Send notifications
        WorkflowActions.send_action_notifications(workflow_instance, "Approve", user, comment)
        
        return workflow_instance.status
    
    @staticmethod
    def reject_workflow(workflow_instance, user, comment=None):
        """
        Reject a workflow at the current step
        """
        # Check if user can reject
        if not WorkflowActions.can_reject(workflow_instance, user):
            frappe.throw(_("You are not allowed to reject this workflow"))
        
        # Get current step
        workflow_def = frappe.get_doc("Workflow Definition", workflow_instance.workflow_definition)
        current_step = workflow_def.get_step_by_order(workflow_instance.current_step)
        
        if not current_step:
            frappe.throw(_("Current step not found"))
        
        # Log the rejection action
        WorkflowActions.log_action(workflow_instance, "Reject", current_step.step_name, user, comment)
        
        # Transition to rejected state
        WorkflowStateMachine.transition_to(workflow_instance, WorkflowState.REJECTED, user, comment)
        
        # Send notifications
        WorkflowActions.send_action_notifications(workflow_instance, "Reject", user, comment)
        
        return workflow_instance.status
    
    @staticmethod
    def request_changes(workflow_instance, user, comment=None):
        """
        Request changes for a workflow at the current step
        """
        # Check if user can request changes
        if not WorkflowActions.can_request_changes(workflow_instance, user):
            frappe.throw(_("You are not allowed to request changes for this workflow"))
        
        # Get current step
        workflow_def = frappe.get_doc("Workflow Definition", workflow_instance.workflow_definition)
        current_step = workflow_def.get_step_by_order(workflow_instance.current_step)
        
        if not current_step:
            frappe.throw(_("Current step not found"))
        
        # Log the request changes action
        WorkflowActions.log_action(workflow_instance, "Request Changes", current_step.step_name, user, comment)
        
        # Get the next step for changes
        from .routing import WorkflowRouting
        next_step = WorkflowRouting.get_next_step(workflow_instance, current_step, "Request Changes")
        
        if next_step:
            # Move to next step
            workflow_instance.current_step = next_step.step_order
            workflow_instance.process_step(next_step)
        else:
            # If no specific step for changes, go back to the previous step
            if workflow_instance.current_step > 1:
                workflow_instance.current_step -= 1
                previous_step = workflow_def.get_step_by_order(workflow_instance.current_step)
                if previous_step:
                    workflow_instance.process_step(previous_step)
        
        workflow_instance.save()
        
        # Send notifications
        WorkflowActions.send_action_notifications(workflow_instance, "Request Changes", user, comment)
        
        return workflow_instance.status
    
    @staticmethod
    def forward_workflow(workflow_instance, user, to_step=None, comment=None):
        """
        Forward a workflow to a specific step
        """
        # Check if user can forward
        if not WorkflowActions.can_forward(workflow_instance, user):
            frappe.throw(_("You are not allowed to forward this workflow"))
        
        # Get current step
        workflow_def = frappe.get_doc("Workflow Definition", workflow_instance.workflow_definition)
        current_step = workflow_def.get_step_by_order(workflow_instance.current_step)
        
        if not current_step:
            frappe.throw(_("Current step not found"))
        
        # Get the target step
        if to_step:
            target_step = workflow_def.get_step_by_order(to_step)
            if not target_step:
                frappe.throw(_("Target step not found"))
        else:
            # Get next step for forward action
            from .routing import WorkflowRouting
            target_step = WorkflowRouting.get_next_step(workflow_instance, current_step, "Forward")
            
            if not target_step:
                frappe.throw(_("No target step found for forward action"))
        
        # Log the forward action
        WorkflowActions.log_action(workflow_instance, "Forward", f"{current_step.step_name} → {target_step.step_name}", user, comment)
        
        # Move to target step
        workflow_instance.current_step = target_step.step_order
        
        if target_step.step_type == "End":
            # Complete the workflow
            WorkflowStateMachine.transition_to(workflow_instance, WorkflowState.COMPLETED, user, comment)
        else:
            # Process the target step
            workflow_instance.process_step(target_step)
        
        workflow_instance.save()
        
        # Send notifications
        WorkflowActions.send_action_notifications(workflow_instance, "Forward", user, comment)
        
        return workflow_instance.status
    
    @staticmethod
    def skip_step(workflow_instance, user, comment=None):
        """
        Skip the current step
        """
        # Check if user can skip
        if not WorkflowActions.can_skip(workflow_instance, user):
            frappe.throw(_("You are not allowed to skip this step"))
        
        # Get current step
        workflow_def = frappe.get_doc("Workflow Definition", workflow_instance.workflow_definition)
        current_step = workflow_def.get_step_by_order(workflow_instance.current_step)
        
        if not current_step:
            frappe.throw(_("Current step not found"))
        
        # Log the skip action
        WorkflowActions.log_action(workflow_instance, "Skip", current_step.step_name, user, comment)
        
        # Get the next step
        from .routing import WorkflowRouting
        next_step = WorkflowRouting.get_next_step(workflow_instance, current_step, "Skip")
        
        if next_step:
            # Move to next step
            workflow_instance.current_step = next_step.step_order
            
            if next_step.step_type == "End":
                # Complete the workflow
                WorkflowStateMachine.transition_to(workflow_instance, WorkflowState.COMPLETED, user, comment)
            else:
                # Process the next step
                workflow_instance.process_step(next_step)
        else:
            # No next step, complete the workflow
            WorkflowStateMachine.transition_to(workflow_instance, WorkflowState.COMPLETED, user, comment)
        
        workflow_instance.save()
        
        # Send notifications
        WorkflowActions.send_action_notifications(workflow_instance, "Skip", user, comment)
        
        return workflow_instance.status
    
    @staticmethod
    def can_approve(workflow_instance, user):
        """
        Check if a user can approve the current step
        """
        workflow_def = frappe.get_doc("Workflow Definition", workflow_instance.workflow_definition)
        current_step = workflow_def.get_step_by_order(workflow_instance.current_step)
        
        if not current_step:
            return False
        
        # Check if user is assigned to the current step
        if not WorkflowRouting.is_user_assigned_to_step(current_step, user, workflow_instance.document):
            return False
        
        # Check if approve action is available for the current step
        actions = frappe.get_all("Workflow Step Action", {
            "parent": current_step.name,
            "parenttype": "Workflow Step",
            "action_type": "Approval"
        })
        
        if not actions:
            return False
        
        # Check if user has permission for any approve action
        for action in actions:
            action_doc = frappe.get_doc("Workflow Step Action", action.name)
            if WorkflowRouting.is_action_allowed(action_doc, user, workflow_instance.document):
                return True
        
        return False
    
    @staticmethod
    def can_reject(workflow_instance, user):
        """
        Check if a user can reject the current step
        """
        workflow_def = frappe.get_doc("Workflow Definition", workflow_instance.workflow_definition)
        current_step = workflow_def.get_step_by_order(workflow_instance.current_step)
        
        if not current_step:
            return False
        
        # Check if user is assigned to the current step
        if not WorkflowRouting.is_user_assigned_to_step(current_step, user, workflow_instance.document):
            return False
        
        # Check if reject action is available for the current step
        actions = frappe.get_all("Workflow Step Action", {
            "parent": current_step.name,
            "parenttype": "Workflow Step",
            "action_type": "Rejection"
        })
        
        if not actions:
            return False
        
        # Check if user has permission for any reject action
        for action in actions:
            action_doc = frappe.get_doc("Workflow Step Action", action.name)
            if WorkflowRouting.is_action_allowed(action_doc, user, workflow_instance.document):
                return True
        
        return False
    
    @staticmethod
    def can_request_changes(workflow_instance, user):
        """
        Check if a user can request changes for the current step
        """
        workflow_def = frappe.get_doc("Workflow Definition", workflow_instance.workflow_definition)
        current_step = workflow_def.get_step_by_order(workflow_instance.current_step)
        
        if not current_step:
            return False
        
        # Check if user is assigned to the current step
        if not WorkflowRouting.is_user_assigned_to_step(current_step, user, workflow_instance.document):
            return False
        
        # Check if request changes action is available for the current step
        actions = frappe.get_all("Workflow Step Action", {
            "parent": current_step.name,
            "parenttype": "Workflow Step",
            "action_type": "Request Changes"
        })
        
        if not actions:
            return False
        
        # Check if user has permission for any request changes action
        for action in actions:
            action_doc = frappe.get_doc("Workflow Step Action", action.name)
            if WorkflowRouting.is_action_allowed(action_doc, user, workflow_instance.document):
                return True
        
        return False
    
    @staticmethod
    def can_forward(workflow_instance, user):
        """
        Check if a user can forward the current step
        """
        workflow_def = frappe.get_doc("Workflow Definition", workflow_instance.workflow_definition)
        current_step = workflow_def.get_step_by_order(workflow_instance.current_step)
        
        if not current_step:
            return False
        
        # Check if user is assigned to the current step
        if not WorkflowRouting.is_user_assigned_to_step(current_step, user, workflow_instance.document):
            return False
        
        # Check if forward action is available for the current step
        actions = frappe.get_all("Workflow Step Action", {
            "parent": current_step.name,
            "parenttype": "Workflow Step",
            "action_type": "Forward"
        })
        
        if not actions:
            return False
        
        # Check if user has permission for any forward action
        for action in actions:
            action_doc = frappe.get_doc("Workflow Step Action", action.name)
            if WorkflowRouting.is_action_allowed(action_doc, user, workflow_instance.document):
                return True
        
        return False
    
    @staticmethod
    def can_skip(workflow_instance, user):
        """
        Check if a user can skip the current step
        """
        workflow_def = frappe.get_doc("Workflow Definition", workflow_instance.workflow_definition)
        current_step = workflow_def.get_step_by_order(workflow_instance.current_step)
        
        if not current_step:
            return False
        
        # Check if step allows skipping
        if not current_step.allow_skip:
            return False
        
        # Check if user is assigned to the current step
        if not WorkflowRouting.is_user_assigned_to_step(current_step, user, workflow_instance.document):
            return False
        
        # Check if skip action is available for the current step
        actions = frappe.get_all("Workflow Step Action", {
            "parent": current_step.name,
            "parenttype": "Workflow Step",
            "action_type": "Skip"
        })
        
        if not actions:
            return False
        
        # Check if user has permission for any skip action
        for action in actions:
            action_doc = frappe.get_doc("Workflow Step Action", action.name)
            if WorkflowRouting.is_action_allowed(action_doc, user, workflow_instance.document):
                return True
        
        return False
    
    @staticmethod
    def log_action(workflow_instance, action, step_name, user, comment=None):
        """
        Log a workflow action
        """
        # Create a comment on the workflow instance
        if comment:
            workflow_instance.add_comment("Comment", f"{action} - {step_name}: {comment}")
        else:
            workflow_instance.add_comment("Comment", f"{action} - {step_name}")
        
        # Update workflow history
        history = workflow_instance.history or []
        history.append({
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "step": step_name,
            "user": user,
            "comment": comment
        })
        
        workflow_instance.history = json.dumps(history)
        workflow_instance.save()
    
    @staticmethod
    def send_action_notifications(workflow_instance, action, user, comment=None):
        """
        Send notifications for a workflow action
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
        subject = f"Workflow {action}: {workflow_instance.document}"
        message = f"The workflow for document {workflow_instance.document} has been {action.lower()}ed by {user}."
        
        if comment:
            message += f"\n\nComment: {comment}"
        
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
                "type": "Alert",
                "subject": subject,
                "content": message,
                "reference_doctype": "Workflow Instance",
                "reference_name": workflow_instance.name
            }).insert()
    
    @staticmethod
    def get_action_recipients(workflow_instance, action, user):
        """
        Get recipients for a workflow action notification
        """
        recipients = []
        
        # Always notify workflow initiator
        if workflow_instance.started_by and workflow_instance.started_by != user:
            recipients.append(workflow_instance.started_by)
        
        # Get current step
        workflow_def = frappe.get_doc("Workflow Definition", workflow_instance.workflow_definition)
        current_step = workflow_def.get_step_by_order(workflow_instance.current_step)
        
        if not current_step:
            return recipients
        
        # Get next step based on action
        from .routing import WorkflowRouting
        next_step = WorkflowRouting.get_next_step(workflow_instance, current_step, action)
        
        if next_step:
            # Notify assignees of the next step
            next_step_assignees = WorkflowRouting.get_step_assignees(next_step, workflow_instance.document)
            for assignee in next_step_assignees:
                if assignee != user and assignee not in recipients:
                    recipients.append(assignee)
        
        # For reject and request changes actions, also notify previous step assignees
        if action in ["Reject", "Request Changes"]:
            if workflow_instance.current_step > 1:
                previous_step = workflow_def.get_step_by_order(workflow_instance.current_step - 1)
                if previous_step:
                    previous_step_assignees = WorkflowRouting.get_step_assignees(previous_step, workflow_instance.document)
                    for assignee in previous_step_assignees:
                        if assignee != user and assignee not in recipients:
                            recipients.append(assignee)
        
        return recipients
    
    @staticmethod
    def get_available_actions(workflow_instance, user):
        """
        Get available actions for a user at the current step
        """
        actions = []
        
        if WorkflowActions.can_approve(workflow_instance, user):
            actions.append("Approve")
        
        if WorkflowActions.can_reject(workflow_instance, user):
            actions.append("Reject")
        
        if WorkflowActions.can_request_changes(workflow_instance, user):
            actions.append("Request Changes")
        
        if WorkflowActions.can_forward(workflow_instance, user):
            actions.append("Forward")
        
        if WorkflowActions.can_skip(workflow_instance, user):
            actions.append("Skip")
        
        return actions
    
    @staticmethod
    def execute_action(workflow_instance, action, user, comment=None, to_step=None):
        """
        Execute a workflow action
        """
        if action == "Approve":
            return WorkflowActions.approve_workflow(workflow_instance, user, comment)
        elif action == "Reject":
            return WorkflowActions.reject_workflow(workflow_instance, user, comment)
        elif action == "Request Changes":
            return WorkflowActions.request_changes(workflow_instance, user, comment)
        elif action == "Forward":
            return WorkflowActions.forward_workflow(workflow_instance, user, to_step, comment)
        elif action == "Skip":
            return WorkflowActions.skip_step(workflow_instance, user, comment)
        else:
            frappe.throw(_("Invalid action: {0}").format(action))