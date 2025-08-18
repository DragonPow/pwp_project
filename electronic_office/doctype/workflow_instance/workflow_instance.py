import frappe
from frappe.model.document import Document
from frappe import _
import json
from datetime import datetime, timedelta
import uuid
from electronic_office.electronic_office.workflow import WorkflowRouting, WorkflowStateMachine, WorkflowState, WorkflowActions, WorkflowNotifications

class WorkflowInstance(Document):
    def validate(self):
        self.validate_workflow_definition()
        self.validate_document()
        self.validate_status()
    
    def validate_workflow_definition(self):
        if not frappe.db.exists("Workflow Definition", self.workflow_definition):
            frappe.throw(_("Workflow Definition {0} does not exist").format(self.workflow_definition))
        
        # Check if workflow definition is active
        workflow_def = frappe.get_doc("Workflow Definition", self.workflow_definition)
        if not workflow_def.is_active:
            frappe.throw(_("Workflow Definition {0} is not active").format(self.workflow_definition))
    
    def validate_document(self):
        if not frappe.db.exists("Document", self.document):
            frappe.throw(_("Document {0} does not exist").format(self.document))
    
    def validate_status(self):
        if self.status == "Completed" and not self.completed_on:
            self.completed_on = datetime.now()
        
        if self.status == "Completed" and not self.completed_by:
            self.completed_by = frappe.session.user
    
    def on_submit(self):
        self.start_workflow()
    
    def start_workflow(self):
        # Use state machine to transition to In Progress
        WorkflowStateMachine.transition_to(self, WorkflowState.IN_PROGRESS, frappe.session.user)
        self.initialize_history()
        self.save()
        
        workflow_def = frappe.get_doc("Workflow Definition", self.workflow_definition)
        start_step = workflow_def.get_start_step()
        
        if start_step:
            self.process_step(start_step)
            self.add_to_history("Workflow Started", f"Workflow started by {frappe.session.user}")
    
    def initialize_history(self):
        if not self.history:
            self.history = json.dumps([])
    
    def add_to_history(self, action, description):
        if not self.history:
            self.initialize_history()
        
        history_list = json.loads(self.history)
        history_entry = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "description": description,
            "user": frappe.session.user,
            "step": self.current_step
        }
        
        history_list.append(history_entry)
        self.history = json.dumps(history_list)
        self.save()
    
    def process_step(self, step):
        assignees = WorkflowRouting.get_step_assignees(step, self.document)
        
        # Update current assignees
        self.current_assignees = assignees
        self.save()
        
        for assignee in assignees:
            self.create_task_for_step(step, assignee)
        
        self.check_step_timeout(step)
        # Notify step assigned
        WorkflowNotifications.notify_step_assigned(self, step, assignees)
        self.add_to_history("Step Processed", f"Step '{step.step_name}' processed with assignees: {', '.join(assignees)}")
    
    def get_step_assignees(self, step):
        return WorkflowRouting.get_step_assignees(step, self.document)
    
    def get_dynamic_assignees(self, step):
        return WorkflowRouting.evaluate_dynamic_assignee(step, frappe.get_doc("Document", self.document), frappe.session.user)
    
    def create_task_for_step(self, step, assignee):
        task = frappe.new_doc("Task")
        task.title = f"{step.step_name} - {self.document}"
        task.description = step.description or f"Workflow task for {step.step_name}"
        task.document = self.document
        task.assigned_to = assignee
        task.assigned_by = frappe.session.user
        task.assigned_on = datetime.now()
        task.task_type = step.step_type
        task.due_date = datetime.now() + timedelta(days=step.timeout_days or 1)
        task.save()
        
        frappe.db.commit()
    
    def check_step_timeout(self, step):
        if step.timeout_days:
            timeout_date = datetime.now() + timedelta(days=step.timeout_days)
            frappe.enqueue(
                "electronic_office.electronic_office.workflow.notifications.check_step_timeout",
                workflow_instance=self.name,
                step_name=step.step_name,
                timeout_date=timeout_date,
                queue="long"
            )
    
    def execute_action(self, action_name, user):
        # Use workflow actions to execute the action
        return WorkflowActions.execute_action(self, action_name, user)
    
    def can_execute_action(self, action, user):
        return WorkflowRouting.is_action_allowed(action, user, self.document)
    
    def evaluate_conditions(self, conditions):
        document = frappe.get_doc("Document", self.document)
        return WorkflowRouting.evaluate_action_conditions({"conditions": conditions}, document)
    
    def compare_values(self, field_value, operator, value):
        if operator == "equals":
            return str(field_value) == str(value)
        elif operator == "not equals":
            return str(field_value) != str(value)
        elif operator == "contains":
            return str(value) in str(field_value)
        elif operator == "not contains":
            return str(value) not in str(field_value)
        
        return False
    
    def process_action(self, action, current_step):
        # This method is now handled by WorkflowActions
        pass
    
    def move_to_next_step(self):
        # This method is now handled by WorkflowStateMachine and WorkflowRouting
        pass
    
    def update_document_status(self):
        document = frappe.get_doc("Document", self.document)
        
        if self.status == "Completed":
            document.status = "Approved"
        elif self.status == "Cancelled":
            document.status = "Rejected"
        elif self.status == "In Progress":
            document.status = "In Review"
        elif self.status == "Draft":
            document.status = "Draft"
        elif self.status == "On Hold":
            document.status = "On Hold"
        elif self.status == "Rejected":
            document.status = "Rejected"
        
        document.save()
        self.add_to_history("Document Status Updated", f"Document status updated to {document.status}")
    
    def get_pending_actions(self, user):
        return WorkflowActions.get_available_actions(self, user)
    
    def is_user_assigned_to_step(self, step, user):
        return WorkflowRouting.is_user_assigned_to_step(step, user, self.document)
    
    def notify_assignees(self, step, assignees):
        # This method is now handled by WorkflowNotifications.notify_step_assigned
        pass
    
    def notify_document_owner(self, subject, message):
        # This method is now handled by WorkflowNotifications.notify_document_owner
        pass
    
    def get_workflow_history(self):
        if not self.history:
            return []
        
        return json.loads(self.history)
    
    def cancel_workflow(self, reason):
        if self.status in ["Completed", "Cancelled"]:
            frappe.throw(_("Cannot cancel a workflow that is already completed or cancelled"))
        
        WorkflowStateMachine.transition_to(self, WorkflowState.CANCELLED, frappe.session.user, reason)

