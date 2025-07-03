frappe.ui.form.on('Sales Order Item', {
  item_code: function(frm, cdt, cdn){
     let d = locals[cdt][cdn];
     if (d.item_code){
       setTimeout(() => {
          //  frappe.call({
          //    method: 'njayallur.njayallur.doc_events.sales_order.get_discount',
          //    args: {
          //      'item_code': d.item_code,
          //      'customer': frm.doc.customer
          //    },
          //    callback: function(r) {
          //      if (r.message){
          //        d.rate = d.rate - r.message;
          //        d.discount_amount = r.message;
          //        d.amount = d.amount - r.message;
          //        frm.refresh_field('items');
          //        frm.doc.total = 0;
          //        frm.doc.grand_total = 0;
          //        frm.doc.items.forEach(function(item) {
          //            frm.doc.total += (item.qty * item.rate);
          //        });
          //        frm.doc.grand_total = frm.doc.total + frm.doc.total_taxes_and_charges;
          //        frm.doc.rounded_total = frm.doc.total + frm.doc.total_taxes_and_charges;
          //        frm.refresh_field('total');
          //        frm.refresh_field('grand_total');
          //        frm.refresh_field('rounded_total');
          //      }
          //    }
          //  });
           frappe.call({
            method: 'njayallur.njayallur.doc_events.sales_order.detect_discount',
            args: {
                'item_code': d.item_code,
                'customer': frm.doc.customer,
            },
            callback: function(response) {
              console.log('j',response)
                 if (response.message) {
                      frappe.model.set_value(cdt, cdn, 'custom_discount_percentage', response.message);
                      frappe.model.set_value(cdt, cdn, 'discount_percentage', response.message);
                      frm.refresh_field('items');
                  } else {
                    frappe.model.set_value(cdt, cdn, 'discount_percentage', 0);
                    frappe.model.set_value(cdt, cdn, 'discount_amount', 0);
                }
            }
        });
       }, 500);
     }
   }
})

frappe.ui.form.on("Sales Order Item", {
  custom_discount_percentage(frm, cdt, cdn){
    let row = locals[cdt][cdn]
    frappe.model.set_value(cdt, cdn, "discount_percentage", row.custom_discount_percentage)
    frm.refresh_field("items")
  }
})
