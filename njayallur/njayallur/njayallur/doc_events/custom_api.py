import frappe
from frappe.utils import get_url
from frappe import _
# set the values of cost center and incoming account 
# of sales invoice from customer group

def set_values (doc,method):
    cust_group= frappe.db.get_value('Customer', doc.customer, 'customer_group')
    cost_center, sales_account = frappe.db.get_value('Customer Group', cust_group, ['cost_center', 'sales_account'])
    if cost_center:
        doc.cost_center=cost_center
    # doc.naming_series=naming_series
    
    if sales_account:
        for i in doc.items:
            i.income_account=sales_account
            i.cost_center=cost_center
            
# def set_values (doc,method):
#     cust_group= frappe.db.get_value('Customer', doc.customer, 'customer_group')
#     cost_center, sales_account,naming_series = frappe.db.get_value('Customer Group', cust_group, ['cost_center', 'sales_account','sales_invoice_naming_series'])
#     if cost_center:
#         doc.cost_center=cost_center
#     # doc.naming_series=naming_series
    
#     if sales_account:
#         for i in doc.items:
#             i.income_account=sales_account
#             i.cost_center=cost_center

# set the naming series of sales invoice to the select 
# option of sales invoice naming series field in the 
# Customer Group doctype
# @frappe.whitelist()
# def get_naming_series():
#     return frappe.get_meta('Sales Invoice').get_field("naming_series").options.splitlines()

# @frappe.whitelist()
# def set_naming(doc, method=None):
#     if isinstance(doc, str):
#         doc = frappe.get_doc("Sales Order", doc)
#     if doc.is_new():
#         cust_group = frappe.db.get_value('Customer', doc.customer, 'customer_group')
#         if not cust_group:
#             frappe.throw(_("Customer Group not found for customer: {0}").format(doc.customer))
        
#         naming_series = frappe.db.get_value('Customer Group', cust_group, 'sales_invoice_naming_series')
#         if not naming_series:
#             frappe.throw(_("Sales Invoice Naming Series not found for customer group: {0}").format(cust_group))
#         doc.naming_series = naming_series


# @frappe.whitelist()
# def set_naming_js(cust=None, method=None): 
#     if cust:
#         cust_group = frappe.db.get_value('Customer', cust, 'customer_group')
#         if not cust_group:
#             frappe.throw(_("Customer Group not found for customer: {0}").format(cust))

#         naming_series = frappe.db.get_value('Customer Group', cust_group, 'sales_invoice_naming_series')
#         if not naming_series:
#             frappe.throw(_("Sales Invoice Naming Series not found for customer group: {0}").format(cust_group))
#     return naming_series




@frappe.whitelist()
def print_format_method():
    try:
        print_formats = frappe.get_all('Print Format', filters={'doc_type': 'Sales Invoice', 'disabled': 0}, fields=['name'])
        return [print_format.name for print_format in print_formats]
    except Exception as e:
        frappe.log_error(f"Error fetching enabled print formats: {str(e)}")
        return []

@frappe.whitelist()
def get_print_url(print_format, doc_name):
    url= get_url(f"/printview?doctype=Sales%20Invoice&name={doc_name}&trigger_print=1&format={print_format}&no_letterhead=1&letterhead=No%20Letterhead&settings=%7B%7D&_lang=en-US") 
    return url



@frappe.whitelist()
def get_item_mrp(item_code):
    """Fetch MRP value for a given item_code."""
    if not item_code:
        return {"mrp": 0}
    item = frappe.get_all("Item", filters={"name": item_code}, fields=["mrp"])
    
    if item:
        return {"mrp": item[0].mrp}
    else:
        return {"mrp": 0}