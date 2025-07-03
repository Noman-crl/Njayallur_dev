import frappe
import base64
"""
All APIs related to user managing should be written here.
"""

"""
Login API
Use default login API
End Point: /api/method/login
Args: usr = Username, pwd = Password
"""

@frappe.whitelist( allow_guest=True )
def login(usr, pwd):
	try:
		user_details = frappe.get_doc('User', usr)
	except frappe.exceptions.DoesNotExistError:
		frappe.local.response["status_code"] =404
		frappe.local.response["message"] ="User not Found"
		return
	try:
		login_manager = frappe.auth.LoginManager()
		login_manager.authenticate(user=usr, pwd=pwd)
		login_manager.post_login()
	except frappe.exceptions.AuthenticationError:
		frappe.clear_messages()
		frappe.local.response["status_code"] =401
		frappe.local.response["message"] ="Invalid username/password"
		return

	api_generate = generate_keys(frappe.session.user)
	user = frappe.get_doc('User', frappe.session.user)

	# t = base64.b64encode((user.api_key).api_generate)
	token = base64.b64encode(('{}:{}'.format(user.api_key, api_generate)).encode('utf-8')).decode('utf-8')

	frappe.local.response["status_code"] =200
	frappe.local.response["message"] ="Authentication success"
	frappe.local.response["username"] =user.username
	frappe.local.response["email"] =user.email
	frappe.local.response["mobile_no"] =user.mobile_no
	frappe.local.response["auth_key"] =token
	frappe.local.response["session"] =frappe.session.user

def generate_keys(user):
	user_details = frappe.get_doc('User', user)
	api_secret = frappe.generate_hash(length=15)

	if not user_details.api_key:
		api_key = frappe.generate_hash(length=15)
		user_details.api_key = api_key

	user_details.api_secret = api_secret
	user_details.flags.ignore_permissions = True
	user_details.flags.ignore_password_policy = True
	user_details.save()

	return api_secret

