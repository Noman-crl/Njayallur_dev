import frappe
from datetime import datetime, date
from frappe.utils import flt, get_url
@frappe.whitelist()
def so_list(filter=None):
    """
    - Listing of Sales Order.
    - Filters: name, customer, from_date,  to_date, delivery_date
    """
    try:
        so_filter = {}
        if filter:
            if filter.get("customer"):
                so_filter["customer"] = filter.get("customer")
            if filter.get("name"):
                so_filter["name"] = filter.get("name")
            if filter.get("from_date"):
                so_filter["delivery_date"] = datetime.strptime(filter.get("from_date"), '%d-%m-%Y')
            if filter.get("to_date"):
                if filter.get("from_date"):
                    so_filter["delivery_date"] = ('between', [datetime.strptime(filter.get("from_date"), '%d-%m-%Y'), datetime.strptime(filter.get("to_date"), '%d-%m-%Y')])
                else:
                    so_filter["delivery_date"] = filter.get("to_date")
        so_list = frappe.db.get_list("Sales Order", so_filter, ["name", "customer", "grand_total", "currency", "delivery_date", "status", "docstatus"], order_by="modified desc", ignore_permissions=True)
        frappe.local.response["status_code"] = 200
        frappe.local.response["message"] = "Success"
        frappe.local.response["data"] = so_list
    except Exception as e:
        frappe.local.response["status_code"] = 500
        frappe.local.response["exception"] = str(e)
        frappe.local.response["message"] ="Something went wrong"

@frappe.whitelist()
def so_details(sales_order):
    """
    - Returns details of a Sales Order
    - sales_order_name: Name of sales order(Mandatory)
    """
    try:
        if not sales_order:
            raise Exception("Sales Order not found")
        sales_order = frappe.get_doc('Sales Order', sales_order)

        sales_order_data = {
            'naming_series': sales_order.naming_series,
            'name': sales_order.name,
            'delivery_date':sales_order.delivery_date.strftime("%d-%m-%Y"),
            'customer': sales_order.customer,
            'customer_name': sales_order.customer_name,
            'order_type': sales_order.order_type,
            'company': sales_order.company,
            'transaction_date': sales_order.transaction_date.strftime("%d-%m-%Y"),
            'status': sales_order.status,
            'currency': sales_order.currency,
            'conversion_rate': sales_order.conversion_rate,
            'selling_price_list': sales_order.selling_price_list,
            'price_list_currency': sales_order.price_list_currency,
            'plc_conversion_rate': sales_order.plc_conversion_rate,
            'grand_total':sales_order.grand_total,
            'docstatus': sales_order.docstatus,
            'pdf': get_url("/api/method/frappe.utils.print_format.download_pdf?doctype=Sales%20Order&name={0}&format=Standard&no_letterhead=1&letterhead=No Letterhead&settings=%7B%7D&_lang=en-US"
                .format(sales_order.name)),
            'items': frappe.db.get_list(
                "Sales Order Item",
                {"parent":sales_order.name},
                ['item_code', 'item_name', 'item_group', 'stock_uom', 'stock_uom', 'qty', 'rate', 'amount', "DATE_FORMAT(delivery_date, '%d-%m-%x') as delivery_date", "warehouse"],
                order_by="IDX asc",
                ignore_permissions=True
            )
        }

        frappe.local.response["status_code"] =200
        frappe.local.response["message"] ="Success"
        frappe.local.response["data"]=sales_order_data
    except Exception as e:
        frappe.local.response["status_code"] = 500
        frappe.local.response["exception"] = str(e)
        frappe.local.response["message"] ="Something went wrong"

