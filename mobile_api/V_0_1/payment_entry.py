import frappe
from datetime import datetime

@frappe.whitelist(allow_guest=True)
def pe_list(filter=None):
    try:
        pe_filter = {}
        
        if filter:
            if filter.get("customer"):
                pe_filter["party"] = filter.get("customer")
            if filter.get("name"):
                pe_filter["name"] = filter.get("name")
            if filter.get("from_date"):
                pe_filter["posting_date"] = datetime.strptime(filter.get("from_date"), '%d-%m-%Y')
            if filter.get("to_date"):
                if filter.get("from_date"):
                    pe_filter["posting_date"] = ('between', [datetime.strptime(filter.get("from_date"), '%d-%m-%Y'), datetime.strptime(filter.get("to_date"), '%d-%m-%Y')])
                else:
                    pe_filter["posting_date"] = filter.get("to_date")

        pe_list = frappe.get_list(
            "Payment Entry",
            filters=pe_filter,
            fields=["name", "party", "payment_type", "mode_of_payment", "paid_amount", "total_allocated_amount", "posting_date", "status", "docstatus"],
            order_by="modified desc",
            ignore_permissions=True
        )

        frappe.local.response["status_code"] = 200
        frappe.local.response["message"] = "Success"
        frappe.local.response["data"] = pe_list
    except Exception as e:
        frappe.local.response["status_code"] = 500
        frappe.local.response["exception"] = str(e)
        frappe.local.response["message"] = "Something went wrong"


@frappe.whitelist()
def pe_details(payment_entry):
    """
    - Detials of a Payment Entry.
    - args: payment_entry(Mandatory).
    - keys: naming_series, name, payment_type, posting_date, company, paty, party_name,
            paid_from, paid_to, paid_amount, received_amount, total_allocated_amount, 
            total_taxes_and_charges, mode_of_payment, status, docstatus, 
            references: reference_doctype, reference_name, total_amount, outstanding_amount,
                        allocated_amount. 
    """
    try:
        if not frappe.db.exists("Payment Entry", {"name": payment_entry}):
            raise Exception("Payment Entry not found")
        doc = frappe.get_doc("Payment Entry", payment_entry)
        payment_entry_data = {
            'naming_series': doc.naming_series,
            'name': doc.name,
            'payment_type':doc.payment_type,
            'posting_date':doc.posting_date.strftime("%d-%m-%Y"),
            'company':doc.company,
            'paty': doc.party,
            'party_name':doc.party_name,
            'paid_from':doc.paid_from,
            'paid_to':doc.paid_to,
            'paid_amount':doc.paid_amount,
            'source_exchange_rate':doc.source_exchange_rate,
            'target_exchange_rate':doc.target_exchange_rate,
            'received_amount':doc.received_amount,
            'total_allocated_amount':doc.total_allocated_amount,
            'total_taxes_and_charges':doc.total_taxes_and_charges,
            'mode_of_payment':doc.mode_of_payment,
            'status': doc.status,
            'docstatus': doc.docstatus,
            'references': frappe.db.get_list(
                "Payment Entry Reference",
                {"parent":doc.name},
                ['reference_doctype', 'reference_name', 'total_amount', 'outstanding_amount', 'allocated_amount'],
                ignore_permissions=True
            )
        }
        frappe.local.response["status_code"] = 200
        frappe.local.response["message"] = "Success"
        frappe.local.response["data"] = payment_entry_data

    except Exception as e:
        frappe.local.response["status_code"] = 500
        frappe.local.response["exception"] = str(e)
        frappe.local.response["message"] = "Something went wrong"

@frappe.whitelist()
def create_pe_from_si(sales_invoice):
    """
    - Create Payment Entry from Sales Invoice.
    - Keys: sales_invoice_name (Mandatory).
    - Inserts Payment Entry in draft
    """
    try:
        # check if sales invoice exists
        if not frappe.db.exists("Sales Invoice", sales_invoice):
            raise Exception("Sales invoice not found")

        # get sales invoice document
        invoice = frappe.get_doc("Sales Invoice", sales_invoice)
        if invoice.status == "Paid":
            raise Exception("Invoice is fully paid")

        # create payment entry document
        payment_entry = frappe.new_doc("Payment Entry")
        payment_entry.posting_date = frappe.utils.nowdate()
        payment_entry.payment_type = "Receive"
        payment_entry.party_type = "Customer"
        payment_entry.party = invoice.customer
        payment_entry.source_exchange_rate = 1.0
        payment_entry.target_exchange_rate = 1.0
        payment_entry.paid_from = invoice.debit_to
        payment_entry.paid_to = 'Cash - NA'
        payment_entry.paid_from_account_currency = frappe.db.get_value("Account", invoice.debit_to, 'account_currency')
        payment_entry.paid_to_account_currency = frappe.db.get_value("Account", 'Cash - NA', 'account_currency')

        # payment_entry.paid_to = sales_invoice.debit_to
        # payment_entry.mode_of_payment = "Cash"
        payment_entry.paid_amount = invoice.outstanding_amount
        payment_entry.received_amount = invoice.outstanding_amount
        payment_entry.reference_no = invoice.name
        payment_entry.reference_date = invoice.posting_date
        payment_entry.remarks = "Payment for sales invoice {}".format(sales_invoice)

        # add payment entry allocation
        allocation = payment_entry.append("references")
        allocation.reference_doctype = "Sales Invoice"
        allocation.reference_name = invoice.name
        allocation.allocated_amount = invoice.outstanding_amount
        # save payment entry
        payment_entry.flags.ignore_permissions=True
        payment_entry.insert()

        frappe.local.response["status_code"] = 200
        frappe.local.response["message"] = "Payment Entry created successfully"
        frappe.local.response["payment_entry"] = payment_entry.name

    except Exception as e:
        frappe.local.response["status_code"] = 500
        frappe.local.response["message"] = "Something went wrong"
        frappe.local.response["exception"] = str(e)

