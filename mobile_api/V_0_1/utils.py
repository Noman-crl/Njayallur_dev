import json
import frappe
import frappe.defaults
from erpnext.stock.get_item_details import get_item_details
from frappe import _, throw
from frappe.model.meta import get_field_precision
from frappe.utils import add_days, add_months, cint, cstr, flt, getdate
from six import iteritems, string_types
import requests

from erpnext import get_company_currency
from erpnext.accounts.doctype.pricing_rule.pricing_rule import (
	get_pricing_rule_for_item,
	set_transaction_type,
)
from erpnext.setup.doctype.brand.brand import get_brand_defaults
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
from erpnext.setup.utils import get_exchange_rate
from erpnext.stock.doctype.batch.batch import get_batch_no
from erpnext.stock.doctype.item.item import get_item_defaults, get_uom_conv_factor
from erpnext.stock.doctype.item_manufacturer.item_manufacturer import get_item_manufacturer_part_no
from erpnext.stock.doctype.price_list.price_list import get_price_list_details
sales_doctypes = ["Quotation", "Sales Order", "Delivery Note", "Sales Invoice", "POS Invoice"]
purchase_doctypes = [
	"Material Request",
	"Supplier Quotation",
	"Purchase Order",
	"Purchase Receipt",
	"Purchase Invoice",
]

@frappe.whitelist()
def get_warehouse_list(company=None):
    """
    - Returns list of all warehouses not disabled.
    - company = default if arg company is None
    """
    if not company:
        company = frappe.defaults.get_defaults().company
    try:
        warehouse = frappe.db.get_list("Warehouse", {"disabled":False, "company":company}, ["name"], pluck="name")
        frappe.local.response["status_code"] =200
        frappe.local.response["message"] ="Success"
        frappe.local.response["warehouse"]=warehouse

    except Exception as e:
        frappe.local.response["status_code"] = 500
        frappe.local.response["exception"] = e
        frappe.local.response["message"] ="Something went wrong"

@frappe.whitelist()
def submit_doc(doctype, docname):
    """
    - Args: doctype = Doctype Name
            docname = Name of Document
    """
    try:
        if frappe.db.exists(doctype, docname):
            doc = frappe.get_doc(doctype, docname)
            doc.submit()
            frappe.local.response["status_code"] =200
            frappe.local.response["message"] ="Document submitted successfully"
            frappe.local.response["sales_order"]=doc.name
        else:
            raise Exception("document not found")

    except Exception as e:
        frappe.local.response["status_code"] = 500
        frappe.local.response["exception"] = e
        frappe.local.response["message"] ="Something went wrong"

@frappe.whitelist()
def mop_list():
    "Returns mode of payment list"
    try:
        mop_list = frappe.db.get_list("Mode of Payment", ["name"], ignore_permissions=True)
        frappe.local.response["status_code"] =200
        frappe.local.response["order"] = mop_list 
    except Exception as e:
        frappe.local.response["status_code"] = 500
        frappe.local.response["message"] = "Something went wrong"
        frappe.local.response["exception"] = str(e)


@frappe.whitelist()
def get_item_details_new(args, doc=None, for_validate=False, overwrite_warehouse=True):
	args = process_args(args)
	item = frappe.get_cached_doc("Item", args.item_code)
	basic_details = get_basic_details(args, item, overwrite_warehouse=True)
	
	item_details = get_item_details(args, doc=None, for_validate=False, overwrite_warehouse=True)
	item_details["mrp"]=basic_details["mrp"]
	return item_details


