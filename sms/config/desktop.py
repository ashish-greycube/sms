# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"module_name": "Sms",
			"color": "red",
			"icon": "fa fa-bell",
			"type": "module",
			"label": _("SMS")
		}
	]
