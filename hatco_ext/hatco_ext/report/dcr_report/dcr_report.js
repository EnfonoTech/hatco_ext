
// Copyright (c) 2026, Aravind R and contributors
// For license information, please see license.txt

frappe.query_reports["DCR Report"] = {
    "tree": true,
    "initial_depth": 0,
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
            "options": [
                "",
                "Opening Cash Balance",
                "Cash Sales",
                "Card/Bank Sales",
                "Credit Sales",
                "Cash Sales Return",
                "Card/Bank Sales Return",
                "Credit Sales Return",
                "Cash Purchases",
                "Card/Bank Purchases",
                "Credit Purchases",
                "Cash Purchase Return",
                "Card/Bank Purchase Return",
                "Credit Purchase Return",
                "Customer Receipts (Cash)",
                "Customer Receipts",
                "Supplier Payments (Cash)",
                "Supplier Payments",
                "Bank Receipts",
                "Bank Payments",
                "Cash Receipts",
                "Cash Payments",
                "Journal Entry",
                "Internal Transfer",
                "Cash Balance"
            ].join("\n"),
            "reqd": 0
        },
        {
            "fieldname": "company",
            "label": "Company",
            "fieldtype": "Link",
            "options": "Company",
            "reqd": 0
        },
        {
            "fieldname": "cost_center",
            "label": "Cost Center",
            "fieldtype": "Link",
            "options": "Cost Center",
            "get_query": function() {
                var company = frappe.query_report.get_filter_value("company");
                if (company) {
                    return { "filters": { "company": company } };
                }
                return {};
            }
        }
    ],

    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (column.fieldname === "type" && data && data.voucher_type && data.voucher_no) {
            value = `<a href="/app/${frappe.router.slug(data.voucher_type)}/${data.voucher_no}"
                    style="color:#000000; text-decoration:underline;">
                        ${value}
                    </a>`;
        }

        if (data && data.bold) {
            return `<strong style="font-weight:700;">${value}</strong>`;
        }

        return value;
    }
};
