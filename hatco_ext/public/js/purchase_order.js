frappe.ui.form.on('Purchase Order', {
    cost_center: function(frm) {
        if (frm.doc.cost_center) {
            $.each(frm.doc.items || [], function(i, row) {
                frappe.model.set_value(row.doctype, row.name, 'cost_center', frm.doc.cost_center);
            });
            $.each(frm.doc.taxes || [], function(i, row) {
                frappe.model.set_value(row.doctype, row.name, 'cost_center', frm.doc.cost_center);
            });
            frm.refresh_field('items');
            frm.refresh_field('taxes');
        }
    },
    onload: function(frm) {
        if (frm.doc.cost_center) {
            $.each(frm.doc.items || [], function(i, row) {
                if (!row.cost_center) {
                    frappe.model.set_value(row.doctype, row.name, 'cost_center', frm.doc.cost_center);
                }
            });
            $.each(frm.doc.taxes || [], function(i, row) {
                if (!row.cost_center) {
                    frappe.model.set_value(row.doctype, row.name, 'cost_center', frm.doc.cost_center);
                }
            });
        }
    }
});

frappe.ui.form.on('Purchase Order Item', {
    items_add: function(frm, cdt, cdn) {
        if (frm.doc.cost_center) {
            frappe.model.set_value(cdt, cdn, 'cost_center', frm.doc.cost_center);
        }
    }
});

frappe.ui.form.on('Purchase Taxes and Charges', {
    taxes_add: function(frm, cdt, cdn) {
        if (frm.doc.cost_center) {
            frappe.model.set_value(cdt, cdn, 'cost_center', frm.doc.cost_center);
        }
    }
});
