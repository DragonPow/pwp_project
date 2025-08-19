import frappe
from frappe import _
from frappe.model.document import Document
import json
from datetime import datetime, timedelta
from pwp_project.pwp_project.workflow import WorkflowRouting, WorkflowStateMachine, WorkflowState, WorkflowActions, WorkflowNotifications

@frappe.whitelist()
def start_workflow(document_name, workflow_definition=None):
    """
    Start a workflow for a document
    """
    if not workflow_definition:
        document = frappe.get_doc("Document", document_name)
        workflow_definition = frappe.db.get_value("Document Type", document.document_type, "workflow")

    if not workflow_definition:
        frappe.throw(_("No workflow definition found for document {0}").format(document_name))

    existing_workflow = frappe.db.exists("Workflow Instance", {
        "document": document_name,
        "status": ["in", ["Pending", "In Progress", "On Hold"]]
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

    # Notify workflow started
    WorkflowNotifications.notify_workflow_started(workflow_instance)

    return workflow_instance.name

@frappe.whitelist()
def execute_workflow_action(workflow_instance, action_name, comment=None, to_step=None):
    """
    Execute a workflow action
    """
    wf_instance = frappe.get_doc("Workflow Instance", workflow_instance)

    # Execute the action
    status = WorkflowActions.execute_action(wf_instance, action_name, frappe.session.user, comment, to_step)

    # Notify workflow action
    WorkflowNotifications.notify_workflow_action(wf_instance, action_name, frappe.session.user, comment)

    return status

@frappe.whitelist()
def get_workflow_status(document_name):
    """
    Get the workflow status for a document
    """
    workflow_instance = frappe.db.get_value("Workflow Instance", {
        "document": document_name,
        "status": ["in", ["Pending", "In Progress", "On Hold"]]
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
    """
    Get pending actions for a user
    """
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
                "actions": actions
            })

    return pending_actions

@frappe.whitelist()
def get_workflow_instance_details(workflow_instance_name):
    """
    Get details of a workflow instance
    """
    workflow_instance = frappe.get_doc("Workflow Instance", workflow_instance_name)
    workflow_definition = frappe.get_doc("Workflow Definition", workflow_instance.workflow_definition)

    current_step = workflow_definition.get_step_by_order(workflow_instance.current_step)

    result = {
        "workflow_instance": workflow_instance.as_dict(),
        "workflow_definition": workflow_definition.as_dict(),
        "current_step": current_step.as_dict() if current_step else None,
        "pending_actions": [],
        "history": []
    }

    # Get pending actions for current user
    if workflow_instance.status == "In Progress" and current_step:
        actions = WorkflowActions.get_available_actions(workflow_instance, frappe.session.user)
        result["pending_actions"] = actions

    # Get workflow history
    history = workflow_instance.history or "[]"
    try:
        result["history"] = json.loads(history)
    except:
        result["history"] = []

    return result

@frappe.whitelist()
def get_workflow_definitions(doctype=None):
    """
    Get workflow definitions
    """
    filters = {"is_active": 1}
    if doctype:
        filters["document_type"] = doctype

    return frappe.get_all("Workflow Definition", filters=filters, fields=["name", "workflow_name", "document_type"])

@frappe.whitelist()
def get_default_workflow_definition(doctype):
    """
    Get the default workflow definition for a document type
    """
    return frappe.db.get_value("Workflow Definition", {"document_type": doctype, "is_active": 1, "is_default": 1}, "name")

@frappe.whitelist()
def get_workflow_statistics(document_type=None):
    """
    Get workflow statistics
    """
    return WorkflowStateMachine.get_workflow_statistics(document_type)

@frappe.whitelist()
def get_workflow_timeline(workflow_instance_name):
    """
    Get the timeline of a workflow instance
    """
    workflow_instance = frappe.get_doc("Workflow Instance", workflow_instance_name)
    return WorkflowStateMachine.get_workflow_timeline(workflow_instance)

@frappe.whitelist()
def get_workflow_path(workflow_instance_name):
    """
    Get the path of a workflow instance
    """
    workflow_instance = frappe.get_doc("Workflow Instance", workflow_instance_name)
    path = WorkflowRouting.get_workflow_path(workflow_instance)

    return [step.as_dict() for step in path]

@frappe.whitelist()
def can_approve(workflow_instance_name):
    """
    Check if current user can approve the workflow
    """
    workflow_instance = frappe.get_doc("Workflow Instance", workflow_instance_name)
    return WorkflowActions.can_approve(workflow_instance, frappe.session.user)

@frappe.whitelist()
def can_reject(workflow_instance_name):
    """
    Check if current user can reject the workflow
    """
    workflow_instance = frappe.get_doc("Workflow Instance", workflow_instance_name)
    return WorkflowActions.can_reject(workflow_instance, frappe.session.user)

@frappe.whitelist()
def can_request_changes(workflow_instance_name):
    """
    Check if current user can request changes for the workflow
    """
    workflow_instance = frappe.get_doc("Workflow Instance", workflow_instance_name)
    return WorkflowActions.can_request_changes(workflow_instance, frappe.session.user)

@frappe.whitelist()
def can_forward(workflow_instance_name):
    """
    Check if current user can forward the workflow
    """
    workflow_instance = frappe.get_doc("Workflow Instance", workflow_instance_name)
    return WorkflowActions.can_forward(workflow_instance, frappe.session.user)

@frappe.whitelist()
def can_skip(workflow_instance_name):
    """
    Check if current user can skip the current step
    """
    workflow_instance = frappe.get_doc("Workflow Instance", workflow_instance_name)
    return WorkflowActions.can_skip(workflow_instance, frappe.session.user)

@frappe.whitelist()
def get_workflow_participants(workflow_instance_name):
    """
    Get all participants in a workflow
    """
    workflow_instance = frappe.get_doc("Workflow Instance", workflow_instance_name)
    return WorkflowNotifications.get_workflow_participants(workflow_instance)

@frappe.whitelist()
def send_workflow_reminder(workflow_instance_name):
    """
    Send a reminder for a workflow step
    """
    workflow_instance = frappe.get_doc("Workflow Instance", workflow_instance_name)
    WorkflowNotifications.send_workflow_reminder(workflow_instance)
    return True

@frappe.whitelist()
def duplicate_workflow(workflow_definition_name):
    """
    Duplicate a workflow definition
    """
    workflow_definition = frappe.get_doc("Workflow Definition", workflow_definition_name)

    # Create a new workflow definition
    new_workflow = frappe.new_doc("Workflow Definition")
    new_workflow.workflow_name = f"{workflow_definition.workflow_name} (Copy)"
    new_workflow.description = workflow_definition.description
    new_workflow.document_type = workflow_definition.document_type
    new_workflow.is_active = 0
    new_workflow.is_default = 0
    new_workflow.allow_parallel_steps = workflow_definition.allow_parallel_steps
    new_workflow.auto_start_on_creation = workflow_definition.auto_start_on_creation
    new_workflow.timeout_days = workflow_definition.timeout_days
    new_workflow.escalation_days = workflow_definition.escalation_days
    new_workflow.notify_on_timeout = workflow_definition.notify_on_timeout
    new_workflow.notify_on_escalation = workflow_definition.notify_on_escalation

    # Copy steps
    for step in workflow_definition.steps:
        new_step = new_workflow.append('steps', {})
        new_step.step_name = step.step_name
        new_step.description = step.description
        new_step.step_type = step.step_type
        new_step.step_order = step.step_order
        new_step.assignee_type = step.assignee_type
        new_step.assignee_value = step.assignee_value
        new_step.timeout_days = step.timeout_days
        new_step.escalation_days = step.escalation_days
        new_step.notify_on_timeout = step.notify_on_timeout
        new_step.notify_on_escalation = step.notify_on_escalation
        new_step.allow_skip = step.allow_skip
        new_step.allow_reject = step.allow_reject
        new_step.custom_script = step.custom_script

        # Copy actions
        for action in step.actions:
            new_action = new_step.append('actions', {})
            new_action.action_name = action.action_name
            new_action.action_type = action.action_type
            new_action.role = action.role
            new_action.next_step = action.next_step
            new_action.custom_script = action.custom_script

        # Copy conditions
        for condition in step.conditions:
            new_condition = new_step.append('conditions', {})
            new_condition.condition_name = condition.condition_name
            new_condition.condition_type = condition.condition_type
            new_condition.field_name = condition.field_name
            new_condition.operator = condition.operator
            new_condition.value = condition.value
            new_condition.logical_operator = condition.logical_operator

    # Copy permissions
    for permission in workflow_definition.permissions:
        new_permission = new_workflow.append('permissions', {})
        new_permission.role = permission.role
        new_permission.permission_level = permission.permission_level

    new_workflow.save()

    return new_workflow.name

@frappe.whitelist()
def activate_workflow(workflow_definition_name):
    """
    Activate a workflow definition
    """
    workflow_definition = frappe.get_doc("Workflow Definition", workflow_definition_name)
    workflow_definition.is_active = 1
    workflow_definition.save()

    return True

@frappe.whitelist()
def deactivate_workflow(workflow_definition_name):
    """
    Deactivate a workflow definition
    """
    workflow_definition = frappe.get_doc("Workflow Definition", workflow_definition_name)
    workflow_definition.is_active = 0
    workflow_definition.save()

    return True

@frappe.whitelist()
def get_assignee_options(doctype):
    """
    Get assignee options for a document type
    """
    # Get document fields
    document_fields = frappe.get_meta(doctype).get("fields")

    # Filter for user and role fields
    user_fields = [field for field in document_fields if field.fieldtype in ["Link", "Select"] and field.options in ["User", "Role"]]

    # Get all roles
    roles = frappe.get_all("Role", {"disabled": 0}, ["name"])

    # Get all users
    users = frappe.get_all("User", {"enabled": 1}, ["name", "full_name"])

    return {
        "fields": [{"label": field.label, "value": field.fieldname} for field in user_fields],
        "roles": [{"label": role.name, "value": role.name} for role in roles],
        "users": [{"label": f"{user.full_name} ({user.name})", "value": user.name} for user in users]
    }

@frappe.whitelist()
def get_document_fields(doctype):
    """
    Get fields for a document type
    """
    document_fields = frappe.get_meta(doctype).get("fields")

    # Filter for relevant field types
    relevant_fields = [field for field in document_fields if field.fieldtype in [
        "Data", "Link", "Select", "Check", "Date", "Datetime", "Time", "Int", "Float", "Percent", "Currency"
    ]]

    return [{"label": field.label, "value": field.fieldname, "type": field.fieldtype} for field in relevant_fields]