def check_step_timeout_job(workflow_instance, step_name, timeout_date):
    if datetime.now() < timeout_date:
        remaining_time = timeout_date - datetime.now()
        frappe.enqueue(
            "electronic_office.electronic_office.workflow.notifications.check_step_timeout",
            workflow_instance=workflow_instance,
            step_name=step_name,
            timeout_date=timeout_date,
            queue="long",
            enqueue_after_minutes=remaining_time.total_seconds() / 60
        )
        return
    
    wf_instance = frappe.get_doc("Workflow Instance", workflow_instance)
    if wf_instance.status != "Completed" and wf_instance.status != "Rejected":
        workflow_def = frappe.get_doc("Workflow Definition", wf_instance.workflow_definition)
        current_step = workflow_def.get_step_by_order(wf_instance.current_step)
        
        if current_step and current_step.step_name == step_name:
            if current_step.notify_on_timeout:
                WorkflowNotifications.notify_step_timeout(wf_instance, current_step)
            
            if current_step.escalation_days:
                WorkflowNotifications.escalate_step(wf_instance, current_step)

def notify_step_timeout(workflow_instance, step):
    # This function is now handled by WorkflowNotifications.notify_step_timeout
    pass

def escalate_step(workflow_instance, step):
    # This function is now handled by WorkflowNotifications.escalate_step
    pass

@frappe.whitelist()
def start_workflow(document_name, workflow_definition=None):
    if not workflow_definition:
        document = frappe.get_doc("Document", document_name)
        workflow_definition = frappe.db.get_value("Document Type", document.document_type, "workflow")
    
    if not workflow_definition:
        frappe.throw(_("No workflow definition found for document {0}").format(document_name))
    
    existing_workflow = frappe.db.exists("Workflow Instance", {
        "document": document_name,
        "status": ["in", ["Pending", "In Progress"]]
    })
    
    if existing_workflow:
        frappe.throw(_("Workflow already exists for document {0}").format(document_name))
    
    workflow_instance = frappe.new_doc("Workflow Instance")
    workflow_instance.document = document_name
    workflow_instance.workflow_definition = workflow_definition
    workflow_instance.status = "Pending"
    workflow_instance.started_by = frappe.session.user
    workflow_instance.started_on = datetime.now()
    workflow_instance.current_step = 1
    workflow_instance.save()
    workflow_instance.submit()
    
    return workflow_instance.name

