import frappe
from frappe.model.document import Document
from frappe import _

class WorkflowDefinition(Document):
    def validate(self):
        self.validate_steps()
        self.validate_default_workflow()
        self.validate_transitions()
    
    def validate_steps(self):
        if not self.steps:
            frappe.throw(_("Workflow must have at least one step"))
        
        step_orders = [step.step_order for step in self.steps]
        if len(step_orders) != len(set(step_orders)):
            frappe.throw(_("Step orders must be unique"))
        
        if min(step_orders) != 1:
            frappe.throw(_("First step order must be 1"))
        
        start_steps = [step for step in self.steps if step.step_type == "Start"]
        if len(start_steps) != 1:
            frappe.throw(_("Workflow must have exactly one Start step"))
        
        end_steps = [step for step in self.steps if step.step_type == "End"]
        if not end_steps:
            frappe.throw(_("Workflow must have at least one End step"))
    
    def validate_transitions(self):
        if self.transitions:
            # Validate that all transitions reference valid steps
            step_names = [step.name for step in self.steps]
            
            for transition in self.transitions:
                if transition.from_step not in step_names:
                    frappe.throw(_("Transition references invalid from step: {0}").format(transition.from_step))
                
                if transition.to_step not in step_names:
                    frappe.throw(_("Transition references invalid to step: {0}").format(transition.to_step))
    
    def validate_default_workflow(self):
        if self.is_default:
            existing_default = frappe.db.exists("Workflow Definition", {
                "document_type": self.document_type,
                "is_default": 1,
                "name": ["!=", self.name]
            })
            
            if existing_default:
                frappe.throw(_("There can be only one default workflow for document type {0}").format(self.document_type))
    
    def on_update(self):
        if self.is_active:
            self.update_document_type_workflow()
        else:
            # If workflow is not active, remove it from document type if it was set as the workflow
            doc_type = frappe.get_doc("Document Type", self.document_type)
            if doc_type.workflow == self.name:
                doc_type.workflow = None
                doc_type.save()
    
    def update_document_type_workflow(self):
        doc_type = frappe.get_doc("Document Type", self.document_type)
        doc_type.workflow = self.name
        doc_type.save()
    
    def get_start_step(self):
        for step in self.steps:
            if step.step_type == "Start":
                return step
        return None
    
    def get_step_by_order(self, order):
        for step in self.steps:
            if step.step_order == order:
                return step
        return None
    
    def get_step_by_name(self, name):
        for step in self.steps:
            if step.name == name:
                return step
        return None
    
    def get_next_step(self, current_step_order):
        next_order = current_step_order + 1
        return self.get_step_by_order(next_order)
    
    def get_steps_for_user(self, user):
        user_roles = frappe.get_roles(user)
        user_steps = []
        
        for step in self.steps:
            if step.assignee_type == "Role" and step.assignee_value in user_roles:
                user_steps.append(step)
            elif step.assignee_type == "User" and step.assignee_value == user:
                user_steps.append(step)
            elif step.allowed_roles:
                for role in user_roles:
                    if role in step.allowed_roles:
                        user_steps.append(step)
                        break
        
        return user_steps
    
    def get_transition(self, from_step, to_step):
        for transition in self.transitions:
            if transition.from_step == from_step and transition.to_step == to_step:
                return transition
        return None
    
    def get_transitions_from_step(self, from_step):
        transitions = []
        for transition in self.transitions:
            if transition.from_step == from_step:
                transitions.append(transition)
        return transitions
    
    def evaluate_workflow_conditions(self, document):
        """
        Evaluate workflow conditions for a document
        """
        if not self.conditions:
            return True
            
        document_doc = frappe.get_doc(document.doctype, document.name)
        
        for condition in self.conditions:
            if not self.evaluate_single_condition(condition, document_doc):
                return False
        
        return True
    
    def evaluate_single_condition(self, condition, document):
        """
        Evaluate a single workflow condition
        """
        try:
            # Get the field value from the document
            field_value = document.get(condition.field)
            
            # Convert to appropriate type for comparison
            if field_value is None:
                field_value = ""
                
            # Compare based on operator
            if condition.operator == "equals":
                return str(field_value) == condition.value
            elif condition.operator == "not_equals":
                return str(field_value) != condition.value
            elif condition.operator == "contains":
                return condition.value in str(field_value)
            elif condition.operator == "not_contains":
                return condition.value not in str(field_value)
            elif condition.operator == "starts_with":
                return str(field_value).startswith(condition.value)
            elif condition.operator == "ends_with":
                return str(field_value).endswith(condition.value)
            elif condition.operator == "greater_than":
                try:
                    return float(field_value) > float(condition.value)
                except:
                    return False
            elif condition.operator == "less_than":
                try:
                    return float(field_value) < float(condition.value)
                except:
                    return False
            elif condition.operator == "greater_than_or_equal":
                try:
                    return float(field_value) >= float(condition.value)
                except:
                    return False
            elif condition.operator == "less_than_or_equal":
                try:
                    return float(field_value) <= float(condition.value)
                except:
                    return False
            elif condition.operator == "in":
                values = condition.value.split(",")
                return str(field_value) in [v.strip() for v in values]
            elif condition.operator == "not_in":
                values = condition.value.split(",")
                return str(field_value) not in [v.strip() for v in values]
                
        except Exception as e:
            frappe.log_error(_("Error evaluating workflow condition: {0}").format(str(e)),
                            "Workflow Condition Evaluation")
            return False
            
        return False
    
    def get_workflow_permissions(self, user):
        """
        Get workflow permissions for a user
        """
        user_roles = frappe.get_roles(user)
        user_permissions = []
        
        for permission in self.permissions:
            if permission.role in user_roles:
                user_permissions.append(permission)
        
        return user_permissions
    
    def check_workflow_permission(self, user, permission_type):
        """
        Check if a user has a specific permission for this workflow
        """
        user_roles = frappe.get_roles(user)
        
        for permission in self.permissions:
            if permission.role in user_roles:
                if permission_type == "create" and permission.allow_create:
                    return True
                elif permission_type == "read" and permission.allow_read:
                    return True
                elif permission_type == "write" and permission.allow_write:
                    return True
                elif permission_type == "delete" and permission.allow_delete:
                    return True
                elif permission_type == "share" and permission.allow_share:
                    return True
                elif permission_type == "export" and permission.allow_export:
                    return True
                elif permission_type == "print" and permission.allow_print:
                    return True
                elif permission_type == "email" and permission.allow_email:
                    return True
                elif permission_type == "report" and permission.allow_report:
                    return True
        
        return False