@frappe.whitelist()
def create_pe(data):
    """
    - Create standalone Payment Entry.
    - Keys: customer, amount, company, paid_from, paid_to, posting_date,
            references: allocated_amount, reference_doctype, reference_name
    """
    try:
        if not data.get("customer") or not data.get("paid_amount"):
            raise Exception("Customer and amount are mandatory.")

        # Convert the amount to a float value
        amount_float = float(data.get("paid_amount"))
        posting_date = datetime.strptime(data.get("posting_date"), '%d-%m-%Y').strftime('%Y-%m-%d')

        # Create the payment entry
        payment_entry = frappe.get_doc({
            'doctype': 'Payment Entry',
            'payment_type': "Receive",
            'company': frappe.defaults.get_defaults().get("company"),
            'paid_from': data.get("paid_from"),
            'paid_to': data.get("paid_to"),
            'mode_of_payment': data.get("mode_of_payment"),
            'posting_date': posting_date,
            'paid_amount': amount_float,
            'received_amount': amount_float,
            'party_type': 'Customer',
            'party': data.get("customer")
        })

        # Append payment references
        references = data.get("references")
        if references:
            for reference in references:
                allocated_amount = float(reference.get("allocated_amount"))
                payment_entry.append("references", {
                    "reference_doctype": reference.get("doctype"),
                    "reference_name": reference.get("docname"),
                    "allocated_amount": allocated_amount
                })

        payment_entry.insert(ignore_permissions=True)

        frappe.local.response["status_code"] = 200
        frappe.local.response["payment_entry"] = payment_entry.name
        frappe.local.response["message"] = "Payment Entry created successfully."
    except Exception as e:
        frappe.local.response["status_code"] = 500
        frappe.local.response["message"] = "Something went wrong"
        frappe.local.response["exception"] = str(e)

@frappe.whitelist(allow_guest=True)
def update_pe(data):
    """
    - Update a Payment Entry.
    - Args: customer, amount, mode_of_payment, party, posting_date, paid_from, paid_to,
            references: reference_doctype, reference_name, allocated_amount
    """
    try:
        if not data.get("name"):
            raise Exception("Payment Entry name is missing")
        payment_entry = data.get("name")
        if not frappe.db.exists("Payment Entry", {"name": payment_entry, "docstatus": 0}):
            raise Exception("Payment Entry not found or not in draft state")
        
        payment_entry = frappe.get_doc("Payment Entry", payment_entry)
        
        # Update fields if provided in the data
        if data.get("customer"):
            payment_entry.party = data.get("customer")
        if data.get("paid_amount"):
            payment_entry.paid_amount = data.get("amount")
        if data.get("mode_of_payment"):
            payment_entry.mode_of_payment = data.get("mode_of_payment")
        if data.get("posting_date"):
            payment_entry.posting_date = datetime.strptime(data.get("posting_date"), '%d-%m-%Y')
        # if data.get("total_allocated_amount"):
        #     payment_entry.total_allocated_amount = data.get("total_allocated_amount")
        if data.get("paid_from"):
            payment_entry.paid_from =  data.get("paid_from")
        if data.get("paid_to"):
            payment_entry.paid_to = data.get("paid_to")
        
        # Update child table references
        references = data.get("references")
        if references and references[0].get("doctype"):
            payment_entry.references = []  # Clear existing references
            for reference in references:
                payment_entry.append("references", {
                    "reference_doctype": reference.get("doctype"),
                    "reference_name": reference.get("docname"),
                    "allocated_amount": reference.get("allocated_amount")
                })
        
        # Save the updated payment entry
        payment_entry.flags.ignore_validate = True
        payment_entry.save(ignore_permissions=True)
        
        frappe.local.response["status_code"] = 200
        frappe.local.response["message"] = "Payment Entry updated successfully."
        frappe.local.response["payment_entry"] = payment_entry.name
    except Exception as e:
        frappe.local.response["status_code"] = 500
        frappe.local.response["message"] = "Something went wrong"
        frappe.local.response["exception"] = str(e)  

@frappe.whitelist()
def paid_from_accounts():
    try:
        frappe.local.response["status_code"] = 200
        frappe.local.response["message"] = "Payment Entry updated successfully."
        frappe.local.response["account"] = frappe.db.get_list(
            "Account",
            {
                "account_type":"Receivable", 
                "is_group":False, 
                "company":frappe.defaults.get_defaults().get("company")
            },
            pluck='name',
            ignore_permissions=True
        )
    except Exception as e:
        frappe.local.response["status_code"] = 500
        frappe.local.response["message"] = "Something went wrong"
        frappe.local.response["exception"] = str(e)

@frappe.whitelist()
def paid_to_accounts():
    try:
        frappe.local.response["status_code"] = 200
        frappe.local.response["message"] = "Payment Entry updated successfully."
        frappe.local.response["account"] = frappe.db.get_list(
            "Account",
            {
                "account_type":('in', ['Bank', "Cash"]), 
                "is_group":False, 
                "company":frappe.defaults.get_defaults().get("company")
            },
            pluck='name',
            ignore_permissions=True
        )
    except Exception as e:
        frappe.local.response["status_code"] = 500
        frappe.local.response["message"] = "Something went wrong"
        frappe.local.response["exception"] = str(e)