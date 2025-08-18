import frappe
from frappe import _
from frappe.model.document import Document
import json
from datetime import datetime, timedelta
from enum import Enum

class WorkflowState(Enum):
    """Workflow states"""
    DRAFT = "Draft"
    PENDING = "Pending"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"
    REJECTED = "Rejected"
    ON_HOLD = "On Hold"

class WorkflowStateMachine:
    """
    Workflow state machine implementation
    """
    
    @staticmethod
    def get_valid_transitions(current_state):
        """
        Get valid transitions from the current state
        """
        transitions = {
            WorkflowState.DRAFT: [WorkflowState.PENDING, WorkflowState.CANCELLED],
            WorkflowState.PENDING: [WorkflowState.IN_PROGRESS, WorkflowState.CANCELLED],
            WorkflowState.IN_PROGRESS: [WorkflowState.COMPLETED, WorkflowState.REJECTED, WorkflowState.ON_HOLD, WorkflowState.CANCELLED],
            WorkflowState.ON_HOLD: [WorkflowState.IN_PROGRESS, WorkflowState.CANCELLED],
            WorkflowState.COMPLETED: [],
            WorkflowState.REJECTED: [WorkflowState.PENDING, WorkflowState.CANCELLED],
            WorkflowState.CANCELLED: [WorkflowState.DRAFT]
        }
        
        return transitions.get(current_state, [])
    
    @staticmethod
    def can_transition(current_state, new_state):
        """
        Check if a transition from current_state to new_state is valid
        """
        valid_transitions = WorkflowStateMachine.get_valid_transitions(current_state)
        return new_state in valid_transitions
    
    @staticmethod
    def transition_to(workflow_instance, new_state, user=None, comment=None):
        """
        Transition a workflow instance to a new state
        """
        if not user:
            user = frappe.session.user
        
        current_state = WorkflowState(workflow_instance.status)
        
        if not WorkflowStateMachine.can_transition(current_state, new_state):
            frappe.throw(_("Invalid transition from {0} to {1}").format(current_state.value, new_state.value))
        
        # Log the transition
        WorkflowStateMachine.log_state_transition(workflow_instance, current_state, new_state, user, comment)
        
        # Update the workflow instance
        workflow_instance.status = new_state.value
        
        # Set completion details if transitioning to a final state
        if new_state in [WorkflowState.COMPLETED, WorkflowState.REJECTED, WorkflowState.CANCELLED]:
            workflow_instance.completed_by = user
            workflow_instance.completed_on = datetime.now()
        
        workflow_instance.save()
        
        # Execute state-specific actions
        WorkflowStateMachine.execute_state_actions(workflow_instance, current_state, new_state, user)
        
        return workflow_instance
    
    @staticmethod
    def log_state_transition(workflow_instance, from_state, to_state, user, comment=None):
        """
        Log a state transition
        """
        # Create a comment on the workflow instance
        if comment:
            workflow_instance.add_comment("Comment", f"State changed from {from_state.value} to {to_state.value}: {comment}")
        else:
            workflow_instance.add_comment("Comment", f"State changed from {from_state.value} to {to_state.value}")
        
        # Update workflow history
        history = workflow_instance.history or []
        history.append({
            "timestamp": datetime.now().isoformat(),
            "action": "State Transition",
            "from_state": from_state.value,
            "to_state": to_state.value,
            "user": user,
            "comment": comment
        })
        
        workflow_instance.history = json.dumps(history)
        workflow_instance.save()
    
    @staticmethod
    def execute_state_actions(workflow_instance, from_state, to_state, user):
        """
        Execute actions specific to a state transition
        """
        # Actions when transitioning to In Progress
        if to_state == WorkflowState.IN_PROGRESS:
            WorkflowStateMachine.start_workflow_processing(workflow_instance, user)
        
        # Actions when transitioning to Completed
        elif to_state == WorkflowState.COMPLETED:
            WorkflowStateMachine.complete_workflow(workflow_instance, user)
        
        # Actions when transitioning to Rejected
        elif to_state == WorkflowState.REJECTED:
            WorkflowStateMachine.reject_workflow(workflow_instance, user)
        
        # Actions when transitioning to Cancelled
        elif to_state == WorkflowState.CANCELLED:
            WorkflowStateMachine.cancel_workflow(workflow_instance, user)
        
        # Actions when transitioning to On Hold
        elif to_state == WorkflowState.ON_HOLD:
            WorkflowStateMachine.hold_workflow(workflow_instance, user)
        
        # Actions when transitioning from On Hold
        elif from_state == WorkflowState.ON_HOLD and to_state == WorkflowState.IN_PROGRESS:
            WorkflowStateMachine.resume_workflow(workflow_instance, user)
    
    @staticmethod
    def start_workflow_processing(workflow_instance, user):
        """
        Start processing a workflow
        """
        workflow_def = frappe.get_doc("Workflow Definition", workflow_instance.workflow_definition)
        
        # Get the start step
        start_step = workflow_def.get_start_step()
        
        if start_step:
            # Process the start step
            workflow_instance.process_step(start_step)
            
            # Send notification to workflow initiator
            WorkflowStateMachine.send_workflow_notification(
                workflow_instance,
                "Workflow Started",
                f"Your workflow for document {workflow_instance.document} has been started.",
                [workflow_instance.started_by]
            )
    
    @staticmethod
    def complete_workflow(workflow_instance, user):
        """
        Complete a workflow
        """
        # Update document status
        document = frappe.get_doc("Document", workflow_instance.document)
        document.status = "Approved"
        document.save()
        
        # Send notification to workflow initiator
        WorkflowStateMachine.send_workflow_notification(
            workflow_instance,
            "Workflow Completed",
            f"Your workflow for document {workflow_instance.document} has been completed.",
            [workflow_instance.started_by]
        )
        
        # Log completion
        frappe.log_message(
            f"Workflow {workflow_instance.name} for document {workflow_instance.document} completed by {user}",
            "Workflow Completion"
        )
    
    @staticmethod
    def reject_workflow(workflow_instance, user):
        """
        Reject a workflow
        """
        # Update document status
        document = frappe.get_doc("Document", workflow_instance.document)
        document.status = "Rejected"
        document.save()
        
        # Send notification to workflow initiator
        WorkflowStateMachine.send_workflow_notification(
            workflow_instance,
            "Workflow Rejected",
            f"Your workflow for document {workflow_instance.document} has been rejected.",
            [workflow_instance.started_by]
        )
        
        # Log rejection
        frappe.log_message(
            f"Workflow {workflow_instance.name} for document {workflow_instance.document} rejected by {user}",
            "Workflow Rejection"
        )
    
    @staticmethod
    def cancel_workflow(workflow_instance, user):
        """
        Cancel a workflow
        """
        # Update document status
        document = frappe.get_doc("Document", workflow_instance.document)
        document.status = "Cancelled"
        document.save()
        
        # Send notification to workflow initiator
        WorkflowStateMachine.send_workflow_notification(
            workflow_instance,
            "Workflow Cancelled",
            f"Your workflow for document {workflow_instance.document} has been cancelled.",
            [workflow_instance.started_by]
        )
        
        # Log cancellation
        frappe.log_message(
            f"Workflow {workflow_instance.name} for document {workflow_instance.document} cancelled by {user}",
            "Workflow Cancellation"
        )
    
    @staticmethod
    def hold_workflow(workflow_instance, user):
        """
        Put a workflow on hold
        """
        # Send notification to current assignees
        current_step = WorkflowStateMachine.get_current_step(workflow_instance)
        if current_step:
            from .routing import WorkflowRouting
            assignees = WorkflowRouting.get_step_assignees(current_step, workflow_instance.document)
            
            WorkflowStateMachine.send_workflow_notification(
                workflow_instance,
                "Workflow On Hold",
                f"The workflow for document {workflow_instance.document} has been put on hold.",
                assignees
            )
        
        # Log hold
        frappe.log_message(
            f"Workflow {workflow_instance.name} for document {workflow_instance.document} put on hold by {user}",
            "Workflow Hold"
        )
    
    @staticmethod
    def resume_workflow(workflow_instance, user):
        """
        Resume a workflow that was on hold
        """
        # Get the current step and process it
        current_step = WorkflowStateMachine.get_current_step(workflow_instance)
        if current_step:
            workflow_instance.process_step(current_step)
        
        # Send notification to current assignees
        if current_step:
            from .routing import WorkflowRouting
            assignees = WorkflowRouting.get_step_assignees(current_step, workflow_instance.document)
            
            WorkflowStateMachine.send_workflow_notification(
                workflow_instance,
                "Workflow Resumed",
                f"The workflow for document {workflow_instance.document} has been resumed.",
                assignees
            )
        
        # Log resumption
        frappe.log_message(
            f"Workflow {workflow_instance.name} for document {workflow_instance.document} resumed by {user}",
            "Workflow Resumption"
        )
    
    @staticmethod
    def get_current_step(workflow_instance):
        """
        Get the current step of a workflow instance
        """
        workflow_def = frappe.get_doc("Workflow Definition", workflow_instance.workflow_definition)
        return workflow_def.get_step_by_order(workflow_instance.current_step)
    
    @staticmethod
    def send_workflow_notification(workflow_instance, subject, message, recipients):
        """
        Send a workflow notification
        """
        if not recipients:
            return
        
        frappe.sendmail(
            recipients=recipients,
            subject=subject,
            message=message,
            reference_doctype="Workflow Instance",
            reference_name=workflow_instance.name
        )
    
    @staticmethod
    def get_workflow_state(workflow_instance):
        """
        Get the current state of a workflow instance
        """
        return WorkflowState(workflow_instance.status)
    
    @staticmethod
    def is_workflow_active(workflow_instance):
        """
        Check if a workflow instance is active (not completed, rejected, or cancelled)
        """
        state = WorkflowStateMachine.get_workflow_state(workflow_instance)
        return state in [WorkflowState.DRAFT, WorkflowState.PENDING, WorkflowState.IN_PROGRESS, WorkflowState.ON_HOLD]
    
    @staticmethod
    def is_workflow_completed(workflow_instance):
        """
        Check if a workflow instance is completed
        """
        state = WorkflowStateMachine.get_workflow_state(workflow_instance)
        return state == WorkflowState.COMPLETED
    
    @staticmethod
    def is_workflow_rejected(workflow_instance):
        """
        Check if a workflow instance is rejected
        """
        state = WorkflowStateMachine.get_workflow_state(workflow_instance)
        return state == WorkflowState.REJECTED
    
    @staticmethod
    def is_workflow_cancelled(workflow_instance):
        """
        Check if a workflow instance is cancelled
        """
        state = WorkflowStateMachine.get_workflow_state(workflow_instance)
        return state == WorkflowState.CANCELLED
    
    @staticmethod
    def is_workflow_on_hold(workflow_instance):
        """
        Check if a workflow instance is on hold
        """
        state = WorkflowStateMachine.get_workflow_state(workflow_instance)
        return state == WorkflowState.ON_HOLD
    
    @staticmethod
    def get_workflow_statistics(document_type=None):
        """
        Get workflow statistics
        """
        filters = {}
        if document_type:
            filters["document_type"] = document_type
        
        # Get all workflow instances
        workflow_instances = frappe.get_all("Workflow Instance", filters, ["status", "workflow_definition"])
        
        # Initialize statistics
        stats = {
            "total": len(workflow_instances),
            "draft": 0,
            "pending": 0,
            "in_progress": 0,
            "completed": 0,
            "rejected": 0,
            "cancelled": 0,
            "on_hold": 0,
            "by_workflow_definition": {}
        }
        
        # Count by status
        for instance in workflow_instances:
            status = instance.status.lower().replace(" ", "_")
            if status in stats:
                stats[status] += 1
            
            # Count by workflow definition
            if instance.workflow_definition not in stats["by_workflow_definition"]:
                stats["by_workflow_definition"][instance.workflow_definition] = {
                    "total": 0,
                    "draft": 0,
                    "pending": 0,
                    "in_progress": 0,
                    "completed": 0,
                    "rejected": 0,
                    "cancelled": 0,
                    "on_hold": 0
                }
            
            stats["by_workflow_definition"][instance.workflow_definition]["total"] += 1
            if status in stats["by_workflow_definition"][instance.workflow_definition]:
                stats["by_workflow_definition"][instance.workflow_definition][status] += 1
        
        return stats
    
    @staticmethod
    def get_workflow_history(workflow_instance):
        """
        Get the history of a workflow instance
        """
        history = workflow_instance.history or "[]"
        try:
            return json.loads(history)
        except:
            return []
    
    @staticmethod
    def get_workflow_timeline(workflow_instance):
        """
        Get a timeline view of a workflow instance
        """
        history = WorkflowStateMachine.get_workflow_history(workflow_instance)
        
        timeline = []
        
        # Add workflow creation
        timeline.append({
            "timestamp": workflow_instance.creation,
            "event": "Workflow Created",
            "user": workflow_instance.owner,
            "description": f"Workflow {workflow_instance.name} created for document {workflow_instance.document}"
        })
        
        # Add state transitions
        for entry in history:
            if entry.get("action") == "State Transition":
                timeline.append({
                    "timestamp": entry.get("timestamp"),
                    "event": f"State Changed: {entry.get('from_state')} → {entry.get('to_state')}",
                    "user": entry.get("user"),
                    "description": entry.get("comment") or f"Workflow state changed from {entry.get('from_state')} to {entry.get('to_state')}"
                })
        
        # Sort timeline by timestamp
        timeline.sort(key=lambda x: x["timestamp"])
        
        return timeline