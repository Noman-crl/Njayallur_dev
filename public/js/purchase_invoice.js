// frappe.ui.form.on("Purchase Invoice Item", {
//     custom_discount_percentage(frm, cdt, cdn){
//         let row = locals[cdt][cdn]
//         frappe.model.set_value(cdt, cdn, "discount_amount", row.price_list_rate*(row.custom_discount_percentage/100))
//         frm.refresh_field("items")
//     },
//     item_code: function(frm, cdt, cdn) {
//         let row = locals[cdt][cdn];
//         if (row.item_code) {
//             frappe.call({
//                 method: 'njayallur.njayallur.doc_events.custom_api.get_item_mrp', 
//                 args: {
//                     item_code: row.item_code
//                 },
//                 callback: function(r) {
//                     if (r.message) {
//                         let mrp = r.message.mrp || 0;
//                         frappe.model.set_value(cdt, cdn, "custom_mrp", mrp);
//                         frm.refresh_field("items");  
//                     } else {
//                         frappe.model.set_value(cdt, cdn, "custom_mrp", 0);
//                     }
//                 }
//             });
//         } else {
//             frappe.model.set_value(cdt, cdn, "custom_mrp", 0);
//         }
//     }
// });


    
frappe.ui.form.on("Purchase Invoice Item", {
    custom_discount_percentage(frm, cdt, cdn){
        let row = locals[cdt][cdn];
        frappe.model.set_value(cdt, cdn, "discount_amount", row.price_list_rate*(row.custom_discount_percentage/100));
        frm.refresh_field("items");
    },
    item_code: function(frm, cdt, cdn) {
        fetch_mrp(frm, cdt, cdn);
    }
});

frappe.ui.form.on("Purchase Invoice", {
    // onload_post_render(frm) {
    before_save(frm) {
        frm.doc.items.forEach(item => {
            fetch_mrp(frm, item.doctype, item.name);
        });                    
    },
    items_add: function(frm, cdt, cdn) {
        fetch_mrp(frm, cdt, cdn);
    }
});

function fetch_mrp(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    if (row.item_code) {
        frappe.call({
            method: 'njayallur.njayallur.doc_events.custom_api.get_item_mrp', 
            args: {
                item_code: row.item_code
            },
            callback: function(r) {
                if (r.message) {
                    let mrp = r.message.mrp || 0;
                    frappe.model.set_value(cdt, cdn, "custom_mrp", mrp);
                } else {
                    frappe.model.set_value(cdt, cdn, "custom_mrp", 0);
                }
                frm.refresh_field("items");
            }, timeout: 30000 
            
        });
    } else {
        frappe.model.set_value(cdt, cdn, "custom_mrp", 0);
    }
}
