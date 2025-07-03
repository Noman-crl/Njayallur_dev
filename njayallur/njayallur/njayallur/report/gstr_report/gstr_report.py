import frappe
from frappe.utils import getdate, flt


def execute(filters=None):
   columns = get_columns()
   data = get_data(filters)
   for row in data:
       row.update(get_basic_invoice_detail(row))
   return columns, data


def get_columns():
  
   return [
       {"label": "GSTIN/UIN of Recipient", "fieldname": "billing_address_gstin", "fieldtype": "Data", "width": 150},
       {"label": "Receiver Name", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 150},
       {"label": "Invoice Number", "fieldname": "invoice_number", "fieldtype": "Link", "options": "Sales Invoice", "width": 100}, 
       {"label": "Invoice Date", "fieldname": "posting_date", "fieldtype": "Date", "width": 120},
       {"label": "Invoice Value", "fieldname": "grand_total", "fieldtype": "Currency", "width": 120},
       {"label": "Place of Supply", "fieldname": "place_of_supply", "fieldtype": "Data", "width": 120},
       {"label": "Reverse Charge", "fieldname": "reverse_charge", "fieldtype": "Data", "width": 100},
       {"label": "Tax Rate", "fieldname": "tax_rate", "fieldtype": "Data", "width": 100},
       {"label": "Taxable Value", "fieldname": "invoice_value", "fieldtype": "Currency", "width": 120},
       {"label": "Item Tax Template", "fieldname": "item_tax_template", "fieldtype": "Data", "width": 150}
   ]



def get_data(filters):
  
   conditions = []
  
   if filters.get("from_date"):
       conditions.append(f"si.posting_date >= '{filters['from_date']}'")
   if filters.get("to_date"):
       conditions.append(f"si.posting_date <= '{filters['to_date']}'")
   if filters.get("customer_type"):
       if filters["customer_type"] == "B2B":
           conditions.append("si.name LIKE 'B2B%'")
       elif filters["customer_type"] == "B2C":
           conditions.append("si.name LIKE 'B2C%'")
   if filters.get("tax_rate"):
       conditions.append(f"ROUND(CASE \
           WHEN sii.item_tax_template = 'In State GST 12%' THEN 12 \
           WHEN sii.item_tax_template = 'In State GST 0%' THEN 0 \
           WHEN sii.item_tax_template = 'In State GST 18%' THEN 18 \
           WHEN sii.item_tax_template = 'In State GST 5%' THEN 5 \
           WHEN sii.item_tax_template = 'Out State GST 0%' THEN 0 \
           WHEN sii.item_tax_template = 'Out State GST 5%' THEN 5 \
           WHEN sii.item_tax_template = 'Out State GST 12%' THEN 12 \
           WHEN sii.item_tax_template = 'Out State GST 18%' THEN 18 \
           ELSE NULL END, 2) = {flt(filters['tax_rate'].strip('%'))}")
   if filters.get("invoice_number"):
       conditions.append(f"si.name = '{filters['invoice_number']}'")


   conditions_query = " AND ".join(conditions)
   if conditions_query:
       conditions_query = " AND " + conditions_query


   query = f"""
       SELECT
           si.name as invoice_number,
           si.customer,
           si.posting_date,
           si.billing_address_gstin,
           si.place_of_supply,
           sii.item_tax_template,
           ROUND(SUM(sii.net_amount), 2) as invoice_value,
           ROUND(si.grand_total) as grand_total,
           CASE
               WHEN sii.item_tax_template = 'In State GST 12%' THEN 12
               WHEN sii.item_tax_template = 'In State GST 0%' THEN 0
               WHEN sii.item_tax_template = 'In State GST 18%' THEN 18
               WHEN sii.item_tax_template = 'In State GST 5%' THEN 5
               WHEN sii.item_tax_template = 'Out State GST 0%' THEN 0
               WHEN sii.item_tax_template = 'Out State GST 5%' THEN 5
               WHEN sii.item_tax_template = 'Out State GST 12%' THEN 12
               WHEN sii.item_tax_template = 'Out State GST 18%' THEN 18
               ELSE NULL
           END AS tax_rate,
           CASE
               WHEN si.is_reverse_charge = 1 THEN 'Y'
               ELSE 'N'
           END AS reverse_charge
       FROM
           `tabSales Invoice` si
       LEFT JOIN
           `tabSales Invoice Item` sii
       ON
           si.name = sii.parent
       WHERE
           sii.item_tax_template IN ('In State GST 12%', 'In State GST 0%', 'In State GST 18%', 'In State GST 5%',
                                    'Out State GST 0%', 'Out State GST 5%', 'Out State GST 12%',
                                    'Out State GST 18%')
           AND si.docstatus != 2
           {conditions_query}
       GROUP BY
           si.name, tax_rate
   """
   data = frappe.db.sql(query, as_dict=True)
   return data



def get_basic_invoice_detail(row):
   return {
       "inum": row["invoice_number"],
       "idt": getdate(row["posting_date"]).strftime("%d-%m-%Y"),
       "val": flt(row["invoice_value"], 2),
       "gtotal": row["grand_total"], 
       "reverse_charge": row["reverse_charge"]
   }