@frappe.whitelist()
def get_workflow_definitions(doctype=None):
    filters = {"is_active": 1}
    if doctype:
        filters["document_type"] = doctype
    
    return frappe.get_all("Workflow Definition", filters=filters, fields=["name", "workflow_name", "document_type"])

@frappe.whitelist()
def get_default_workflow_definition(doctype):
    return frappe.db.get_value("Workflow Definition", {"document_type": doctype, "is_default": 1}, "name")

@frappe.whitelist()
def get_workflow_definition_details(workflow_name):
    workflow_def = frappe.get_doc("Workflow Definition", workflow_name)
    
    # Get steps with their details
    steps = []
    for step in workflow_def.steps:
        steps.append({
            "name": step.name,
            "step_name": step.step_name,
            "description": step.description,
            "step_type": step.step_type,
            "step_order": step.step_order,
            "assignee_type": step.assignee_type,
            "assignee_value": step.assignee_value,
            "allowed_roles": step.allowed_roles,
            "time_limit": step.time_limit,
            "timeout_days": step.timeout_days,
            "escalation_days": step.escalation_days,
            "notify_on_timeout": step.notify_on_timeout,
            "notify_on_escalation": step.notify_on_escalation,
            "allow_skip": step.allow_skip,
            "allow_reject": step.allow_reject
        })
    
    # Get transitions with their details
    transitions = []
    for transition in workflow_def.transitions:
        transitions.append({
            "name": transition.name,
            "from_step": transition.from_step,
            "to_step": transition.to_step,
            "auto_transition": transition.auto_transition,
            "notify_on_transition": transition.notify_on_transition
        })
    
    # Get conditions with their details
    conditions = []
    if workflow_def.conditions:
        for condition in workflow_def.conditions:
            conditions.append({
                "name": condition.name,
                "condition_name": condition.condition_name,
                "description": condition.description,
                "condition_type": condition.condition_type,
                "field_name": condition.field_name,
                "operator": condition.operator,
                "value": condition.value,
                "role": condition.role,
                "document_type": condition.document_type,
                "logical_operator": condition.logical_operator
            })
    
    # Get permissions with their details
    permissions = []
    for permission in workflow_def.permissions:
        permissions.append({
            "name": permission.name,
            "role": permission.role,
            "permission_level": permission.permission_level,
            "allow_create": permission.allow_create,
            "allow_read": permission.allow_read,
            "allow_write": permission.allow_write,
            "allow_delete": permission.allow_delete,
            "allow_share": permission.allow_share,
            "allow_export": permission.allow_export,
            "allow_print": permission.allow_print,
            "allow_email": permission.allow_email,
            "allow_report": permission.allow_report,
            "if_owner": permission.if_owner
        })
    
    return {
        "workflow_definition": workflow_def,
        "steps": steps,
        "transitions": transitions,
        "conditions": conditions,
        "permissions": permissions
    }

@frappe.whitelist()
def test_workflow_conditions(workflow_name, document_name):
    workflow_def = frappe.get_doc("Workflow Definition", workflow_name)
    document = frappe.get_doc("Document", document_name)
    
    return workflow_def.evaluate_workflow_conditions(document)