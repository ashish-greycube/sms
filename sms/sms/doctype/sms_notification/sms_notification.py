# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json, os
from frappe import _
from frappe.model.document import Document
from frappe.utils import validate_email_address, nowdate, parse_val, is_html, add_to_date
from frappe.utils.jinja import validate_template
from frappe.utils.safe_exec import get_safe_globals
from frappe.modules.utils import export_module_json, get_doc_module
from six import string_types
from frappe.core.doctype.sms_settings.sms_settings import send_sms

class SMSNotification(Document):
	def onload(self):
		'''load message'''
		if self.is_standard:
			self.message = self.get_template()

	def autoname(self):
		if not self.name:
			self.name = self.subject

	def validate(self):
		validate_template(self.message)

		if self.event in ("Days Before", "Days After") and not self.date_changed:
			frappe.throw(_("Please specify which date field must be checked"))

		if self.event=="Value Change" and not self.value_changed:
			frappe.throw(_("Please specify which value field must be checked"))

		self.validate_forbidden_types()
		self.validate_condition()
		frappe.cache().hdel('sms_notifications', self.document_type)

	def on_update(self):
		path = export_module_json(self, self.is_standard, self.module)
		if path:
			# js
			if not os.path.exists(path + '.md') and not os.path.exists(path + '.html'):
				with open(path + '.md', 'w') as f:
					f.write(self.message)

			# py
			if not os.path.exists(path + '.py'):
				with open(path + '.py', 'w') as f:
					f.write("""from __future__ import unicode_literals

import frappe

def get_context(context):
	# do your magic here
	pass
""")



	def validate_condition(self):
		temp_doc = frappe.new_doc(self.document_type)
		if self.condition:
			try:
				frappe.safe_eval(self.condition, None, get_context(temp_doc.as_dict()))
			except Exception:
				frappe.throw(_("The Condition '{0}' is invalid").format(self.condition))

	def validate_forbidden_types(self):
		forbidden_document_types = ("Email Queue",)
		if (self.document_type in forbidden_document_types
			or frappe.get_meta(self.document_type).istable):
			# currently notifications don't work on child tables as events are not fired for each record of child table

			frappe.throw(_("Cannot set SMS Notification on Document Type {0}").format(self.document_type))

	def get_documents_for_today(self):
		'''get list of documents that will be triggered today'''
		docs = []

		diff_days = self.days_in_advance
		if self.event=="Days After":
			diff_days = -diff_days

		reference_date = add_to_date(nowdate(), days=diff_days)
		reference_date_start = reference_date + ' 00:00:00.000000'
		reference_date_end = reference_date + ' 23:59:59.000000'

		doc_list = frappe.get_all(self.document_type,
			fields='name',
			filters=[
				{ self.date_changed: ('>=', reference_date_start) },
				{ self.date_changed: ('<=', reference_date_end) }
			])

		for d in doc_list:
			doc = frappe.get_doc(self.document_type, d.name)

			if self.condition and not frappe.safe_eval(self.condition, None, get_context(doc)):
				continue

			docs.append(doc)

		return docs

	def send(self, doc):
		'''Build recipients and send SMS Notification'''

		context = get_context(doc)
		context = {"doc": doc, "alert": self, "comments": None}
		if doc.get("_comments"):
			context["comments"] = json.loads(doc.get("_comments"))

		if self.is_standard:
			self.load_standard_properties(context)
		try:

			if self.channel == 'SMS':
				self.send_sms(doc, context)

		except:
			frappe.log_error(title='Failed to send notification', message=frappe.get_traceback())

		if self.set_property_after_alert:
			allow_update = True
			if doc.docstatus == 1 and not doc.meta.get_field(self.set_property_after_alert).allow_on_submit:
				allow_update = False
			try:
				if allow_update and not doc.flags.in_notification_update:
					fieldname = self.set_property_after_alert
					value = self.property_value
					if doc.meta.get_field(fieldname).fieldtype in frappe.model.numeric_fieldtypes:
						value = frappe.utils.cint(value)

					doc.set(fieldname, value)
					doc.flags.updater_reference = {
						'doctype': self.doctype,
						'docname': self.name,
						'label': _('via SMS Notification')
					}
					doc.flags.in_notification_update = True
					doc.save(ignore_permissions=True)
					doc.flags.in_notification_update = False
			except Exception:
				frappe.log_error(title='Document update failed', message=frappe.get_traceback())

	def send_sms(self, doc, context):
		send_sms(
			receiver_list=self.get_receiver_list(doc, context),
			msg=frappe.render_template(self.message, context)
		)


	def get_receiver_list(self, doc, context):
		''' return receiver list based on the doc field and role specified '''
		receiver_list = []
		for recipient in self.recipients:
			if recipient.condition:
				if not frappe.safe_eval(recipient.condition, None, context):
					continue

			# For sending messages to the owner's mobile phone number
			if recipient.receiver_by_document_field == 'owner':
				receiver_list.append(get_user_info(doc.get('owner'), 'mobile_no'))
			# For sending messages to the number specified in the receiver field
			elif recipient.receiver_by_document_field:
				receiver_list.append(doc.get(recipient.receiver_by_document_field))

			#For sending messages to specified role
			if recipient.receiver_by_role:
				receiver_list += get_info_based_on_role(recipient.receiver_by_role, 'mobile_no')

		return receiver_list


	def get_template(self):
		module = get_doc_module(self.module, self.doctype, self.name)
		def load_template(extn):
			template = ''
			template_path = os.path.join(os.path.dirname(module.__file__),
				frappe.scrub(self.name) + extn)
			if os.path.exists(template_path):
				with open(template_path, 'r') as f:
					template = f.read()
			return template

		return load_template('.html') or load_template('.md')

	def load_standard_properties(self, context):
		'''load templates and run get_context'''
		module = get_doc_module(self.module, self.doctype, self.name)
		if module:
			if hasattr(module, 'get_context'):
				out = module.get_context(context)
				if out: context.update(out)

		self.message = self.get_template()

		if not is_html(self.message):
			self.message = frappe.utils.md_to_html(self.message)

