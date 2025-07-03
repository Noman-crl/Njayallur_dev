import frappe

@frappe.whitelist(allow_guest=True)
def get_items(**kwargs):
    try:
        spl = "Standard Selling"
        pos_profile = kwargs.get("pos_profile")
        if pos_profile:
            spl = frappe.db.get_value("POS Profile", pos_profile, "selling_price_list") or "Standard Selling"
        # pl_settings = frappe.db.get_single_value("DE Restaurant Settings", "products_page_length")
        start = kwargs.get("start") or 0
        page_length = kwargs.get("page_length") or 10
        item_code = kwargs.get("item_code") or None
        item_name = kwargs.get("item_name") or None
        item_group = kwargs.get("item_group") or None
        search_term = kwargs.get("search_term") or None
        filters = ""
        if search_term:
            item_code = search_item(search_term)
            if not item_code:
                raise Exception("No item found")
        if item_code and type(item_code) == str:
            filters += "and item.item_code = '{0}'".format(item_code)
        if item_code and type(item_code) == tuple:
            filters += "and item.item_code in {0}".format(item_code)
        if item_name:
            filters += "and item.item_name = {0}".format(item_name)
        if item_group:
            filters += "and item.item_group = '{0}'".format(item_group)
        filters += "and item_price.price_list = '{0}'".format(spl)
        items = frappe.db.sql("""
            SELECT 
                item.item_name,
                item.item_code,
                item.description,
                item.item_group,
                item.stock_uom,
                item.image,
                item_price.price_list,
                item_price.currency,
                item_price.price_list_rate as rate,
                barcode.barcode,
                barcode_type
            FROM
                `tabItem` item
            LEFT JOIN
                `tabItem Price` item_price
            ON
                item_price.item_code = item.item_code
            LEFT JOIN
                `tabItem Barcode` barcode
            ON
                barcode.parent = item.item_code
            WHERE
                item.disabled = False
                {filters}
            LIMIT
                {start}, {page_length}
        """.format(
            filters = filters,
            start = start,
            page_length = page_length
        ), 
        as_dict=True)
        frappe.local.response["status_code"] = 200
        frappe.local.response["message"] = "Success"
        frappe.local.response["items"] = items or "No items found"
    except Exception as e:
        frappe.local.response["status_code"] = 500
        frappe.local.response["message"] = "Something went wrong. Couldn't get menu."
        frappe.local.response["exception"] = str(e)

@frappe.whitelist(allow_guest=True)
def search_item(query):
    try:
        if not query:
            return None
        data = []
        if query:
            with_item_code = frappe.db.get_list("Item", {"item_code": ("like","%"+query+"%"), "disabled":False}, pluck="name", ignore_permissions=True)
            if with_item_code: 
                data.extend(with_item_code)

            with_item_name = frappe.db.get_list("Item", {"item_name": ("like","%"+query+"%"), "disabled":False}, pluck="name", ignore_permissions=True)
            if with_item_name: 
                data.extend(with_item_name)

            with_item_group = frappe.db.get_list("Item", {"item_group": ("like","%"+query+"%"), "disabled":False}, pluck="name", ignore_permissions=True)
            if with_item_group: 
                data.extend(with_item_group)
        
        if data:
            if len(data) > 1:
                return tuple(data)
            return data[0]
        else:
            return None

    except Exception as e:
        frappe.local.response["status_code"] = 500
        frappe.local.response["exception"] = str(e)