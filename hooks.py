app_name = "pwp_project"
app_title = "PWP Project System"
app_publisher = "Government Agency"
app_description = "PWP Project System for government agencies"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "info@government.gov"
app_license = "GPL-3.0"
app_version = "0.0.1"

# Includes in <head>
# ------------------
# include_js, include_css, include_less, include_scss

# include_js = ["pwp_project.bundle.js"]
# include_css = ["pwp_project.bundle.css"]

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
before_install = "pwp_project.install.before_install"
after_install = "pwp_project.install.after_install"

# Uninstallation
# --------------
before_uninstall = "pwp_project.uninstall.before_uninstall"
after_uninstall = "pwp_project.uninstall.after_uninstall"

# Desk Notifications
# ------------------
# desk_notifications = {
# 	"all": ["pwp_project.notifications.get_notifications"],
# 	"for_doctype": {
# 		"ToDo": "pwp_project.notifications.get_todo_notifications"
# 	}
# }

# Email Notifications
# -------------------
# email_notifications = {
# 	"all": ["pwp_project.email.notifications.get_notifications"],
# 	"for_doctype": {
# 		"ToDo": "pwp_project.email.notifications.get_todo_notifications"
# 	}
# }

# Document Events
# ---------------
doc_events = {
	"Document": {
		"on_update": "pwp_project.document.events.on_update",
		"on_submit": "pwp_project.document.events.on_submit",
		"on_cancel": "pwp_project.document.events.on_cancel"
	},
	"Workflow Instance": {
		"on_update": "pwp_project.workflow.events.on_update",
		"on_submit": "pwp_project.workflow.events.on_submit",
		"on_cancel": "pwp_project.workflow.events.on_cancel"
	}
}

# Scheduled Tasks
# ---------------
# scheduler_events = {
# 	"all": [
# 		"pwp_project.tasks.all"
# 	],
# 	"daily": [
# 		"pwp_project.tasks.daily"
# 	],
# 	"hourly": [
# 		"pwp_project.tasks.hourly"
# 	],
# 	"weekly": [
# 		"pwp_project.tasks.weekly"
# 	],
# 	"monthly": [
# 		"pwp_project.tasks.monthly"
# 	]
# }

# Testing
# -------
# before_tests = "pwp_project.install.before_tests"
# after_tests = "pwp_project.install.after_tests"

# Integration Requests
# -------------------
# integration_request_service_map = {
# 	"Service 1": "pwp_project.integrations.service_1",
# 	"Service 2": "pwp_project.integrations.service_2"
# }

# Standard Portal Items
# ---------------------
# standard_portal_items = ["pwp_project.portal.items"]

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
# pos_bundles = ["pwp_project.pos.bundle"]

# Prerequisites
# -------------
# prerequisites = ["some_other_app"]
