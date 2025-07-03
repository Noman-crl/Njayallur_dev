import frappe
from datetime import datetime
from frappe.model.mapper import get_mapped_doc

@frappe.whitelist()
def dn_list(filter=None):
    try:
        dn_filter = {}
        if filter:
            if filter.get("customer"):
                dn_filter["customer"] = filter.get("customer")
            if filter.get("name"):
                dn_filter["name"] = filter.get("name")
            if filter.get("from_date"):
                dn_filter["posting_date"] = datetime.strptime(filter.get("from_date"), '%d-%m-%Y')
            if filter.get("to_date"):
                if filter.get("from_date"):
                    dn_filter["posting_date"] = ('between', [datetime.strptime(filter.get("from_date"), '%d-%m-%Y'), datetime.strptime(filter.get("to_date"), '%d-%m-%Y')])
                else:
                    dn_filter["posting_date"] = filter.get("to_date")
        dn_list = frappe.db.get_list("Delivery Note", dn_filter, ["name", "customer", "grand_total", "currency", "posting_date", "status", "docstatus"], order_by="modified desc", ignore_permissions=True)
        frappe.local.response["status_code"] = 200
        frappe.local.response["message"] = "Success"
        frappe.local.response["data"] = dn_list
    except Exception as e:
        frappe.local.response["status_code"] = 500
        frappe.local.response["exception"] = e
        frappe.local.response["message"] ="Something went wrong"

@frappe.whitelist()
def dn_details(delivery_note_name):
    """
    - Returns details of a Delivery Note
    - devlivery_note_name: Name of sales order(Mandatory)
    """
    try:
        if not frappe.db.exists("Delivery Note", delivery_note_name):
            raise Exception("Delivry Note not found")
        doc = frappe.get_doc("Delivery Note", delivery_note_name)
        delivery_note_data = {
            'naming_series': doc.naming_series,
            'name': doc.name,
            'posting_date':doc.posting_date.strftime("%d-%m-%Y"),
            'customer': doc.customer,
            'customer_name': doc.customer_name,
            'currency': doc.currency,
            'company': doc.company,
            'selling_price_list': doc.selling_price_list,
            'status': doc.status,
            'grand_total':doc.grand_total,
            'docstatus': doc.docstatus,
            'items': frappe.db.get_list(
                "Delivery Note Item",
                {"parent":doc.name},
                ['item_code', 'item_name', 'item_group', 'stock_uom', 'stock_uom', 'qty', 'rate', 'amount']
            )
        }
        frappe.local.response["status_code"] = 200
        frappe.local.response["message"] = "Success"
        frappe.local.response["data"] = delivery_note_data

    except Exception as e:
        frappe.local.response["status_code"] = 500
        frappe.local.response["exception"] = str(e)
        frappe.local.response["message"] = "Something went wrong"

@frappe.whitelist()
def create_dn(data):
    try:
        if not data.get("customer") or not data.get("items"):
            raise Exception("Customer and Item Details are mandatory.")
        dn = frappe.new_doc("Delivery Note")
        dn.flags.ignore_permissions = True
        dn.customer = data.get("customer")
        for item in data.get("items"):
            dn.append("items", {
                "item_code": item.get("item_code"),
                "qty": item.get("qty") if item.get("qty") != None else 1,
            })
        dn.coupon_code = data.get("coupon_code") or ""
        dn.discount_amount = data.get("discount_amount") or ""
        dn.additional_discount_percentage = data.get("additional_discount_percentage") or ""
        dn.set_missing_values()
        dn.calculate_taxes_and_totals()
        dn.insert()

        frappe.local.response["status_code"] =200
        frappe.local.response["order"] = dn.name
        frappe.local.response["message"] = "Delivery Note created successfully."
    except Exception as e:
        frappe.local.response["status_code"] = 500
        frappe.local.response["message"] = "Something went wrong"
        frappe.local.response["exception"] = str(e)


