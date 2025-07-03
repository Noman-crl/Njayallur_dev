// frappe.ui.form.on('Customer Group', {
// //  to set the namening series values to the select fields
//     before_load(frm){
//         frappe.call({
//             method : 'njayallur.njayallur.doc_events.custom_api.get_naming_series',
//             callback : function(r) {
//             if (r.message) {
//                 frm.set_df_property("sales_invoice_naming_series", "options", [""].concat(r.message));
//                 }
//             }
//         })
//     }
// });