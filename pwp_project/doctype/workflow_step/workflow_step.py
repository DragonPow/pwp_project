# Copyright (c) 2025, Government Agency and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _

class WorkflowStep(Document):
    def validate(self):
        self.validate_step_name()
        self.validate_step_type()
        self.validate_assignee()
        self.validate_actions()
        self.validate_allowed_roles()
        
    def validate_step_name(self):
        if not self.step_name:
            frappe.throw(_("Step Name is required"))
            
    def validate_step_type(self):
        if self.step_type == "Start" or self.step_type == "End":
            # For Start and End steps, assignee should be None
            self.assignee_type = "None"
            self.assignee_value = ""
            
    def validate_assignee(self):
        if self.assignee_type != "None" and not self.assignee_value:
            frappe.throw(_("Assignee Value is required for {0} assignee type").format(self.assignee_type))
            
        # Validate assignee value based on type
        if self.assignee_type == "Role":
            if not frappe.db.exists("Role", self.assignee_value):
                frappe.throw(_("Role '{0}' does not exist").format(self.assignee_value))
        elif self.assignee_type == "User":
            if not frappe.db.exists("User", self.assignee_value):
                frappe.throw(_("User '{0}' does not exist").format(self.assignee_value))
                
    def validate_actions(self):
        # Ensure that at least one action is defined for non-end steps
        if self.step_type not in ["End", "Notification"] and not self.actions:
            frappe.throw(_("At least one action must be defined for {0} steps").format(self.step_type))
            
    def validate_allowed_roles(self):
        if self.allowed_roles:
            for role in self.allowed_roles:
                if not frappe.db.exists("Role", role):
                    frappe.throw(_("Role '{0}' does not exist").format(role))
            
    def get_assignees(self, document=None):
        """
        Get the list of assignees for this step based on assignee type
        """
        if self.assignee_type == "None":
            return []
            
        elif self.assignee_type == "Role":
            # Get all users with this role
            users = frappe.get_all("User", {
                "enabled": 1
            }, ["name"])
            
            # Filter users with the specified role
            assignees = []
            for user in users:
                if frappe.has_role(self.assignee_value, user.name):
                    assignees.append(user.name)
            return assignees
            
        elif self.assignee_type == "User":
            return [self.assignee_value]
            
        elif self.assignee_type == "Field-based":
            if not document:
                return []
                
            # Get the document
            doc = frappe.get_doc(document.doctype, document.name)
            
            # Get the field value
            field_value = doc.get(self.assignee_value)
            
            if not field_value:
                return []
                
            # If field value is a user, return it
            if frappe.db.exists("User", field_value):
                return [field_value]
                
            # If field value is a role, get all users with that role
            if frappe.db.exists("Role", field_value):
                users = frappe.get_all("User", {
                    "enabled": 1
                }, ["name"])
                
                assignees = []
                for user in users:
                    if frappe.has_role(field_value, user.name):
                        assignees.append(user.name)
                return assignees
                
            return []
            
        elif self.assignee_type == "Dynamic":
            if not self.custom_script:
                return []
                
            # Execute custom script to get assignees
            try:
                # Create a safe environment for execution
                env = {
                    "frappe": frappe,
                    "document": document
                }
                
                # Execute the script
                exec(self.custom_script, env)
                
                # Get the result from the script
                if "get_assignees" in env:
                    return env["get_assignees"]()
                    
            except Exception as e:
                frappe.log_error(_("Error executing custom script for dynamic assignees: {0}").format(str(e)),
                                "Workflow Step Dynamic Assignees")
                
            return []
            
        return []
        
    def get_allowed_users(self, document=None):
        """
        Get the list of users who are allowed to perform this step
        This includes both assignees and users with allowed roles
        """
        allowed_users = []
        
        # Get assignees
        assignees = self.get_assignees(document)
        allowed_users.extend(assignees)
        
        # Get users with allowed roles
        if self.allowed_roles:
            for role in self.allowed_roles:
                users = frappe.get_users_by_role(role)
                for user in users:
                    if user.name not in allowed_users:
                        allowed_users.append(user.name)
        
        return list(set(allowed_users))  # Remove duplicates
        
    def get_available_actions(self, user, document=None):
        """
        Get available actions for a user at this step
        """
        if not self.actions:
            return []
            
        available_actions = []
        
        for action in self.actions:
            # Check if user has permission for this action
            if self.is_action_allowed(action, user, document):
                available_actions.append(action)
                
        return available_actions
        
    def is_action_allowed(self, action, user, document=None):
        """
        Check if a user is allowed to perform a specific action
        """
        # Check if user is allowed for this step
        allowed_users = self.get_allowed_users(document)
        if user not in allowed_users:
            return False
            
        # Check action permissions
        if action.role and not frappe.has_role(action.role, user):
            return False
            
        # Check action conditions
        if action.conditions:
            return self.evaluate_conditions(action.conditions, document)
            
        return True
        
    def evaluate_conditions(self, conditions, document):
        """
        Evaluate conditions to determine if an action is allowed
        """
        if not conditions:
            return True
            
        if not document:
            return False
            
        # Get the document
        doc = frappe.get_doc(document.doctype, document.name)
        
        # Evaluate each condition
        all_conditions_met = True
        any_condition_met = False
        
        for condition in conditions:
            condition_met = self.evaluate_single_condition(condition, doc)
            
            if condition.logical_operator == "AND":
                all_conditions_met = all_conditions_met and condition_met
            elif condition.logical_operator == "OR":
                any_condition_met = any_condition_met or condition_met
                
        # If all conditions use AND, return if all are met
        # If any condition uses OR, return if any is met
        if any_condition_met:
            return True
            
        return all_conditions_met
        
    def evaluate_single_condition(self, condition, document):
        """
        Evaluate a single condition
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
            frappe.log_error("Error evaluating condition: {0}".format(str(e)), 
                            "Workflow Step Condition Evaluation")
            return False
            
        return False
        
    def get_next_steps(self, workflow_definition):
        """
        Get possible next steps based on transitions
        """
        # Get transitions from this step
        transitions = frappe.get_all("Workflow Transition", {
            "workflow_definition": workflow_definition,
            "from_step": self.name
        })
        
        next_steps = []
        for transition in transitions:
            to_step = frappe.get_doc("Workflow Step", transition.to_step)
            if to_step:
                next_steps.append(to_step)
                
        # If no transitions defined, get next step by order
        if not next_steps:
            next_step = frappe.get_all("Workflow Step", {
                "parent": workflow_definition,
                "parenttype": "Workflow Definition",
                "step_order": self.step_order + 1
            })
            
            if next_step:
                next_steps.append(frappe.get_doc("Workflow Step", next_step[0].name))
                
        return next_steps
        
    def get_timeout_date(self):
        """
        Get the timeout date for this step
        """
        # Use time_limit in hours if specified, otherwise use timeout_days
        if self.time_limit:
            from frappe.utils import add_hours, now_datetime
            return add_hours(now_datetime(), self.time_limit)
        elif self.timeout_days:
            from frappe.utils import add_days, nowdate
            return add_days(nowdate(), self.timeout_days)
        return None
        
    def get_escalation_date(self):
        """
        Get the escalation date for this step
        """
        if not self.escalation_days:
            return None
            
        from frappe.utils import add_days, nowdate
        return add_days(nowdate(), self.escalation_days)
        
    def evaluate_step_conditions(self, document):
        """
        Evaluate conditions for step execution
        """
        if not self.conditions:
            return True
            
        return self.evaluate_conditions(self.conditions, document)
        
    def get_next_steps_based_on_conditions(self, workflow_definition, document):
        """
        Get next steps based on conditions and transitions
        """
        # Get transitions from this step
        transitions = frappe.get_all("Workflow Transition", {
            "workflow_definition": workflow_definition,
            "from_step": self.name
        })
        
        next_steps = []
        for transition in transitions:
            # Check if transition conditions are met
            transition_conditions_met = True
            
            if transition.transition_condition:
                # Get transition condition document
                transition_doc = frappe.get_doc("Workflow Transition", transition.name)
                transition_conditions_met = self.evaluate_conditions(transition_doc.transition_condition, document)
            
            if transition_conditions_met:
                to_step = frappe.get_doc("Workflow Step", transition.to_step)
                if to_step:
                    next_steps.append(to_step)
        
        # If no transitions defined or conditions not met, get next step by order
        if not next_steps:
            next_step = frappe.get_all("Workflow Step", {
                "parent": workflow_definition,
                "parenttype": "Workflow Definition",
                "step_order": self.step_order + 1
            })
            
            if next_step:
                next_steps.append(frappe.get_doc("Workflow Step", next_step[0].name))
                
        return next_steps