def get_basic_details(args, item, overwrite_warehouse=True):
	"""
	:param args: {
	                "item_code": "",
	                "warehouse": None,
	                "customer": "",
	                "conversion_rate": 1.0,
	                "selling_price_list": None,
	                "price_list_currency": None,
	                "price_list_uom_dependant": None,
	                "plc_conversion_rate": 1.0,
	                "doctype": "",
	                "name": "",
	                "supplier": None,
	                "transaction_date": None,
	                "conversion_rate": 1.0,
	                "buying_price_list": None,
	                "is_subcontracted": "Yes" / "No",
	                "ignore_pricing_rule": 0/1
	                "project": "",
	                barcode: "",
	                serial_no: "",
	                currency: "",
	                update_stock: "",
	                price_list: "",
	                company: "",
	                order_type: "",
	                is_pos: "",
	                project: "",
	                qty: "",
	                stock_qty: "",
	                conversion_factor: "",
	                against_blanket_order: 0/1
	        }
	:param item: `item_code` of Item object
	:return: frappe._dict
	"""

	if not item:
		item = frappe.get_doc("Item", args.get("item_code"))

	if item.variant_of:
		item.update_template_tables()

	item_defaults = get_item_defaults(item.name, args.company)
	item_group_defaults = get_item_group_defaults(item.name, args.company)
	brand_defaults = get_brand_defaults(item.name, args.company)

	defaults = frappe._dict(
		{
			"item_defaults": item_defaults,
			"item_group_defaults": item_group_defaults,
			"brand_defaults": brand_defaults,
		}
	)

	warehouse = get_item_warehouse(item, args, overwrite_warehouse, defaults)

	if args.get("doctype") == "Material Request" and not args.get("material_request_type"):
		args["material_request_type"] = frappe.db.get_value(
			"Material Request", args.get("name"), "material_request_type", cache=True
		)

	expense_account = None

	if args.get("doctype") == "Purchase Invoice" and item.is_fixed_asset:
		from erpnext.assets.doctype.asset_category.asset_category import get_asset_category_account

		expense_account = get_asset_category_account(
			fieldname="fixed_asset_account", item=args.item_code, company=args.company
		)

	# Set the UOM to the Default Sales UOM or Default Purchase UOM if configured in the Item Master
	if not args.get("uom"):
		if args.get("doctype") in sales_doctypes:
			args.uom = item.sales_uom if item.sales_uom else item.stock_uom
		elif (args.get("doctype") in ["Purchase Order", "Purchase Receipt", "Purchase Invoice"]) or (
			args.get("doctype") == "Material Request" and args.get("material_request_type") == "Purchase"
		):
			args.uom = item.purchase_uom if item.purchase_uom else item.stock_uom
		else:
			args.uom = item.stock_uom

	# Set stock UOM in args, so that it can be used while fetching item price
	args.stock_uom = item.stock_uom

	if args.get("batch_no") and item.name != frappe.get_cached_value(
		"Batch", args.get("batch_no"), "item"
	):
		args["batch_no"] = ""

	out = frappe._dict(
		{
			"item_code": item.name,
			"item_name": item.item_name,
            "mrp":item.mrp,
			"description": cstr(item.description).strip(),
			"image": cstr(item.image).strip(),
			"warehouse": warehouse,
			"income_account": get_default_income_account(
				args, item_defaults, item_group_defaults, brand_defaults
			),
			"expense_account": expense_account
			or get_default_expense_account(args, item_defaults, item_group_defaults, brand_defaults),
			"discount_account": get_default_discount_account(args, item_defaults),
			"provisional_expense_account": get_provisional_account(args, item_defaults),
			"cost_center": get_default_cost_center(
				args, item_defaults, item_group_defaults, brand_defaults
			),
			"has_serial_no": item.has_serial_no,
			"has_batch_no": item.has_batch_no,
			"batch_no": args.get("batch_no"),
			"uom": args.uom,
			"stock_uom": item.stock_uom,
			"min_order_qty": flt(item.min_order_qty) if args.doctype == "Material Request" else "",
			"qty": flt(args.qty) or 1.0,
			"stock_qty": flt(args.qty) or 1.0,
			"price_list_rate": 0.0,
			"base_price_list_rate": 0.0,
			"rate": 0.0,
			"base_rate": 0.0,
			"amount": 0.0,
			"base_amount": 0.0,
			"net_rate": 0.0,
			"net_amount": 0.0,
			"discount_percentage": 0.0,
			"discount_amount": flt(args.discount_amount) or 0.0,
			"supplier": get_default_supplier(args, item_defaults, item_group_defaults, brand_defaults),
			"update_stock": args.get("update_stock")
			if args.get("doctype") in ["Sales Invoice", "Purchase Invoice"]
			else 0,
			"delivered_by_supplier": item.delivered_by_supplier
			if args.get("doctype") in ["Sales Order", "Sales Invoice"]
			else 0,
			"is_fixed_asset": item.is_fixed_asset,
			"last_purchase_rate": item.last_purchase_rate
			if args.get("doctype") in ["Purchase Order"]
			else 0,
			"transaction_date": args.get("transaction_date"),
			"against_blanket_order": args.get("against_blanket_order"),
			"bom_no": item.get("default_bom"),
			"weight_per_unit": args.get("weight_per_unit") or item.get("weight_per_unit"),
			"weight_uom": args.get("weight_uom") or item.get("weight_uom"),
			"grant_commission": item.get("grant_commission"),
		}
	)

	if item.get("enable_deferred_revenue") or item.get("enable_deferred_expense"):
		out.update(calculate_service_end_date(args, item))

	# calculate conversion factor
	if item.stock_uom == args.uom:
		out.conversion_factor = 1.0
	else:
		out.conversion_factor = args.conversion_factor or get_conversion_factor(item.name, args.uom).get(
			"conversion_factor"
		)

	args.conversion_factor = out.conversion_factor
	out.stock_qty = out.qty * out.conversion_factor
	args.stock_qty = out.stock_qty

	# calculate last purchase rate
	if args.get("doctype") in purchase_doctypes:
		from erpnext.buying.doctype.purchase_order.purchase_order import item_last_purchase_rate

		out.last_purchase_rate = item_last_purchase_rate(
			args.name, args.conversion_rate, item.name, out.conversion_factor
		)

	# if default specified in item is for another company, fetch from company
	for d in [
		["Account", "income_account", "default_income_account"],
		["Account", "expense_account", "default_expense_account"],
		["Cost Center", "cost_center", "cost_center"],
		["Warehouse", "warehouse", ""],
	]:
		if not out[d[1]]:
			out[d[1]] = frappe.get_cached_value("Company", args.company, d[2]) if d[2] else None

	for fieldname in ("item_name", "item_group", "brand", "stock_uom"):
		out[fieldname] = item.get(fieldname)

	if args.get("manufacturer"):
		part_no = get_item_manufacturer_part_no(args.get("item_code"), args.get("manufacturer"))
		if part_no:
			out["manufacturer_part_no"] = part_no
		else:
			out["manufacturer_part_no"] = None
			out["manufacturer"] = None
	else:
		data = frappe.get_value(
			"Item", item.name, ["default_item_manufacturer", "default_manufacturer_part_no"], as_dict=1
		)

		if data:
			out.update(
				{
					"manufacturer": data.default_item_manufacturer,
					"manufacturer_part_no": data.default_manufacturer_part_no,
				}
			)

	child_doctype = args.doctype + " Item"
	meta = frappe.get_meta(child_doctype)
	if meta.get_field("barcode"):
		update_barcode_value(out)

	if out.get("weight_per_unit"):
		out["total_weight"] = out.weight_per_unit * out.stock_qty

	return out

