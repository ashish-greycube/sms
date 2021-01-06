from __future__ import unicode_literals
from frappe import _
import frappe


def get_data():
	config = [
		{
			"label": _("SMS Communication"),
			"items": [
				{
					"type": "doctype",
					"name": "SMS Notification",
                    "label":"Create SMS Notifications",
					"description": _("SMS Notification.")
				},	
				{
					"type": "doctype",
					"name": "Repeat Notification",
                    "label":"Create Repeat Email-SMS",
					"description": _("Repeat Notification.")
				},				                
				{
					"type": "doctype",
					"name": "SMS Log",
					"route": "#List/SMS Log/List"
				},	
				{
					"type": "doctype",
					"name": "SMS Settings",
					"description": _("Setup SMS gateway settings")
				}                						
			]
		}, 		{
			"label": _("Email Communication"),
			"icon": "fa fa-envelope",
			"items": [
				{
					"type": "doctype",
					"label":"Create Email Notifications",
					"name": "Notification",
					"description": _("Setup Notifications based on various criteria.")
				},
				{
					"type": "doctype",
					"name": "Email Template",
					"description": _("Email Templates for common queries.")
				},
				{
					"type": "doctype",
					"name": "Communication",
					"label":"Open Email Inbox",
				},
				{
					"type": "doctype",
					"name": "Email Queue"
				},								
				{
					"type": "doctype",
					"name": "Email Account",
					"description": _("Add / Manage Email Accounts.")
				},
				{
					"type": "doctype",
					"name": "Email Domain",
					"description": _("Add / Manage Email Domains.")
				},
				{
					"type": "doctype",
					"route": "Form/Notification Settings/{}".format(frappe.session.user),
					"name": "Notification Settings",
					"description": _("Configure notifications for mentions, assignments, energy points and more.")
				},
				{
					"type": "doctype",
					"name": "Error Log",
					"description": _("Log of error on automated events (scheduler).")
				}												
			]
		}
		]
	return config