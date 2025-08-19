# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.model.document import Document

class WorkflowCondition(Document):
	def validate(self):
		"""Validate the workflow condition document"""
		self.validate_mandatory_fields()
		self.validate_duplicate_condition()

	def before_save(self):
		"""Perform operations before saving the document"""
		self.set_defaults()

	def validate_mandatory_fields(self):
		"""Validate that mandatory fields are set"""
		if not self.workflow_definition:
			frappe.throw(_("Workflow Definition is mandatory"))
		if not self.condition_name:
			frappe.throw(_("Condition Name is mandatory"))
		if not self.condition_field:
			frappe.throw(_("Condition Field is mandatory"))
		if not self.condition_operator:
			frappe.throw(_("Condition Operator is mandatory"))

	def validate_duplicate_condition(self):
		"""Validate that there are no duplicate conditions for the same workflow"""
		if self.workflow_definition and self.condition_name:
			existing_condition = frappe.db.exists("Workflow Condition", {
				"workflow_definition": self.workflow_definition,
				"condition_name": self.condition_name,
				"name": ("!=", self.name)
			})
			if existing_condition:
				frappe.throw(_("Another condition with the same name already exists for this workflow definition"))

	def set_defaults(self):
		"""Set default values if not already set"""
		if not self.is_active:
			self.is_active = 1
		if not self.condition_value:
			self.condition_value = ""
		if not self.description:
			self.description = ""