@frappe.whitelist()
def update_dn(data):
    try:
        dn_name = data.get("name")
        if not frappe.db.exists("Delivery Note", {"name":dn_name}):
            raise Exception("Delivery Note not found")
        doc = frappe.get_doc("Delivery Note", dn_name)
        if doc.docstatus != 0:
            raise Exception("Cannot edit Submitted/Cancelled documnent")
        dn_items = frappe.db.get_list("Delivery Note Item", {"parent":dn_name}, ["item_code"], pluck="item_code")
        if data.get("coupon_code"):
            doc.coupon_code = data.get("coupon_code")
        if data.get("discount_amount"):
            doc.discount_amount = data.get("discount_amount")
        if data.get("additional_discount_percentage"):
            doc.additional_discount_percentage = data.get("additional_discount_percentage") or ""
        if data.get("items"):
            for item in data.get("items"):
                if item.get("item_code") != "":
                    if item.get("item_code") not in dn_items:
                        im = frappe.get_doc("Item", item.get("item_code"))
                        doc.append("items", {
                            "item_code":item.get("item_code"),
                            "item_name":im.item_name,
                            "description":data.get("description") or im.description or im.item_name,
                            "stock_uom":im.stock_uom,
                            "uom":im.stock_uom,
                            "conversion_factor":1,
                            "qty":item.get("qty"),
                            'warehouse':item.get("warehouse")
                        })
                    else:
                        for doc_item in doc.items:
                            if doc_item.item_code == item.get("item_code") and item.get("qty") != 0:
                                if item.get("qty"):
                                    doc_item.qty = item.get("qty")
                                if item.get("warehouse"):
                                    doc_item.warehouse = item.get("warehouse")
                                if item.get("description"):
                                    doc_item.description = item.get("description")
                            if doc_item.item_code == item.get("item_code") and item.get("qty") == 0:
                                doc.items.remove(doc_item)
        if len(doc.items) == 0:
            doc.delete()
        else:
            doc.save()
        frappe.local.response["status_code"] =200
        frappe.local.response["message"] ="Success"
        frappe.local.response["delivery_note"]=doc.name
    except Exception as e:
            frappe.local.response["status_code"] = 500
            frappe.local.response["exception"] = str(e)

@frappe.whitelist()
def make_dn_from_so(sales_order_name):
    try:
        delivery_note = None
        target_doc = None
        if not frappe.db.exists("Sales Order", sales_order_name):
            raise Exception("Sales order not found")
        doc = frappe.get_doc("Sales Order", sales_order_name)
        items_without_dn = []
        if doc.docstatus != 1:
            raise Exception("Please submit sales order before creating delivery note")
        for item in doc.items:
            dn_count = frappe.db.count('Delivery Note Item', {'item_code':item.item_code, 'against_sales_order':sales_order_name})
            if dn_count == 0:
                items_without_dn.append(item)


        if items_without_dn:
            delivery_note = frappe.new_doc('Delivery Note')
            delivery_note.customer = doc.customer
            for item_without_dn in items_without_dn :
                delivery_note.append('items',{
                    'item_code' : item_without_dn.item_code,
                    'qty' :item_without_dn.qty,
                    'against_sales_order' : doc.name
                })
            delivery_note.insert(ignore_permissions=True)

        else:
            delivery_note = get_mapped_doc(
                "Sales Order",
                sales_order_name,
                {
                    "Sales Order": {"doctype": "Delivery Note", "validation": {"docstatus": ["=", 1]}},
                    "Sales Order Item": {
                        "doctype": "Delivery Note Item",
                        "field_map": {"parent": "against_sales_order"},
                    },
                },
                target_doc,
    	    )
            delivery_note.insert()
        if delivery_note:
            frappe.local.response["status_code"] =200
            frappe.local.response["message"] ="Delivery Note Created Successfully"
            frappe.local.response["delivery_note"] = delivery_note.name
        else:
            frappe.local.response["status_code"] =400
            frappe.local.response["message"] ="Delivery Note exists againsts all items"

    except Exception as e:
        frappe.local.response["status_code"] = 500
        frappe.local.response["exception"] = str(e)
        frappe.local.response["message"] ="Something went wrong"