def process_args(args):
	if isinstance(args, string_types):
		args = json.loads(args)

	args = frappe._dict(args)

	if not args.get("price_list"):
		args.price_list = args.get("selling_price_list") or args.get("buying_price_list")

	if args.barcode:
		args.item_code = get_item_code(barcode=args.barcode)
	elif not args.item_code and args.serial_no:
		args.item_code = get_item_code(serial_no=args.serial_no)

	set_transaction_type(args)
	return args


def get_item_warehouse(item, args, overwrite_warehouse, defaults=None):
	if not defaults:
		defaults = frappe._dict(
			{
				"item_defaults": get_item_defaults(item.name, args.company),
				"item_group_defaults": get_item_group_defaults(item.name, args.company),
				"brand_defaults": get_brand_defaults(item.name, args.company),
			}
		)

	if overwrite_warehouse or not args.warehouse:
		warehouse = (
			args.get("set_warehouse")
			or defaults.item_defaults.get("default_warehouse")
			or defaults.item_group_defaults.get("default_warehouse")
			or defaults.brand_defaults.get("default_warehouse")
			or args.get("warehouse")
		)

		if not warehouse:
			defaults = frappe.defaults.get_defaults() or {}
			warehouse_exists = frappe.db.exists(
				"Warehouse", {"name": defaults.default_warehouse, "company": args.company}
			)
			if defaults.get("default_warehouse") and warehouse_exists:
				warehouse = defaults.default_warehouse

	else:
		warehouse = args.get("warehouse")

	if not warehouse:
		default_warehouse = frappe.db.get_single_value("Stock Settings", "default_warehouse")
		if frappe.db.get_value("Warehouse", default_warehouse, "company") == args.company:
			return default_warehouse

	return warehouse

def get_default_income_account(args, item, item_group, brand):
	return (
		item.get("income_account")
		or item_group.get("income_account")
		or brand.get("income_account")
		or args.income_account
	)


def get_default_expense_account(args, item, item_group, brand):
	return (
		item.get("expense_account")
		or item_group.get("expense_account")
		or brand.get("expense_account")
		or args.expense_account
	)


def get_provisional_account(args, item):
	return item.get("default_provisional_account") or args.default_provisional_account


def get_default_discount_account(args, item):
	return item.get("default_discount_account") or args.discount_account


def get_default_deferred_account(args, item, fieldname=None):
	if item.get("enable_deferred_revenue") or item.get("enable_deferred_expense"):
		return (
			item.get(fieldname)
			or args.get(fieldname)
			or frappe.get_cached_value("Company", args.company, "default_" + fieldname)
		)
	else:
		return None


