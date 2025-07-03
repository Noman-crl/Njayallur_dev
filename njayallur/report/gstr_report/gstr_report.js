frappe.query_reports["GSTR Report"] = {
    "filters": [
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today().slice(0, 7) + "-01",
            "reqd": 1
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_days(frappe.datetime.month_end(), 0),
            "reqd": 1
        },
        {
            "fieldname": "customer_type",
            "label": __("Customer Type"),
            "fieldtype": "Select",
            "options": ["", "B2B", "B2C"],
            "default": "",
            "reqd": 0
        },
   
        {
            "fieldname": "invoice_number",
            "label": __("Invoice Number"),
            "fieldtype": "Data",
            "default": "",
            "reqd": 0
        },
        {
            "fieldname": "tax_rate",
            "label": __("Tax Rate"),
            "fieldtype": "Select",
            "options": ["", "0%", "5%", "12%", "18%"],
            "default": "",
            "reqd": 0
        }
    ]
 };
 