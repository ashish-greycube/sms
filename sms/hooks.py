# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from . import __version__ as app_version

app_name = "sms"
app_title = "Communication"
app_publisher = "GreyCube Technologies"
app_description = "send sms from any doctype"
app_icon = "fa fa-bell"
app_color = "red"
app_email = "admin@greycube.in"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/sms/css/sms.css"
# app_include_js = "/assets/sms/js/sms.js"

# include js, css files in header of web template
# web_include_css = "/assets/sms/css/sms.css"
# web_include_js = "/assets/sms/js/sms.js"

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Website user home page (by function)
# get_website_user_home_page = "sms.utils.get_home_page"

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "sms.install.before_install"
before_migrate = "sms.install_fixtures.install_fixtures"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "sms.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"*": {
	"on_update": "sms.sms.doctype.sms_notification.sms_notification.trigger_hook_events",
        "after_insert":"sms.sms.doctype.sms_notification.sms_notification.trigger_hook_events",
        "on_submit":"sms.sms.doctype.sms_notification.sms_notification.trigger_hook_events",
        "on_cancel":"sms.sms.doctype.sms_notification.sms_notification.trigger_hook_events"
	},
    "Payment Entry":{
        "on_submit":"sms.sms.doctype.sms_notification.sms_notification.membership_creation_renewal",
    } 
}

# Scheduled Tasks
# ---------------

scheduler_events = {
	"daily": [
        "sms.sms.doctype.sms_notification.sms_notification.trigger_daily_alerts",
        "sms.sms.doctype.sms_notification.sms_notification.birthday_reminders",
	],
"cron": {
        "30 6 1 */3 *": [
            "sms.sms.doctype.sms_notification.sms_notification.trigger_every_3_months_sms",
            "sms.sms.doctype.sms_notification.sms_notification.trigger_every_3_months_email"
        ],
        "30 6 1 */2 *": [
            "sms.sms.doctype.sms_notification.sms_notification.trigger_every_2_months_sms",
            "sms.sms.doctype.sms_notification.sms_notification.trigger_every_2_months_email"
        ],        
        "30 6 1,15 * *": [
            "sms.sms.doctype.sms_notification.sms_notification.trigger_every_15_days_sms",
            "sms.sms.doctype.sms_notification.sms_notification.trigger_every_15_days_email"
        ],
        "30 6 25 * *": [
            "sms.sms.doctype.sms_notification.sms_notification.trigger_25th_of_every_month_sms",
            "sms.sms.doctype.sms_notification.sms_notification.trigger_25th_of_every_month_email"
        ]
    }        
}

# Testing
# -------

# before_tests = "sms.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "sms.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "sms.task.get_dashboard_data"
# }

fixtures = [
      {
        "dt": "SMS Settings", 
        "filters": [["name", "in", ["SMS Settings"]]]
      },
      {
        "dt": "Notification", 
        "filters": [["name", "in", ["Payment Receipt", "Payment Cancellation", "Reminder: Check your Blood Pressure", 
                                    "Update Your Fitness Metrics", "Just Checking In", "Reservation Confirmation",
                                    "Your Reservation has been Cancelled", "birthday_reminder", "Your Reservation has been Modified",
                                    "membership_active", "membership_renewal", "Your Membership has been Suspended", 
                                    "Your Membership is about to Expire.", "Your Spa Booking has been Modified (service)", "Your booking has been Cancelled",
                                    "Welcome letter"
                    ]]]
      }
]