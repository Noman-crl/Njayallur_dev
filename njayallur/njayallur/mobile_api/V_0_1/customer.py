import frappe
import base64
import imghdr
from frappe.utils.file_manager import save_file

@frappe.whitelist()
def create_customer(**kwargs):
    """

    Required kwars: image, full_name, account, mobile_no, customer_group, customer_type, longitude, territory, latitude, company, email
    """
    try:
        if not kwargs.get("image"):
            raise Exception("Image is mandatory")
        if not kwargs.get("full_name"):
            raise Exception("Full name is mandatory")
        if not kwargs.get("mobile_no"):
            raise Exception("Phone Number is mandatory")

        if frappe.db.exists("Customer", {"customer_name":kwargs.get("full_name")}):
            raise Exception("Customer already exists")

        if frappe.db.exists("Customer", {"mobile_no":kwargs.get("mobile_no")}):
            raise Exception("Mobile number already exists")
        customer = frappe.new_doc("Customer")
        customer.customer_name = kwargs.get("full_name")

        img = upload_cus_img(kwargs.get("image"), kwargs.get("full_name"))

        customer.image = img.file_url
        customer.customer_type = kwargs.get("customer_type") or "Individual"
        customer.customer_group = kwargs.get("customer_group") or "All Customer Groups"
        customer.territory = kwargs.get("territory") or "All Territories"
        customer.mobile_no = kwargs.get("mobile_no")
        customer.email_id = kwargs.get("email_id")
        customer.insert(ignore_permissions=True)
        frappe.db.delete("File", img.name)
        frappe.local.response["status_code"] = 200
        frappe.local.response["message"] = "Customer created successfully"
        frappe.local.response["customer"] = customer.name
    except Exception as e:
        frappe.local.response["status_code"] = 500
        frappe.local.response["message"] = "Someting went wrong."
        frappe.local.response["error"] = str(e)

from erpnext.accounts.party import get_dashboard_info

@frappe.whitelist()
def customer_details(customer_id=None, customer_group=None):
    try:
        filters = ""
        if customer_id:
            filters += f"and cus.name = '{customer_id}'"
        if customer_group:
            filters += f"and cus.customer_group = '{customer_group}'"

        data = frappe.db.sql(
            """
            SELECT
                cus.name as customer_id, 
                cus.customer_name, 
                cus.image, 
                cus.customer_group,
                cus.customer_type,
                cus.territory,
                cus.territory,
                cus.mobile_no,
                cus.email_id
            FROM
                `tabCustomer` cus
            WHERE
                cus.disabled = False
                {filters}
            """.format(
                filters=filters
            ),
            as_dict=True
        )

        # Include Annual Billing and Total Unpaid in the response
        if customer_id:
            for entry in data:
                dashboard_info = get_dashboard_info("Customer", entry.customer_id)
                entry["annual_billing"] = dashboard_info[0].get("billing_this_year") if dashboard_info else 0
                entry["total_unpaid"] = dashboard_info[0].get("total_unpaid") if dashboard_info else 0
        frappe.local.response["status_code"] = 200
        frappe.local.response["message"] = data
    except Exception as e:
        frappe.local.response["status_code"] = 500
        frappe.local.response["message"] = "Something went wrong."
        frappe.local.response["error"] = str(e)





def upload_cus_img(image, customer):
    """
        image: Base64 encoded data.
        customer: existing customer name(primary key)
        save_file - inbuilt function to upload file.
    """
    if not "data:image/jpeg;base64," in image:
        raise Exception("Invalid Image")
    data = image.split(',')[1]
    
    dec_data = base64.b64decode(data)
    exten = imghdr.what(None, h=dec_data)
    file = save_file(customer+"."+exten, dec_data, "", "", is_private=0)
    return file

@frappe.whitelist()
def get_customer_groups():
    try:
        cust_grp = frappe.db.get_list("Customer Group", ["name"], pluck='name', ignore_permissions=True)
        frappe.local.response["status_code"] = 200
        frappe.local.response["message"] = cust_grp
    except Exception as e:
        frappe.local.response["status_code"] = 500
        frappe.local.response["message"] = "Someting went wrong."
        frappe.local.response["error"] = str(e)

@frappe.whitelist()
def get_customer_territory():
    try:
        ttry = frappe.db.get_list("Territory", ["name"], pluck='name', ignore_permissions=True)
        frappe.local.response["status_code"] = 200
        frappe.local.response["message"] = ttry
    except Exception as e:
        frappe.local.response["status_code"] = 500
        frappe.local.response["message"] = "Someting went wrong."
        frappe.local.response["error"] = str(e)