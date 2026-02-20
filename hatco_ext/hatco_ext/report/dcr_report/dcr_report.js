// Copyright (c) 2026, Aravind R and contributors
// For license information, please see license.txt

//Filters for DCR Report
frappe.query_reports["DCR Report"] = {
    "filters": [
        {
            "fieldname": "date",
            "label": "Date",
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
            "reqd": 0 
        },
        {
            "fieldname": "type",
            "label": "Type",
            "fieldtype": "Select",
            "options": "\nCash Sales\nCard Sales\nCredit Sales\nCash Purchases\nCard Purchases\nCredit Purchases\nSales Return\nPurchase Return\nCustomer Receipts\nSupplier Payments\nBank Receipts\nBank Payments\nCash Receipts\nCash Payments\nJournal Entry",
            "reqd": 0 
        },
        {
            "fieldname": "cost_center",
            "label": "Cost Center",
            "fieldtype": "Link",
            "options": "Cost Center"
        }
    ],
    
    // Types into a clickable link

    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        
        if (column.fieldname === "type" && data && data.voucher_type && data.voucher_no) {

            const doctype = data.voucher_type;
            const docname = data.voucher_no;
            
            const regex = new RegExp(`(${docname})`, 'g');
            value = value.replace(regex, `<a href="/app/${doctype.toLowerCase().replace(/\s+/g, '-')}/${docname}" style="color: #000000; text-decoration: underline;">${docname}</a>`);
        }
        
        return value;
    }
};