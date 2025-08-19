# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.model.document import Document

class WorkflowStepAction(Document):
	def validate(self):
		"""Validate the workflow step action document"""
		self.validate_mandatory_fields()
		self.validate_duplicate_action()

	def before_save(self):
		"""Perform operations before saving the document"""
		self.set_defaults()

	def validate_mandatory_fields(self):
		"""Validate that mandatory fields are set"""
		if not self.workflow_step:
			frappe.throw(_("Workflow Step is mandatory"))
		if not self.action_name:
			frappe.throw(_("Action Name is mandatory"))
		if not self.status:
			frappe.throw(_("Status is mandatory"))

	def validate_duplicate_action(self):
		"""Validate that there are no duplicate actions for the same step"""
		if self.workflow_step and self.action_name:
			existing_action = frappe.db.exists("Workflow Step Action", {
				"workflow_step": self.workflow_step,
				"action_name": self.action_name,
				"name": ("!=", self.name)
			})
			if existing_action:
				frappe.throw(_("Another action with the same name already exists for this workflow step"))

	def set_defaults(self):
		"""Set default values if not already set"""
		if not self.is_active:
			self.is_active = 1
		if not self.allow_comments:
			self.allow_comments = 1
		if not self.allow_attachment:
			self.allow_attachment = 0