import frappe
from frappe import _
from frappe.utils import cint, cstr, flt

@frappe.whitelist()
def get_item_data(customer, item_code, rate=0, item_tax_template=None):
    discount_amount = 0.0
    discount_percentage = 0.0
    sii = frappe.qb.DocType("Sales Invoice Item")
    si = frappe.qb.DocType("Sales Invoice")
    query = (
        frappe.qb.from_(sii)
        .inner_join(si)
        .on(si.name==sii.parent)
        .select(sii.item_code, sii.custom_discount_percentage)
        .where(si.customer==customer)
        .where(sii.item_code==item_code)
        .orderby(si.posting_date, order=frappe.qb.desc)
        .limit(1)
    )
    dp_item = query.run(as_dict=True)
    if dp_item:
        discount_percentage = dp_item[0].custom_discount_percentage
    sales_invoices = frappe.get_all(
        'Sales Invoice',
        filters={'customer': customer},
        fields=['name', 'posting_date'],
        order_by='posting_date DESC',
        limit=1
    )

    if sales_invoices:
        sales_invoice = sales_invoices[0]['name']
        discount_amount = frappe.db.get_value(
            'Sales Invoice Item',
            {'parent': sales_invoice, 'item_code': item_code},
            'discount_amount'
        )
    itt = None
    if item_tax_template:
        itt = frappe.db.get_all(
            "Item Tax Template Detail", 
            {'parent':item_tax_template},
            ["tax_type", "tax_rate"]
        )
    total_tax = 0
    tax_inc_rate = rate
    if itt:
        for t in itt:
            if "Output" in t.tax_type:
                total_tax += t.tax_rate
        if total_tax:
            tax_inc_rate = ((total_tax/100) * flt(rate)) + flt(rate)
    black_listed = False
    if(frappe.db.exists("Black Listed Item", {'item_code':item_code, 'parent':customer})):
        black_listed = True
    return {"discount_amount": discount_amount, 'discount_percentage': discount_percentage, 'tax_inc_rate':tax_inc_rate, "blacklisted":black_listed}


@frappe.whitelist()
def get_overdue_invoice(customer):
    if frappe.db.exists("Sales Invoice", {"customer":customer, "status":"Overdue"}):
        doc = frappe.get_last_doc("Sales Invoice", {"customer":customer, "status":"Overdue"})
        return {"invoice":doc.name, "outstanding":doc.outstanding_amount}

@frappe.whitelist()
def check_unpaid_invoice(customer):
    unpaid = frappe.db.count("Sales Invoice", {'docstatus':1, 
    'status':('NOT IN', ('Paid', 'Return', 'Submitted', 'Credit Note Issued')),
    'customer':customer})
    return unpaid

@frappe.whitelist()
def detect_discount(item_code, customer):
    detect_invoices = frappe.db.sql("""
        SELECT sii.discount_percentage 
        FROM `tabSales Invoice` si
        JOIN `tabSales Invoice Item` sii ON si.name = sii.parent
        WHERE sii.item_code = %s AND si.customer = %s
        ORDER BY si.posting_date DESC, si.posting_time DESC
        """, (item_code, customer))   
    discount_amount = 0

    if detect_invoices:
        discount_amount = detect_invoices[0][0]
    return int(round(discount_amount)) 
    
def validate_item_tax(doc,method=None):
    for item in doc.items:  
        if not item.item_tax_template:
            item_tax_template = frappe.db.get_value(
                "Item Tax",
                {"parent": item.item_code},  
                "item_tax_template"
            )
            
            if item_tax_template:
                item.item_tax_template = item_tax_template
            else:
                frappe.throw(
                    _("Row {0}: Item Tax Template is missing for item {1}. Please add it in the Item Doctype or manually set it.").format(
                        item.idx, item.item_code
                    )
                )
