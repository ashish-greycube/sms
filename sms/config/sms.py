from __future__ import unicode_literals
from frappe import _
import frappe


def get_data():
	config = [
		{
			"label": _("Communication"),
			"items": [
				{
					"type": "doctype",
					"name": "SMS Notification",
                    "label":"Create SMS Templates",
					"description": _("SMS Notification.")
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
		}		
		]
	return config