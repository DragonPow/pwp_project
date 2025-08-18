# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.model.document import Document

class WorkflowTransition(Document):
	def validate(self):
		"""Validate the workflow transition document"""
		self.validate_mandatory_fields()
		self.validate_duplicate_transition()
		self.validate_circular_transition()

	def before_save(self):
		"""Perform operations before saving the document"""
		self.set_defaults()

	def validate_mandatory_fields(self):
		"""Validate that mandatory fields are set"""
		if not self.workflow_definition:
			frappe.throw(_("Workflow Definition is mandatory"))
		if not self.from_step:
			frappe.throw(_("From Step is mandatory"))
		if not self.to_step:
			frappe.throw(_("To Step is mandatory"))
		if not self.action:
			frappe.throw(_("Action is mandatory"))

	def validate_duplicate_transition(self):
		"""Validate that there are no duplicate transitions for the same workflow"""
		if self.workflow_definition and self.from_step and self.to_step and self.action:
			existing_transition = frappe.db.exists("Workflow Transition", {
				"workflow_definition": self.workflow_definition,
				"from_step": self.from_step,
				"to_step": self.to_step,
				"action": self.action,
				"name": ("!=", self.name)
			})
			if existing_transition:
				frappe.throw(_("Another transition with the same from step, to step, and action already exists for this workflow"))

	def validate_circular_transition(self):
		"""Validate that the transition does not create a circular reference"""
		if self.from_step == self.to_step:
			frappe.throw(_("From Step and To Step cannot be the same"))

	def set_defaults(self):
		"""Set default values if not already set"""
		if not self.is_active:
			self.is_active = 1
		if not self.allow_revert:
			self.allow_revert = 0
		if not self.condition:
			self.condition = ""