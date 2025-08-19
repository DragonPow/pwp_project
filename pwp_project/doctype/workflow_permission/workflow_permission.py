# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.model.document import Document

class WorkflowPermission(Document):
	def validate(self):
		"""Validate the workflow permission document"""
		self.validate_mandatory_fields()
		self.validate_duplicate_permission()

	def before_save(self):
		"""Perform operations before saving the document"""
		self.set_defaults()

	def validate_mandatory_fields(self):
		"""Validate that mandatory fields are set"""
		if not self.workflow_definition:
			frappe.throw(_("Workflow Definition is mandatory"))
		if not self.workflow_step:
			frappe.throw(_("Workflow Step is mandatory"))
		if not self.role:
			frappe.throw(_("Role is mandatory"))
		if not self.permlevel:
			frappe.throw(_("Permission Level is mandatory"))

	def validate_duplicate_permission(self):
		"""Validate that there are no duplicate permissions for the same workflow step and role"""
		if self.workflow_definition and self.workflow_step and self.role and self.permlevel:
			existing_permission = frappe.db.exists("Workflow Permission", {
				"workflow_definition": self.workflow_definition,
				"workflow_step": self.workflow_step,
				"role": self.role,
				"permlevel": self.permlevel,
				"name": ("!=", self.name)
			})
			if existing_permission:
				frappe.throw(_("Another permission with the same role and permission level already exists for this workflow step"))

	def set_defaults(self):
		"""Set default values if not already set"""
		if not self.is_active:
			self.is_active = 1
		if not self.read:
			self.read = 1
		if not self.write:
			self.write = 0
		if not self.create:
			self.create = 0
		if not self.delete:
			self.delete = 0
		if not self.submit:
			self.submit = 0
		if not self.cancel:
			self.cancel = 0
		if not self.amend:
			self.amend = 0