@frappe.whitelist()
def get_documents_for_today(notification):
	notification = frappe.get_doc('SMS Notification', notification)
	notification.check_permission('read')
	return [d.name for d in notification.get_documents_for_today()]

def trigger_daily_alerts():
	trigger_notifications(None, "daily")


def trigger_hook_events(self,method):
	# return
	"""Run notifications for this method"""
	if (frappe.flags.in_import and frappe.flags.mute_emails) or frappe.flags.in_patch or frappe.flags.in_install:
		return

	if self.flags.sms_notifications_executed==None:
		self.flags.sms_notifications_executed = []

	# from frappe.email.doctype.notification.notification import evaluate_alert

	if self.flags.sms_notifications == None:
		alerts = frappe.cache().hget('sms_notifications', self.doctype)
		if alerts==None:
			alerts = frappe.get_all('SMS Notification', fields=['name', 'event', 'method'],
				filters={'enabled': 1, 'document_type': self.doctype})
			frappe.cache().hset('sms_notifications', self.doctype, alerts)
		self.flags.sms_notifications = alerts
	if not self.flags.sms_notifications:
		return

	def _evaluate_alert(alert):
		if not alert.name in self.flags.sms_notifications_executed:
			evaluate_alert(self, alert.name, alert.event)
			self.flags.sms_notifications_executed.append(alert.name)

	event_map = {
		"on_update": "Save",
		"after_insert": "New",
		"on_submit": "Submit",
		"on_cancel": "Cancel"
	}

	if not self.flags.in_insert:
		# value change is not applicable in insert
		event_map['on_change'] = 'Value Change'

	for alert in self.flags.sms_notifications:
		event = event_map.get(method, None)
		if event and alert.event == event:
			_evaluate_alert(alert)
		elif alert.event=='Method' and method == alert.method:
			_evaluate_alert(alert)
		elif alert.event=='Value Change' :
			_evaluate_alert(alert)			

def get_documents_for_processing(self):
	'''get list of documents that will be triggered today'''
	docs = []

	diff_days = self.days_in_advance
	if self.event=="Condition Days After":
		diff_days = -diff_days

	reference_date = add_to_date(nowdate(), days=diff_days)
	reference_date_start = reference_date + ' 00:00:00.000000'
	reference_date_end = nowdate() + ' 23:59:59.000000'

	doc_list = frappe.get_all(self.document_type,
		fields='name',
		filters=[
			{ self.date_changed: ('<=', reference_date_start) },
			{ self.date_changed: ('not in', [None,'']) }
		])
	print(doc_list,'doclist',self.document_type,self.date_changed,reference_date_start,reference_date_end)
	for d in doc_list:
		doc = frappe.get_doc(self.document_type, d.name)

		if self.condition and not frappe.safe_eval(self.condition, None, get_context(doc)):
			continue

		docs.append(doc)

	return docs





def trigger_notifications(doc, method=None):
	if frappe.flags.in_import or frappe.flags.in_patch:
		# don't send notifications while syncing or patching
		return

	if method == "daily":
		doc_list = frappe.get_all('SMS Notification',
			filters={
				'event': ('in', ('Days Before', 'Days After')),
				'enabled': 1
			})
		print('daily doc',doc_list)
		for d in doc_list:
			alert = frappe.get_doc("SMS Notification", d.name)

			for doc in alert.get_documents_for_today():
				evaluate_alert(doc, alert, alert.event)
				frappe.db.commit()

