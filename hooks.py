app_name = "electronic_office"
app_title = "Electronic Office System"
app_publisher = "Government Agency"
app_description = "Electronic Office System for government agencies"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "info@government.gov"
app_license = "GPL-3.0"
app_version = "0.0.1"

# Includes in <head>
# ------------------
# include_js, include_css, include_less, include_scss

# include_js = ["electronic_office.bundle.js"]
# include_css = ["electronic_office.bundle.css"]

# Home Pages
# ----------
home_page = "workflow_dashboard"

# Website User Roles
# ------------------
# website_user_roles = []

# Website Route Rules
# -------------------
# website_route_rules = [
# 	{"from_route": "/from", "to_route": "/to", "role": "System Manager"}
# ]

# DocType Permissions
# -------------------
permissions = [
	{"doctype": "Document", "role": "System Manager", "permlevel": 0},
	{"doctype": "Document", "role": "Document Manager", "permlevel": 0},
	{"doctype": "Workflow Definition", "role": "System Manager", "permlevel": 0},
	{"doctype": "Workflow Definition", "role": "Workflow Manager", "permlevel": 0},
	{"doctype": "Digital Signature", "role": "System Manager", "permlevel": 0},
	{"doctype": "Digital Signature", "role": "Digital Signature Authority", "permlevel": 0}
]

# Installation
# ------------
before_install = "electronic_office.install.before_install"
after_install = "electronic_office.install.after_install"

# Uninstallation
# --------------
before_uninstall = "electronic_office.uninstall.before_uninstall"
after_uninstall = "electronic_office.uninstall.after_uninstall"

# Desk Notifications
# ------------------
# desk_notifications = {
# 	"all": ["electronic_office.notifications.get_notifications"],
# 	"for_doctype": {
# 		"ToDo": "electronic_office.notifications.get_todo_notifications"
# 	}
# }

# Email Notifications
# -------------------
# email_notifications = {
# 	"all": ["electronic_office.email.notifications.get_notifications"],
# 	"for_doctype": {
# 		"ToDo": "electronic_office.email.notifications.get_todo_notifications"
# 	}
# }

# Document Events
# ---------------
doc_events = {
	"Document": {
		"on_update": "electronic_office.document.events.on_update",
		"on_submit": "electronic_office.document.events.on_submit",
		"on_cancel": "electronic_office.document.events.on_cancel"
	},
	"Workflow Instance": {
		"on_update": "electronic_office.workflow.events.on_update",
		"on_submit": "electronic_office.workflow.events.on_submit",
		"on_cancel": "electronic_office.workflow.events.on_cancel"
	}
}

# Scheduled Tasks
# ---------------
# scheduler_events = {
# 	"all": [
# 		"electronic_office.tasks.all"
# 	],
# 	"daily": [
# 		"electronic_office.tasks.daily"
# 	],
# 	"hourly": [
# 		"electronic_office.tasks.hourly"
# 	],
# 	"weekly": [
# 		"electronic_office.tasks.weekly"
# 	],
# 	"monthly": [
# 		"electronic_office.tasks.monthly"
# 	]
# }

# Testing
# -------
# before_tests = "electronic_office.install.before_tests"
# after_tests = "electronic_office.install.after_tests"

# Integration Requests
# -------------------
# integration_request_service_map = {
# 	"Service 1": "electronic_office.integrations.service_1",
# 	"Service 2": "electronic_office.integrations.service_2"
# }

# Standard Portal Items
# ---------------------
# standard_portal_items = ["electronic_office.portal.items"]

# Portal Menu Items
# -----------------
# portal_menu_items = [
# 	{
# 		"title": "Support",
# 		"route": "/support",
# 		"reference_doctype": "Issue",
# 		"role": "Customer"
# 	}
# ]

# Point of Sale
# -------------
# pos_bundles = ["electronic_office.pos.bundle"]

# Prerequisites
# -------------
# prerequisites = ["some_other_app"]