frappe.ui.form.on('Sales Invoice', {
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

frappe.ui.form.on('Sales Invoice Item', {
    items_add: function(frm, cdt, cdn) {
        if (frm.doc.cost_center) {
            frappe.model.set_value(cdt, cdn, 'cost_center', frm.doc.cost_center);
        }
    }
});

frappe.ui.form.on('Sales Taxes and Charges', {
    taxes_add: function(frm, cdt, cdn) {
        if (frm.doc.cost_center) {
            frappe.model.set_value(cdt, cdn, 'cost_center', frm.doc.cost_center);
        }
    }
});

frappe.ui.form.on('Sales Invoice', {
    refresh: function(frm) {
        setTimeout(function() {
            let grid_footer = frm.fields_dict['items'].grid.wrapper.find('.grid-footer');
            let $spb = grid_footer.find('button').filter(function() {
                return $(this).text().trim() === 'Show Price History';
            });
            if ($spb.length) {
                $spb.off('click').on('click', function(e) {
                    e.stopImmediatePropagation();
                    show_price_history_dialog(frm);
                });

                let $phb = grid_footer.find('button').filter(function() {
                    return $(this).text().trim() === 'Show Purchase History';
                });
                if (!$phb.length) {
                    let $btn = $($spb[0].outerHTML).text('Show Purchase History').off('click');
                    $btn.on('click', function() {
                        show_purchase_history_dialog(frm);
                    });
                    $spb.after($btn);
                }
            }
        }, 300);
    }
});

function show_price_history_dialog(frm) {
    function fetch_history() {
        let item_code = d.get_value('item_code');
        if (!item_code) return;
        frappe.call({
            method: 'hatco_ext.api.get_price_history',
            args: {
                item_code: item_code,
                company: frm.doc.company,
                cost_center: frm.doc.cost_center || null
            },
            callback: function(r) {
                let rows = r.message || [];
                if (!rows.length) {
                    d.fields_dict.history.$wrapper.html(
                        '<p class="text-muted text-center" style="padding:20px">' + __('No history found') + '</p>'
                    );
                    return;
                }
                let html = `<table class="table table-bordered table-condensed" style="margin-top:10px">
                    <thead><tr>
                        <th>${__('Item Name')}</th>
                        <th>${__('Customer')}</th>
                        <th>${__('Sales Rate')}</th>
                        <th>${__('Sales Qty')}</th>
                        <th>${__('Invoice')}</th>
                        <th>${__('Date')}</th>
                    </tr></thead><tbody>`;
                rows.forEach(function(row) {
                    html += `<tr>
                        <td>${row.item_name || ''}</td>
                        <td>${row.customer || ''}</td>
                        <td>${frappe.format(row.sales_rate, {fieldtype:'Currency'})}</td>
                        <td>${row.sales_qty}</td>
                        <td><a href="/app/sales-invoice/${row.sales_invoice}" target="_blank">${row.sales_invoice}</a></td>
                        <td>${frappe.datetime.str_to_user(row.date)}</td>
                    </tr>`;
                });
                html += '</tbody></table>';
                d.fields_dict.history.$wrapper.html(html);
            }
        });
    }

    let d = new frappe.ui.Dialog({
        title: __('Item Sales & Purchase Price History'),
        size: 'large',
        fields: [
            {
                fieldname: 'item_code',
                label: __('Item Code'),
                fieldtype: 'Link',
                options: 'Item',
                reqd: 1,
                change: fetch_history
            },
            {
                fieldname: 'history',
                fieldtype: 'HTML'
            }
        ]
    });

    if (frm.doc.items && frm.doc.items.length === 1) {
        d.set_value('item_code', frm.doc.items[0].item_code);
    }

    d.show();
}

function show_purchase_history_dialog(frm) {
    function fetch_history() {
        let item_code = pd.get_value('item_code');
        if (!item_code) return;
        frappe.call({
            method: 'hatco_ext.api.get_purchase_history',
            args: {
                item_code: item_code,
                company: frm.doc.company
            },
            callback: function(r) {
                let rows = r.message || [];
                if (!rows.length) {
                    pd.fields_dict.history.$wrapper.html(
                        '<p class="text-muted text-center" style="padding:20px">' + __('No purchase history found') + '</p>'
                    );
                    return;
                }
                let html = `<table class="table table-bordered table-condensed" style="margin-top:10px">
                    <thead><tr>
                        <th>${__('Item Name')}</th>
                        <th>${__('Supplier')}</th>
                        <th>${__('Purchase Rate')}</th>
                        <th>${__('Purchase Qty')}</th>
                        <th>${__('Invoice')}</th>
                        <th>${__('Date')}</th>
                    </tr></thead><tbody>`;
                rows.forEach(function(row) {
                    html += `<tr>
                        <td>${row.item_name || ''}</td>
                        <td>${row.supplier || ''}</td>
                        <td>${frappe.format(row.purchase_rate, {fieldtype:'Currency'})}</td>
                        <td>${row.purchase_qty}</td>
                        <td><a href="/app/purchase-invoice/${row.purchase_invoice}" target="_blank">${row.purchase_invoice}</a></td>
                        <td>${frappe.datetime.str_to_user(row.date)}</td>
                    </tr>`;
                });
                html += '</tbody></table>';
                pd.fields_dict.history.$wrapper.html(html);
            }
        });
    }

    let pd = new frappe.ui.Dialog({
        title: __('Purchase History'),
        size: 'large',
        fields: [
            {
                fieldname: 'item_code',
                label: __('Item Code'),
                fieldtype: 'Link',
                options: 'Item',
                reqd: 1,
                change: fetch_history
            },
            {
                fieldname: 'history',
                fieldtype: 'HTML'
            }
        ]
    });

    if (frm.doc.items && frm.doc.items.length === 1) {
        pd.set_value('item_code', frm.doc.items[0].item_code);
    }

    pd.show();
}