def evaluate_alert(doc, alert, event):
	from jinja2 import TemplateError
	try:
		if isinstance(alert, string_types):
			alert = frappe.get_doc("SMS Notification", alert)

		context = get_context(doc)

		if alert.condition:
			if not frappe.safe_eval(alert.condition, None, context):
				return

		if event=="Value Change" and not doc.is_new():
			if not frappe.db.has_column(doc.doctype, alert.value_changed):
				alert.db_set('enabled', 0)
				frappe.log_error('SMS Notification {0} has been disabled due to missing field'.format(alert.name))
				return

			doc_before_save = doc.get_doc_before_save()
			field_value_before_save = doc_before_save.get(alert.value_changed) if doc_before_save else None

			field_value_before_save = parse_val(field_value_before_save)
			if (doc.get(alert.value_changed) == field_value_before_save):
				# value not changed
				return

		if event != "Value Change" and not doc.is_new():
			# reload the doc for the latest values & comments,
			# except for validate type event.
			doc.reload()
		alert.send(doc)
	except TemplateError:
		frappe.throw(_("Error while evaluating SMS Notification {0}. Please fix your template.").format(alert))
	except Exception as e:
		error_log = frappe.log_error(message=frappe.get_traceback(), title=str(e))
		frappe.throw(_("Error in SMS Notification: {}").format(
			frappe.utils.get_link_to_form('Error Log', error_log.name)))

def get_context(doc):
	return {"doc": doc, "nowdate": nowdate, "frappe": frappe._dict(utils=get_safe_globals().get("frappe").get("utils"))}

def get_assignees(doc):
	assignees = []
	assignees = frappe.get_all('ToDo', filters={'status': 'Open', 'reference_name': doc.name,
		'reference_type': doc.doctype}, fields=['owner'])

	recipients = [d.owner for d in assignees]

	return recipients



def get_info_based_on_role(role, field='email'):
	''' Get information of all users that have been assigned this role '''
	users = frappe.get_list("Has Role", filters={"role": role, "parenttype": "User"},
		fields=["parent"])

	return get_user_info(users, field)

def get_user_info(users, field='email'):
	''' Fetch details about users for the specified field '''
	info_list = []
	for user in users:
		user_info, enabled = frappe.db.get_value("User", user.parent, [field, "enabled"])
		if enabled and user_info not in ["admin@example.com", "guest@example.com"]:
			info_list.append(user_info)
	return info_list


	


def trigger_repeat_sms_with_condition(condition):
	if frappe.flags.in_import or frappe.flags.in_patch:
		# don't send notifications while syncing or patching
		return

	doc_list = frappe.get_all('SMS Notification',
		filters={
			'event': 'Condition Days After',
			'interval':condition,
			'enabled': 1
		})
	for d in doc_list:
		alert = frappe.get_doc("SMS Notification", d.name)
		print(d.name,'alert selected')
		for doc in get_documents_for_processing(alert):
			print(doc.name,'doc impacted')
			evaluate_alert(doc, alert, alert.event)
			frappe.db.commit()	

def trigger_repeat_email_with_condition(condition):			
	from frappe.email.doctype.notification.notification import evaluate_alert
	if frappe.flags.in_import or frappe.flags.in_patch:
		# don't send notifications while syncing or patching
		return

	doc_list = frappe.get_all('Notification',
		filters={
			'event': 'Condition Days After',
			'interval':condition,
			'enabled': 1
		})
	for d in doc_list:
		alert = frappe.get_doc("Notification", d.name)
		print(d.name,'alert selected')
		for doc in get_documents_for_processing(alert):
			print(doc.name,'doc impacted')
			evaluate_alert(doc, alert, alert.event)
			frappe.db.commit()	

def trigger_every_3_months_sms():
	trigger_repeat_sms_with_condition(condition='Every 3 months')


def trigger_every_3_months_email():
	trigger_repeat_email_with_condition(condition='Every 3 months')			

def trigger_every_2_months_sms():
	trigger_repeat_sms_with_condition(condition='Every 2 months')


def trigger_every_2_months_email():
	trigger_repeat_email_with_condition(condition='Every 2 months')			

def trigger_every_15_days_sms():
	trigger_repeat_sms_with_condition(condition='Every 15 days')


def trigger_every_15_days_email():
	trigger_repeat_email_with_condition(condition='Every 15 days')		


def trigger_25th_of_every_month_sms():
	trigger_repeat_sms_with_condition(condition='25th of every month')


def trigger_25th_of_every_month_email():
	trigger_repeat_email_with_condition(condition='25th of every month')	


