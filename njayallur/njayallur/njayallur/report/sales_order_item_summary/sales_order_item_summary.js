// Copyright (c) 2023, Faircode pvt and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Sales Order Item Summary"] = {
	"filters": [
		{
			fieldname:'from_date',
			label:"From Date",
			fieldtype:"Date",
			reqd: 1,
			default: frappe.datetime.get_today(),
			width: "60px"
		},
		{
			fieldname:'to_date',
			label:"To Date",
			fieldtype:"Date",
			reqd: 1,
			default: frappe.datetime.get_today(),
			width: "60px"
		},
		{
			fieldname:'item_code',
			label:"Item Code",
			fieldtype:"Link",
			options:"Item"
		}
	]
};
