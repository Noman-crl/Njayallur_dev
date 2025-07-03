import frappe

@frappe.whitelist()
def get_discount(customer, item_code):
    discount_amount = 0.0
    sales_orders = frappe.get_all(
        'Sales Order',
        filters={'customer': customer},
        fields=['name', 'transaction_date'],
        order_by='transaction_date DESC',
        limit=1
    )
    if sales_orders:
        sales_order = sales_orders[0]['name']
        discount_amount = frappe.db.get_value(
            'Sales Order Item',
            {'parent': sales_order, 'item_code': item_code},
            'discount_amount'
        )

    return discount_amount

@frappe.whitelist()
def detect_discount(item_code, customer):
    settings = frappe.db.get_value('Njayallur Settings', None, 'allow_previous_discount_in_so')
    if settings == '1':
        detect_orders = frappe.db.sql("""
            SELECT sii.custom_discount_percentage, si.name
            FROM `tabSales Order` si
            JOIN `tabSales Order Item` sii ON si.name = sii.parent
            WHERE sii.item_code = %s AND si.customer = %s
            ORDER BY si.creation DESC
            """, (item_code, customer))
        if detect_orders:
            discount_amount = detect_orders[0][0]
            return discount_amount
        else:
            return 0