def membership_creation_renewal(self,method):
	for reference in self.get("references"):
		if reference.reference_doctype == 'Sales Invoice':
			sales_invoice=reference.reference_name
			membership_detail= frappe.db.get_list('Membership Invoice CT',filters={'invoice': sales_invoice},fields=['parent'],as_list=False)
			if len(membership_detail)>0:
				membership_name=membership_detail[0].parent	
				membership = frappe.get_doc('Membership CT',membership_name)
				if membership:
					args={
					'membership_plan':membership.membership_plan or '',
					'current_invoice_start':membership.current_invoice_start or '',
					'current_invoice_end':membership.current_invoice_end or '',
					'member_web_login_id':membership.member_web_login_id or '',
					'name':membership.name or ''
					}

					no_of_sales_invoice=len(membership.get("invoices"))
					if no_of_sales_invoice>1:
						#renewal logic
						send_membership_creation_renewal_sms(self,notification_name='membership_renewal',args=args)
						send_membership_creation_renewal_email(self,notification_name='membership_renewal',args=args)
					else:
						#first time, active paid logic
						send_membership_creation_renewal_sms(self,notification_name='membership_active',args=args)
						send_membership_creation_renewal_email(self,notification_name='membership_active',args=args)

def send_membership_creation_renewal_sms(self,notification_name,args=None):
	if frappe.db.exists('SMS Notification',notification_name):	
		alert = frappe.get_doc('SMS Notification',notification_name)
		if alert:
			doc=frappe.get_doc(self.doctype,self.name)
			context = get_context(doc)
			context = {"doc": doc, "alert": alert, "comments": None}
			msg=frappe.render_template(alert.message,context)
			if args !=None:
				msg=frappe.render_template(msg, args)
			print(alert.get_receiver_list(doc, context),len(alert.get_receiver_list(doc, context)))	
			receiver_list=list(filter(None,alert.get_receiver_list(doc, context)))
			if len(receiver_list)>0:
				send_sms(
					receiver_list=receiver_list,
					msg=msg
				)
				print('msg sent',alert.get_receiver_list(doc, context),msg)	

def send_membership_creation_renewal_email(self,notification_name,args):
	if frappe.db.exists('Notification',notification_name):	
		alert = frappe.get_doc('Notification',notification_name)
		if alert:
			doc=frappe.get_doc(self.doctype,self.name)
			context = get_context(doc)
			context = {"doc": doc, "alert": alert, "comments": None}

			from email.utils import formataddr
			subject = alert.subject
			if "{" in subject:
				subject = frappe.render_template(alert.subject, context)

			attachments = alert.get_attachment(doc)
			recipients, cc, bcc = alert.get_list_of_recipients(doc, context)
			if not (recipients or cc or bcc):
				return

			sender = None
			if alert.sender and alert.sender_email:
				sender = formataddr((alert.sender, alert.sender_email))
			msg=frappe.render_template(alert.message,context)
			if args !=None:
				msg=frappe.render_template(msg, args)			
			frappe.sendmail(recipients = recipients,
				subject = subject,
				sender = sender,
				cc = cc,
				bcc = bcc,
				message = msg,
				reference_doctype = doc.doctype,
				reference_name = doc.name,
				attachments = attachments,
				expose_recipients="header",
				print_letterhead = ((attachments
					and attachments[0].get('print_letterhead')) or False))

def birthday_reminders():
	print('-'*100)
	"""Get  whose birthday is today for SMS"""
	todays_date=frappe.utils.today()
	contacts = frappe.db.sql("""
select distinct(contact.name)
from `tabMembership CT` membership
inner join `tabDynamic Link` link
on link.link_name=membership.customer
inner join `tabContact` contact 
on contact.name=link.parent
where 
link.parenttype='Contact' and link.link_doctype='Customer'
and membership.status in ('Active Unpaid','Active Paid','Past Due Date','Suspended')
and contact.mobile_no is not null
and DATE_FORMAT(contact.birth_date_cf,'%%m-%%d') = DATE_FORMAT(%s,'%%m-%%d')
""",(todays_date),as_dict=1)
	if len(contacts)>0:
		for contact in contacts:
			print(contact.name)
			doc=frappe.get_doc('Contact',contact.name)
			send_membership_creation_renewal_sms(doc,notification_name='birthday_reminder',args=None)
			# 
	contacts = frappe.db.sql("""
select distinct(contact.name)
from `tabMembership CT` membership
inner join `tabDynamic Link` link
on link.link_name=membership.customer
inner join `tabContact` contact 
on contact.name=link.parent
where 
link.parenttype='Contact' and link.link_doctype='Customer'
and membership.status in ('Active Unpaid','Active Paid','Past Due Date','Suspended')
and contact.email_id is not null
and DATE_FORMAT(contact.birth_date_cf,'%%m-%%d') = DATE_FORMAT(%s,'%%m-%%d')
""",(todays_date),as_dict=1)
	if len(contacts)>0:
		for contact in contacts:
			print(contact.name)
			doc=frappe.get_doc('Contact',contact.name)
			send_membership_creation_renewal_email(doc,notification_name='birthday_reminder',args=None)		
