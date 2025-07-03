import frappe
from datetime import datetime

@frappe.whitelist()
def si_list(filter=None):
    """
    - List of submitted Sales Invoices.
    - Filters: name, customer, from_date, to_date
    """
    try:
        si_filter = {"docstatus":1}
        if filter:
            if filter.get("customer"):
                si_filter["customer"] = filter.get("customer")
            if filter.get("name"):
                si_filter["name"] = filter.get("name")
            if filter.get("from_date"):
                si_filter["due_date"] = datetime.strptime(filter.get("from_date"), '%d-%m-%Y')
            if filter.get("to_date"):
                if filter.get("from_date"):
                    si_filter["due_date"] = ('between', [datetime.strptime(filter.get("from_date"), '%d-%m-%Y'), datetime.strptime(filter.get("to_date"), '%d-%m-%Y')])
                else:
                    si_filter["due_date"] = filter.get("to_date")
        si_list = frappe.db.get_list("Sales Invoice", si_filter, ["name", "customer", "grand_total", "currency", "DATE_FORMAT(due_date, '%d-%m-%x') as due_date", "status", "docstatus"], order_by="modified desc", ignore_permissions=True)
        frappe.local.response["status_code"] =200
        frappe.local.response["message"] = "Success"
        frappe.local.response["data"] = si_list
    except Exception as e:
        frappe.local.response["status_code"] = 500
        frappe.local.response["exception"] = str(e)
        frappe.local.response["message"] ="Something went wrong"

@frappe.whitelist()
def sales_invoice_detail(sales_invoice_name):
    try:
        doc = frappe.get_doc("Sales Invoice", sales_invoice_name)
        sales_invoice_data = {
            'naming_series': doc.naming_series,
            'name': doc.name,
            'posting_date':doc.posting_date.strftime("%d-%m-%Y"),
            'due_date':doc.due_date.strftime("%d-%m-%Y"),
            'update_stock':doc.update_stock,
            'customer': doc.customer,
            'customer_name': doc.customer_name,
            'currency': doc.currency,
            'company': doc.company,
            'selling_price_list': doc.selling_price_list,
            'status': doc.status,
            'grand_total': doc.rounded_total or doc.grand_total,
            'docstatus': doc.docstatus,
            'items': frappe.db.get_list(
                "Sales Invoice Item",
                {"parent":doc.name},
                ['item_code', 'item_name', 'item_group', 'uom', 'stock_uom', 'stock_uom', 'qty', 'rate', 'amount'],
                order_by="IDX asc",
                ignore_permissions=True
            )
        }
        frappe.local.response["status_code"] = 200
        frappe.local.response["message"] = "Success"
        frappe.local.response["data"] = sales_invoice_data
    except Exception as e:
        frappe.local.response["status_code"] = 500
        frappe.local.response["exception"] = e
        frappe.local.response["message"] = "Something went wrong"