@frappe.whitelist()
def execute_workflow_action(workflow_instance, action_name):
    wf_instance = frappe.get_doc("Workflow Instance", workflow_instance)
    return WorkflowActions.execute_action(wf_instance, action_name, frappe.session.user)

@frappe.whitelist()
def get_workflow_status(document_name):
    workflow_instance = frappe.db.get_value("Workflow Instance", {
        "document": document_name,
        "status": ["in", ["Pending", "In Progress"]]
    }, ["name", "status", "current_step", "workflow_definition"])
    
    if workflow_instance:
        return {
            "workflow_instance": workflow_instance[0],
            "status": workflow_instance[1],
            "current_step": workflow_instance[2],
            "workflow_definition": workflow_instance[3]
        }
    
    return None

@frappe.whitelist()
def get_pending_actions(user=None):
    if not user:
        user = frappe.session.user
    
    pending_actions = []
    
    workflow_instances = frappe.get_all("Workflow Instance", {
        "status": "In Progress"
    }, ["name", "document", "workflow_definition", "current_step"])
    
    for wf_instance in workflow_instances:
        instance = frappe.get_doc("Workflow Instance", wf_instance.name)
        actions = WorkflowActions.get_available_actions(instance, user)
        
        if actions:
            pending_actions.append({
                "workflow_instance": wf_instance.name,
                "document": wf_instance.document,
                "workflow_definition": wf_instance.workflow_definition,
                "current_step": wf_instance.current_step,
                "actions": [action.action_name for action in actions]
            })
    
    return pending_actions
@frappe.whitelist()
def cancel_workflow_instance(workflow_instance, reason):
    wf_instance = frappe.get_doc("Workflow Instance", workflow_instance)
    WorkflowStateMachine.transition_to(wf_instance, WorkflowState.CANCELLED, frappe.session.user, reason)
    return wf_instance.status

@frappe.whitelist()
def get_workflow_history(workflow_instance):
    wf_instance = frappe.get_doc("Workflow Instance", workflow_instance)
    return wf_instance.get_workflow_history()

@frappe.whitelist()
def reassign_workflow_step(workflow_instance, new_assignee):
    wf_instance = frappe.get_doc("Workflow Instance", workflow_instance)
    
    if wf_instance.status != "In Progress":
        frappe.throw(_("Can only reassign steps for workflows in progress"))
    
    # Update current assignees
    if new_assignee not in wf_instance.current_assignees:
        wf_instance.current_assignees.append(new_assignee)
        wf_instance.save()
        
        # Create a new task for the new assignee
        workflow_def = frappe.get_doc("Workflow Definition", wf_instance.workflow_definition)
        current_step = workflow_def.get_step_by_order(wf_instance.current_step)
        
        if current_step:
            wf_instance.create_task_for_step(current_step, new_assignee)
        
        wf_instance.add_to_history("Step Reassigned", f"Step reassigned to {new_assignee} by {frappe.session.user}")
        
        # Notify the new assignee
        WorkflowNotifications.notify_step_reassigned(wf_instance, current_step, new_assignee)
    
    return wf_instance.current_assignees

@frappe.whitelist()
def get_workflow_instance_details(workflow_instance_name):
    wf_instance = frappe.get_doc("Workflow Instance", workflow_instance_name)
    workflow_def = frappe.get_doc("Workflow Definition", wf_instance.workflow_definition)
    
    # Get current step details
    current_step = workflow_def.get_step_by_order(wf_instance.current_step)
    
    # Get pending actions for current user
    pending_actions = []
    if current_step and wf_instance.status == "In Progress":
        pending_actions = WorkflowActions.get_available_actions(wf_instance, frappe.session.user)
    
    return {
        "workflow_instance": wf_instance,
        "workflow_definition": workflow_def,
        "current_step": current_step,
        "pending_actions": pending_actions,
        "history": wf_instance.get_workflow_history()
    }