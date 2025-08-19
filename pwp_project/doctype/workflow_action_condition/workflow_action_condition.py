# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.model.document import Document

class WorkflowActionCondition(Document):
	def validate(self):
		"""Validate the workflow action condition document"""
		self.validate_mandatory_fields()
		self.validate_duplicate_condition()

	def before_save(self):
		"""Perform operations before saving the document"""
		self.set_defaults()

	def validate_mandatory_fields(self):
		"""Validate that mandatory fields are set"""
		if not self.workflow_action:
			frappe.throw(_("Workflow Action is mandatory"))
		if not self.condition_field:
			frappe.throw(_("Condition Field is mandatory"))
		if not self.condition_operator:
			frappe.throw(_("Condition Operator is mandatory"))

	def validate_duplicate_condition(self):
		"""Validate that there are no duplicate conditions for the same action"""
		if self.workflow_action and self.condition_field:
			existing_condition = frappe.db.exists("Workflow Action Condition", {
				"workflow_action": self.workflow_action,
				"condition_field": self.condition_field,
				"name": ("!=", self.name)
			})
			if existing_condition:
				frappe.throw(_("Another condition with the same field already exists for this workflow action"))

	def set_defaults(self):
		"""Set default values if not already set"""
		if not self.is_active:
			self.is_active = 1
		if not self.condition_value:
			self.condition_value = ""