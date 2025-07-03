frappe.ui.form.on('Sales Invoice', {
    onload: function(frm) {
        if (frm.doc.docstatus == 0) {
            $.each(frm.doc.items, function(i, v) {
                if (v.discount_percentage == 0) {
                    setTimeout(() => {
                        frappe.call({
                            method: 'njayallur.njayallur.doc_events.sales_invoice.detect_discount',
                            args: {
                                'item_code': v.item_code,
                                'customer': frm.doc.customer,
                            },
                            callback: function(response) {
                                frappe.model.set_value(v.doctype, v.name, 'discount_percentage', response.message || 0);
                                frm.refresh_field('items');
                            }
                        });
                    }, 500);
                }
            });
        }
    },

    after_save: function(frm) {
        frappe.db.get_single_value("Njayallur Settings", 'match_invoice_title').then((match) => {
            if (frm.doc.customer !== frm.doc.title && match) {
                frm.set_value('title', frm.doc.customer);
                frm.refresh_field('title');
                frm.save();
            }
        });
    },

    refresh: function(frm) {
        frm.add_custom_button(__('Print Now'), function() {
            frappe.call({
                method: 'njayallur.njayallur.doc_events.custom_api.print_format_method',
                callback: function(response) {
                    var print_formats = response.message;
                    if (print_formats.length) {
                        frappe.prompt([
                            {'fieldname': 'print_format', 'fieldtype': 'Select', 'label': 'Select Print Format', 'options': print_formats.join('\n')}
                        ],
                        function(values){
                            frappe.msgprint('Selected Print Format: ' + values.print_format);
                            getPrintURL(values.print_format);
                        },
                        'Select Print Format');
                    } else {
                        frappe.msgprint('Not found.');
                    }
                }
            });
        });

        function getPrintURL(print_format) {
            frappe.call({
                method: 'njayallur.njayallur.doc_events.custom_api.get_print_url',
                args: {
                    'print_format': print_format,
                    'doc_name': frm.doc.name
                },
                callback: function(response) {
                    var print_url = response.message;
                    if (print_url) {
                        window.open(print_url);
                    } else {
                        frappe.msgprint('Failed to get print URL.');
                    }
                }
            });
        }
    }
});

frappe.ui.form.on('Sales Invoice', {
    refresh: function(frm) {
        if (frm.doc.docstatus == 0) {
            calculateNonTaxableValue(frm);
        }
    },
    items_add: function(frm) {
        calculateNonTaxableValue(frm);
    },
    items_remove: function(frm) {
        calculateNonTaxableValue(frm);
    }
});

function calculateNonTaxableValue(frm) {
    var totalNonTaxable = 0;
    frm.doc.items.forEach(function(item) {
        if (item.item_tax_template === "In State GST 0%") {
            totalNonTaxable += flt(item.amount);
        }
    });
    frm.set_value("custom_non_taxable_value", totalNonTaxable);
    console.log("Custom non-taxable value calculated:", totalNonTaxable);
}

frappe.ui.form.on('Sales Invoice', {
    refresh: function(frm) {
        $('.audit-trail').hide();
    }
});

function check_customer_overdue_and_unpaid_invoices(frm) {
    frappe.db.get_doc("Njayallur Settings").then(settings => {
        let customer = frm.doc.customer;

        if (settings.check_overdue && customer) {
            frappe.xcall("njayallur.njayallur.doc_events.sales_invoice.get_overdue_invoice", { "customer": customer })
                .then(doc => {
                    if (doc) {
                        setTimeout(() => {
                            frappe.msgprint(`<b>${customer}</b> has an <b>overdue</b> of <b>INR ${doc.outstanding}</b> from Invoice <b>${doc.invoice}</b>`);
                            frm.set_value("customer", "");
                        }, 500);
                    }
                });
        }

        if (settings.allowed_bills_without_payment) {
            frappe.xcall("njayallur.njayallur.doc_events.sales_invoice.check_unpaid_invoice", { "customer": customer })
                .then(count => {
                    if (count >= settings.allowed_bills_without_payment) {
                        setTimeout(() => {
                            frappe.msgprint(`<b>${customer}</b> has <b>${count}</b> Unpaid/Partly Paid invoices`);
                            frm.set_value("customer", "");
                        }, 500);
                    }
                });
        }
    });
}

frappe.ui.form.on('Sales Invoice Item', {
    item_code: function(frm, cdt, cdn) {
        let d = locals[cdt][cdn];
        if (d.item_code) {
            setTimeout(() => {
                frappe.call({
                    method: 'njayallur.njayallur.doc_events.sales_invoice.detect_discount',
                    args: {
                        'item_code': d.item_code,
                        'customer': frm.doc.customer,
                    },
                    callback: function(response) {
                        frappe.model.set_value(cdt, cdn, 'custom_discount_percentage', response.message || 0);
                        frappe.model.set_value(cdt, cdn, 'discount_percentage', response.message || 0);
                        frm.refresh_field('items');
                    }
                });

                frappe.call({
                    method: 'njayallur.njayallur.doc_events.sales_invoice.get_item_data',
                    args: {
                        'item_code': d.item_code,
                        'customer': frm.doc.customer,
                        'rate': d.rate,
                        'item_tax_template': d.item_tax_template
                    },
                    callback: function(r) {
                        if (r.message && r.message.blacklisted) {
                            frappe.msgprint(`<b>${d.item_code}</b> is blacklisted`);
                            frm.doc.items.splice(d.idx - 1, 1);
                            frm.refresh_field("items");
                        }
                    }
                });
            }, 500);
        }
    },

    custom_discount_percentage: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        frappe.model.set_value(cdt, cdn, "discount_amount", row.price_list_rate * (row.custom_discount_percentage / 100));
        frm.refresh_field("items");
    }
});