def get_default_cost_center(args, item=None, item_group=None, brand=None, company=None):
	cost_center = None

	if not company and args.get("company"):
		company = args.get("company")

	if args.get("project"):
		cost_center = frappe.db.get_value("Project", args.get("project"), "cost_center", cache=True)

	if not cost_center and (item and item_group and brand):
		if args.get("customer"):
			cost_center = (
				item.get("selling_cost_center")
				or item_group.get("selling_cost_center")
				or brand.get("selling_cost_center")
			)
		else:
			cost_center = (
				item.get("buying_cost_center")
				or item_group.get("buying_cost_center")
				or brand.get("buying_cost_center")
			)

	elif not cost_center and args.get("item_code") and company:
		for method in ["get_item_defaults", "get_item_group_defaults", "get_brand_defaults"]:
			path = "erpnext.stock.get_item_details.{0}".format(method)
			data = frappe.get_attr(path)(args.get("item_code"), company)

			if data and (data.selling_cost_center or data.buying_cost_center):
				return data.selling_cost_center or data.buying_cost_center

	if not cost_center and args.get("cost_center"):
		cost_center = args.get("cost_center")

	if (
		company
		and cost_center
		and frappe.get_cached_value("Cost Center", cost_center, "company") != company
	):
		return None

	if not cost_center and company:
		cost_center = frappe.get_cached_value("Company", company, "cost_center")

	return cost_center

def get_default_supplier(args, item, item_group, brand):
	return (
		item.get("default_supplier")
		or item_group.get("default_supplier")
		or brand.get("default_supplier")
	)


def get_price_list_rate(args, item_doc, out=None):
	if out is None:
		out = frappe._dict()

	meta = frappe.get_meta(args.parenttype or args.doctype)

	if meta.get_field("currency") or args.get("currency"):
		if not args.get("price_list_currency") or not args.get("plc_conversion_rate"):
			# if currency and plc_conversion_rate exist then
			# `get_price_list_currency_and_exchange_rate` has already been called
			pl_details = get_price_list_currency_and_exchange_rate(args)
			args.update(pl_details)

		if meta.get_field("currency"):
			validate_conversion_rate(args, meta)

		price_list_rate = get_price_list_rate_for(args, item_doc.name)

		# variant
		if price_list_rate is None and item_doc.variant_of:
			price_list_rate = get_price_list_rate_for(args, item_doc.variant_of)

		# insert in database
		if price_list_rate is None:
			if args.price_list and args.rate:
				insert_item_price(args)
			return out

		out.price_list_rate = (
			flt(price_list_rate) * flt(args.plc_conversion_rate) / flt(args.conversion_rate)
		)

		if not out.price_list_rate and args.transaction_type == "buying":
			from erpnext.stock.doctype.item.item import get_last_purchase_details

			out.update(get_last_purchase_details(item_doc.name, args.name, args.conversion_rate))

	return out

def update_barcode_value(out):
	barcode_data = get_barcode_data([out])

	# If item has one barcode then update the value of the barcode field
	if barcode_data and len(barcode_data.get(out.item_code)) == 1:
		out["barcode"] = barcode_data.get(out.item_code)[0]


def get_barcode_data(items_list):
	# get itemwise batch no data
	# exmaple: {'LED-GRE': [Batch001, Batch002]}
	# where LED-GRE is item code, SN0001 is serial no and Pune is warehouse

	itemwise_barcode = {}
	for item in items_list:
		barcodes = frappe.db.sql(
			"""
			select barcode from `tabItem Barcode` where parent = %s
		""",
			item.item_code,
			as_dict=1,
		)

		for barcode in barcodes:
			if item.item_code not in itemwise_barcode:
				itemwise_barcode.setdefault(item.item_code, [])
			itemwise_barcode[item.item_code].append(barcode.get("barcode"))

	return itemwise_barcode


@frappe.whitelist()
def get_attendance():
	url = "http://www.esslcloud.com/DW001/WebAPIService.asmx"
	data = """<?xml version="1.0" encoding="utf-8"?>
	<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
	<soap:Body>
		<GetTransactionsLog xmlns="http://tempuri.org/">
			<FromDateTime>2023-11-12 10:00:01</FromDateTime>
			<ToDateTime>2023-11-24 23:59:00</ToDateTime>
			<SerialNumber>CGKK232561771</SerialNumber>
			<UserName>faircode</UserName>
			<UserPassword>Admin@123</UserPassword>
		</GetTransactionsLog>
	</soap:Body>
	</soap:Envelope>"""
	headers = {
		'Host': 'www.esslcloud.com',
		'Content-Type': 'text/xml; charset=utf-8',
		'Content-Length': str(len(data)),
		'SOAPAction': 'http://tempuri.org/GetTransactionsLog'
	}
	
	response = requests.post(url, headers=headers, data=data)
	print(response.text)
	return response.text