@frappe.whitelist()
def make_so(data):
    """
    - Keys: customer, delivery_date, order_type, selling_price_list, coupon_code, 
            discount_amount, additional_discount_percentage, items: item_code, qty, 
            delivery_date.
    """
    try:
        if not data.get("customer") or not data.get("items") or not data.get("delivery_date"):
            raise Exception("Customer, delivery Date and Item Details are mandatory.")
        so = frappe.new_doc("Sales Order")
        so.flags.ignore_permissions = True
        so.customer = data.get("customer")
        so.delivery_date = datetime.strptime(data.get("delivery_date"), '%d-%m-%Y') if data.get("delivery_date") else ""
        so.order_type = "Sales"
        so.selling_price_list = get_customer_price_list(data.get("customer"))
        so.coupon_code = data.get("coupon_code") or ""
        so.discount_amount = data.get("discount_amount") or ""
        so.additional_discount_percentage = data.get("additional_discount_percentage") or ""
        so.set_warehouse = data.get("warehouse")
        for item in data.get("items"):
            so.append("items", {
                "item_code": item.get("item_code"),
                "qty": item.get("qty") if item.get("qty") != None else 1,
                "delivery_date": datetime.strptime(item.get("delivery_date"), '%d-%m-%Y') if item.get("delivery_date") else datetime.strptime(data.get("delivery_date"), '%d-%m-%Y'),
                "warehouse": item.get("warehouse") if item.get("warehouse") else data.get("warehouse"),
                "discount_percentage": item.get("discount_percentage") if item.get("discount_percentage") else 0,
            })
        so.set_missing_values()
        so.calculate_taxes_and_totals()
        so.insert()
        frappe.local.response["status_code"] =200
        frappe.local.response["order"] = so.name
        frappe.local.response["net_total"] = so.net_total
        frappe.local.response["grand_total"] = so.rounded_total or so.grand_total
        frappe.local.response["pdf"] = get_url("/api/method/frappe.utils.print_format.download_pdf?doctype=Sales%20Order&name={0}&format=Standard&no_letterhead=1&letterhead=No Letterhead&settings=%7B%7D&_lang=en-US".format(so.name))
        frappe.local.response["message"] = "Placed order successfully."
    except Exception as e:
        frappe.local.response["status_code"] = 500
        frappe.local.response["message"] = "Something went wrong"
        frappe.local.response["exception"] = str(e)

@frappe.whitelist()
def update_so(data):
    """
    - Keys: so_name, customer, delivery_date, coupon_code, discount_amount, 
        additional_discount_percentage, items: item_code, qty, delivery_date.
    - If qty is zero remove item.
    - If no item reamins delete doc.
    """
    try:
        so_name = data.get("name")
        if not frappe.db.exists("Sales Order", {"name":so_name}):
            raise Exception("Sales Order not found")
        doc = frappe.get_doc("Sales Order", so_name)
        if doc.docstatus != 0:
            raise Exception("Cannot edit Submitted/Cancelled documnent")
        so_items = frappe.db.get_list("Sales Order Item", {"parent":so_name}, ["item_code"], pluck="item_code", ignore_permissions=True)
        if data.get("customer"):
            doc.customer = data.get("customer")
        if data.get("delivery_date"):
            doc.delivery_date = datetime.strptime(data.get("delivery_date"), '%d-%m-%Y')
        if data.get("coupon_code"):
            doc.coupon_code = data.get("coupon_code")
        if data.get("discount_amount"):
            doc.discount_amount = data.get("discount_amount")
        if data.get("additional_discount_percentage"):
            doc.additional_discount_percentage = data.get("additional_discount_percentage") or ""
        if data.get("warehouse"):
            doc.set_warehouse = data.get("warehouse")
        if data.get("items"):
            for item in data.get("items"):
                if item.get("item_code") and item.get("item_code") not in so_items:
                    dd = (datetime.strptime(item.get("delivery_date"), '%d-%m-%Y') if item.get("delivery_date") else doc.delivery_date)
                    doc.append("items", {
                        "item_code":item.get("item_code"),
                        "qty":item.get("qty"),
                        "delivery_date":date(dd.year, dd.month, dd.day)
                    })
                else:
                    for doc_item in doc.items:
                        if doc_item.item_code == item.get("item_code") and item.get("qty") != 0:
                            if item.get("qty"):
                                doc_item.qty = item.get("qty")
                            if item.get("delivery_date"):
                                dd = datetime.strptime(item.get("delivery_date"), '%d-%m-%Y')

                                doc_item.delivery_date = date(dd.year, dd.month, dd.day)
                        if doc_item.item_code == item.get("item_code") and item.get("qty") == 0:
                            doc.items.remove(doc_item)
        if len(doc.items) == 0:
            doc.delete()
        else:
            doc.save(ignore_permissions=True)
        frappe.local.response["status_code"] =200
        frappe.local.response["message"] ="Success"
        frappe.local.response["sales_order"]=doc.name
    except Exception as e:
            frappe.local.response["status_code"] = 500
            frappe.local.response["exception"] = str(e)

def get_customer_price_list(customer):
    """
    - Returns price list of a customer.
    - Will consider default price list from customer document else from customer group document.
    - Return "Standard Selling" if both none.
    """
    price_list = ""
    cus_doc= frappe.get_doc("Customer", customer, ["default_price_list"])
    cgpl = frappe.db.get_value("Customer Group", cus_doc.customer_group, ["default_price_list"])
    price_list = cus_doc.default_price_list if cus_doc.default_price_list else cgpl
    if not price_list:
        return "Standard Selling"
    else:
        return price_list
