# Copyright (c) 2023, Faircode pvt and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	data = []
	columns = get_columns()
	if not filters.get("from_date") or not filters.get("to_date"):
		frappe.throw("Please set filters")
	data = get_data(filters)
	return columns, data

def get_columns():
	return [
		{
			'label':_("Item Code"),
			'fieldname':'item_code',
			'field_type':'Link',
			'options':"Item",
			"width":300
		},
		{
			'label':_("Total Qty"),
			'fieldname':'total_qty',
			'field_type':'Float',
			"width":300
		},
		{
			'label':_("MRP"),
			'fieldname':'mrp',
			'field_type':'Currency',
			"width":300
		}
	]

def get_data(filters):
	filter = ""
	sii = frappe.db.get_list(
		"Sales Invoice Item", 
		{'docstatus':1, 'sales_order':( '!=', '')}, 
		['sales_order'], 
		pluck='sales_order',
		ignore_permissions=True
	)
	if (sii):
		sii = tuple(sii)
		sii += tuple('0')
		filter += "AND soi.parent NOT IN {sii}".format(sii=sii)
	if filters.get('item_code'):
		filter += "AND soi.item_code = '{item_code}'".format(item_code=filters.get('item_code'))
	query = frappe.db.sql("""
	SELECT
		SUM(soi.qty) as total_qty,
		soi.item_code,
		soi.name,
		soi.mrp,
		soi.rate,
		soi.amount,
		soi.parent
	FROM
		`tabSales Order Item` soi
	INNER JOIN
		`tabSales Order` so
	ON
		soi.parent = so.name
	WHERE
		so.docstatus = 1 AND
		so.transaction_date BETWEEN '{from_date}' AND '{to_date}'
		{filter}
	GROUP BY
		soi.item_code
	""".format(
		from_date = filters.get("from_date"),
		to_date = filters.get("to_date"),
		filter = filter
	), 
	as_dict=True)
	return query