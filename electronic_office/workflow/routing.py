import frappe
from frappe import _
from frappe.model.document import Document
import json
from datetime import datetime, timedelta

class WorkflowRouting:
    """
    Workflow routing logic based on document attributes
    """
    
    @staticmethod
    def get_next_step(workflow_instance, current_step, action=None):
        """
        Determine the next step in the workflow based on current step, action, and document attributes
        """
        workflow_def = frappe.get_doc("Workflow Definition", workflow_instance.workflow_definition)
        document = frappe.get_doc("Document", workflow_instance.document)
        
        # Get transitions from the current step
        transitions = frappe.get_all("Workflow Transition", {
            "workflow_definition": workflow_def.name,
            "from_step": current_step.name
        })
        
        # If no transitions defined, use sequential step order
        if not transitions:
            return workflow_def.get_step_by_order(current_step.step_order + 1)
        
        # Evaluate transitions based on conditions
        for transition in transitions:
            transition_doc = frappe.get_doc("Workflow Transition", transition.name)
            
            # Check if transition matches the action (if provided)
            if action and transition_doc.action and transition_doc.action != action:
                continue
            
            # Evaluate transition conditions
            if WorkflowRouting.evaluate_transition_conditions(transition_doc, document):
                return frappe.get_doc("Workflow Step", transition_doc.to_step)
        
        # If no matching transitions found, use sequential step order
        return workflow_def.get_step_by_order(current_step.step_order + 1)
    
    @staticmethod
    def evaluate_transition_conditions(transition, document):
        """
        Evaluate conditions for a transition
        """
        if not transition.conditions:
            return True
        
        # Get conditions for the transition
        conditions = frappe.get_all("Workflow Transition Condition", {
            "parent": transition.name,
            "parenttype": "Workflow Transition"
        })
        
        if not conditions:
            return True
        
        # Evaluate each condition
        all_conditions_met = True
        any_condition_met = False
        
        for condition in conditions:
            condition_doc = frappe.get_doc("Workflow Transition Condition", condition.name)
            condition_met = WorkflowRouting.evaluate_single_condition(condition_doc, document)
            
            if condition_doc.logical_operator == "AND":
                all_conditions_met = all_conditions_met and condition_met
            elif condition_doc.logical_operator == "OR":
                any_condition_met = any_condition_met or condition_met
        
        # If all conditions use AND, return if all are met
        # If any condition uses OR, return if any is met
        if any_condition_met:
            return True
            
        return all_conditions_met
    
    @staticmethod
    def evaluate_single_condition(condition, document):
        """
        Evaluate a single condition
        """
        try:
            # Get the field value from the document
            field_value = document.get(condition.field_name)
            
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
            elif condition.operator == "is_empty":
                return not field_value or str(field_value).strip() == ""
            elif condition.operator == "is_not_empty":
                return field_value and str(field_value).strip() != ""
                
        except Exception as e:
            frappe.log_error(f"Error evaluating condition: {str(e)}", "Workflow Routing Condition Evaluation")
            return False
            
        return False
    
    @staticmethod
    def get_available_actions(workflow_instance, user):
        """
        Get available actions for a user at the current step
        """
        workflow_def = frappe.get_doc("Workflow Definition", workflow_instance.workflow_definition)
        current_step = workflow_def.get_step_by_order(workflow_instance.current_step)
        
        if not current_step:
            return []
        
        # Check if user is assigned to the current step
        if not WorkflowRouting.is_user_assigned_to_step(current_step, user, workflow_instance.document):
            return []
        
        # Get actions for the current step
        actions = frappe.get_all("Workflow Step Action", {
            "parent": current_step.name,
            "parenttype": "Workflow Step"
        })
        
        available_actions = []
        
        for action in actions:
            action_doc = frappe.get_doc("Workflow Step Action", action.name)
            
            # Check if user has permission for this action
            if WorkflowRouting.is_action_allowed(action_doc, user, workflow_instance.document):
                available_actions.append(action_doc)
        
        return available_actions
    
    @staticmethod
    def is_user_assigned_to_step(step, user, document_name):
        """
        Check if a user is assigned to a step
        """
        document = frappe.get_doc("Document", document_name)
        user_roles = frappe.get_roles(user)
        
        if step.assignee_type == "Role" and step.assignee_value in user_roles:
            return True
        elif step.assignee_type == "User" and step.assignee_value == user:
            return True
        elif step.assignee_type == "Field-based":
            field_value = document.get(step.assignee_value)
            return field_value == user
        elif step.assignee_type == "Dynamic":
            return WorkflowRouting.evaluate_dynamic_assignee(step, document, user)
        
        return False
    
    @staticmethod
    def evaluate_dynamic_assignee(step, document, user):
        """
        Evaluate dynamic assignee conditions
        """
        if not step.custom_script:
            return False
        
        try:
            # Create a safe environment for execution
            namespace = {
                "doc": document,
                "frappe": frappe,
                "user": user
            }
            
            # Execute the script
            exec(step.custom_script, namespace)
            
            # Check if the user is in the returned assignees
            if "assignees" in namespace:
                return user in namespace["assignees"]
            
            # Check if there's a custom function to evaluate
            if "is_assignee" in namespace:
                return namespace["is_assignee"](user)
                
        except Exception as e:
            frappe.log_error(f"Error in dynamic assignee script: {str(e)}", "Workflow Routing Dynamic Assignee")
            
        return False
    
    @staticmethod
    def is_action_allowed(action, user, document_name):
        """
        Check if a user is allowed to perform a specific action
        """
        document = frappe.get_doc("Document", document_name)
        user_roles = frappe.get_roles(user)
        
        # Check role permission
        if action.role and action.role not in user_roles and action.role != "All":
            return False
        
        # Check action conditions
        if action.conditions:
            return WorkflowRouting.evaluate_action_conditions(action, document)
        
        return True
    
    @staticmethod
    def evaluate_action_conditions(action, document):
        """
        Evaluate conditions for an action
        """
        # Get conditions for the action
        conditions = frappe.get_all("Workflow Action Condition", {
            "parent": action.name,
            "parenttype": "Workflow Step Action"
        })
        
        if not conditions:
            return True
        
        # Evaluate each condition
        all_conditions_met = True
        any_condition_met = False
        
        for condition in conditions:
            condition_doc = frappe.get_doc("Workflow Action Condition", condition.name)
            condition_met = WorkflowRouting.evaluate_single_condition(condition_doc, document)
            
            if condition_doc.logical_operator == "AND":
                all_conditions_met = all_conditions_met and condition_met
            elif condition_doc.logical_operator == "OR":
                any_condition_met = any_condition_met or condition_met
        
        # If all conditions use AND, return if all are met
        # If any condition uses OR, return if any is met
        if any_condition_met:
            return True
            
        return all_conditions_met
    
    @staticmethod
    def route_document_based_on_attributes(document_name, workflow_definition=None):
        """
        Route a document to the appropriate workflow based on its attributes
        """
        document = frappe.get_doc("Document", document_name)
        
        if not workflow_definition:
            # Get default workflow for document type
            workflow_definition = frappe.db.get_value("Document Type", document.document_type, "workflow")
        
        if not workflow_definition:
            # Find matching workflow based on document attributes
            workflow_definition = WorkflowRouting.find_matching_workflow(document)
        
        if workflow_definition:
            # Start workflow instance
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
        
        return None
    
    @staticmethod
    def find_matching_workflow(document):
        """
        Find a workflow definition that matches the document attributes
        """
        # Get all active workflows for the document type
        workflows = frappe.get_all("Workflow Definition", {
            "document_type": document.document_type,
            "is_active": 1
        })
        
        for workflow in workflows:
            workflow_doc = frappe.get_doc("Workflow Definition", workflow.name)
            
            # Check if workflow conditions match the document
            if WorkflowRouting.evaluate_workflow_conditions(workflow_doc, document):
                return workflow_doc.name
        
        return None
    
    @staticmethod
    def evaluate_workflow_conditions(workflow_def, document):
        """
        Evaluate conditions for a workflow definition
        """
        if not workflow_def.conditions:
            return True
        
        # Evaluate each condition
        all_conditions_met = True
        any_condition_met = False
        
        for condition in workflow_def.conditions:
            condition_met = WorkflowRouting.evaluate_single_condition(condition, document)
            
            if condition.logical_operator == "AND":
                all_conditions_met = all_conditions_met and condition_met
            elif condition.logical_operator == "OR":
                any_condition_met = any_condition_met or condition_met
        
        # If all conditions use AND, return if all are met
        # If any condition uses OR, return if any is met
        if any_condition_met:
            return True
            
        return all_conditions_met
    
    @staticmethod
    def get_workflow_path(workflow_instance):
        """
        Get the complete path of a workflow instance
        """
        workflow_def = frappe.get_doc("Workflow Definition", workflow_instance.workflow_definition)
        
        path = []
        current_step = workflow_def.get_step_by_order(workflow_instance.current_step)
        
        if current_step:
            path.append(current_step)
            
            # Get future steps based on transitions
            while True:
                next_step = WorkflowRouting.get_next_step(workflow_instance, current_step)
                if not next_step:
                    break
                path.append(next_step)
                current_step = next_step
        
        return path
    
    @staticmethod
    def can_skip_step(workflow_instance, user):
        """
        Check if a user can skip the current step
        """
        workflow_def = frappe.get_doc("Workflow Definition", workflow_instance.workflow_definition)
        current_step = workflow_def.get_step_by_order(workflow_instance.current_step)
        
        if not current_step or not current_step.allow_skip:
            return False
        
        # Check if user has permission to skip
        return WorkflowRouting.is_user_assigned_to_step(current_step, user, workflow_instance.document)
    
    @staticmethod
    def skip_step(workflow_instance, user, reason=None):
        """
        Skip the current step and move to the next step
        """
        if not WorkflowRouting.can_skip_step(workflow_instance, user):
            frappe.throw(_("You are not allowed to skip this step"))
        
        workflow_def = frappe.get_doc("Workflow Definition", workflow_instance.workflow_definition)
        current_step = workflow_def.get_step_by_order(workflow_instance.current_step)
        
        # Log the skip action
        WorkflowRouting.log_workflow_action(workflow_instance, "Skip", current_step.step_name, user, reason)
        
        # Move to next step
        next_step = WorkflowRouting.get_next_step(workflow_instance, current_step)
        
        if next_step:
            workflow_instance.current_step = next_step.step_order
            
            if next_step.step_type == "End":
                workflow_instance.status = "Completed"
                workflow_instance.completed_by = user
                workflow_instance.completed_on = datetime.now()
            
            workflow_instance.save()
            
            # Process the next step
            if next_step.step_type != "End":
                workflow_instance.process_step(next_step)
        else:
            # No next step, complete the workflow
            workflow_instance.status = "Completed"
            workflow_instance.completed_by = user
            workflow_instance.completed_on = datetime.now()
            workflow_instance.save()
        
        return workflow_instance.status
    
    @staticmethod
    def log_workflow_action(workflow_instance, action, step_name, user, comment=None):
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