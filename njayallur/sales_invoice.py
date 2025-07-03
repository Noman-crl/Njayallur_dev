import frappe

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
