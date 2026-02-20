# Copyright (c) 2026, Aravind R and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {
            "label": _("Type"),
            "fieldname": "type",
            "fieldtype": "Data",
            "width": 350
        },
        {
            "label": _("Total"),
            "fieldname": "total",
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "label": _("Invoice"),
            "fieldname": "invoice_count",
            "fieldtype": "Int",
            "width": 120
        },
        {
            "label": _("Voucher Type"),
            "fieldname": "voucher_type",
            "fieldtype": "Data",
            "width": 0,
            "hidden": 1
        },
        {
            "label": _("Voucher No"),
            "fieldname": "voucher_no",
            "fieldtype": "Dynamic Link",
            "options": "voucher_type",
            "width": 0,
            "hidden": 1
        }
    ]


def get_data(filters):
    filters = filters or {}
    date = filters.get("date")
    type_filter = filters.get("type")
    cost_center = filters.get("cost_center")  

    types = [
        "Cash Sales",
        "Card/Bank Sales",
        "Credit Sales",
        "Cash Purchases",
        "Card/Bank Purchases",
        "Credit Purchases",
        "Sales Return",
        "Purchase Return",
        "Customer Receipts",
        "Supplier Payments",
        "Bank Receipts",
        "Bank Payments",
        "Cash Receipts",
        "Cash Payments",
        "Journal Entry",
    ]

    # If type filter is selected, show only that type  
    if type_filter:
        types = [type_filter]

    result = []

    for t in types:
        total = 0
        count = 0
        paid_rows = []

        # Voucher type conditions
        if t in ["Cash Sales", "Card/Bank Sales", "Credit Sales"]:
            paid_rows = fetch_sales_invoices(t, date, cost_center)
   
        elif t in ["Cash Purchases", "Card/Bank Purchases", "Credit Purchases"]:
            paid_rows = fetch_purchase_invoices(t, date, cost_center)
       
        elif t == "Sales Return":
            paid_rows = get_sales_returns(date, cost_center)
        elif t == "Purchase Return":
            paid_rows = get_purchase_returns(date, cost_center)
        
        elif t == "Customer Receipts":
            paid_rows = get_customer_receipts(date, cost_center)
        elif t == "Supplier Payments":
            paid_rows = get_supplier_payments(date, cost_center)

       
        elif t in ["Bank Receipts", "Bank Payments", "Cash Receipts", "Cash Payments", "Journal Entry"]:
            paid_rows = get_journal_entries(date, t, cost_center)

        
        total = sum(r.get("amount", 0) or 0 for r in paid_rows)
        count = len(paid_rows)

        # Add total row
        result.append({
            "type": t,
            "total": total,
            "invoice_count": count,
            "indent": 0
        })

        # Add individual invoice/payment rows
        for row in paid_rows:
            result.append({
                "type": f"{row.get('voucher_type', row.get('document',''))} {row.get('voucher_no', row.get('id',''))}",
                "total": row.get("amount", 0),
                "invoice_count": "",
                "voucher_type": row.get("voucher_type", row.get("document","")),
                "voucher_no": row.get("voucher_no", row.get("id","")),
                "indent": 1
            })

    return result


def fetch_sales_invoices(t, date, cost_center):
    """Fetch Sales Invoice rows per type & MoP"""

    date_condition = f"AND si.posting_date = '{date}'" if date else ""

    if t == "Cash Sales":
        mop_condition = None
        amount_field = "IFNULL(SUM(per.allocated_amount),0)"
        date_condition += " AND pe.posting_date = %(date)s"

    elif t == "Card Sales":
        mop_condition = None
        amount_field = "IFNULL(SUM(per.allocated_amount),0)"
        date_condition += " AND pe.posting_date = %(date)s"

    else:  # Credit Sales
        mop_condition = None
        amount_field = "si.grand_total"
        date_condition += """
            AND (
                si.outstanding_amount = si.grand_total
                OR NOT EXISTS (
                    SELECT 1 FROM `tabPayment Entry Reference` per2
                    INNER JOIN `tabPayment Entry` pe2
                        ON pe2.name = per2.parent
                    WHERE per2.reference_name = si.name
                        AND per2.reference_doctype='Sales Invoice'
                        AND pe2.docstatus=1
                        AND pe2.posting_date = %(date)s
                )
            )
        """

    query = f"""
        SELECT si.name AS voucher_no,
               {amount_field} AS amount,
               'Sales Invoice' AS voucher_type
        FROM `tabSales Invoice` si
        LEFT JOIN `tabPayment Entry Reference` per
            ON per.reference_name = si.name AND per.reference_doctype='Sales Invoice'
        LEFT JOIN `tabPayment Entry` pe
            ON pe.name = per.parent AND pe.docstatus=1
        WHERE si.docstatus=1
              AND si.is_return=0
              {date_condition}
              AND (%(cost_center)s IS NULL OR si.cost_center = %(cost_center)s)
        GROUP BY si.name
    """
    return frappe.db.sql(query, {"date": date, "cost_center": cost_center}, as_dict=True)


def fetch_purchase_invoices(t, date, cost_center):
    """Fetch Purchase Invoice rows per type & MoP"""

    date_condition = f"AND pi.posting_date = '{date}'" if date else ""

    if t == "Cash Purchases":
        mop_condition = None
        amount_field = "IFNULL(SUM(per.allocated_amount),0)"
        date_condition += " AND pe.posting_date = %(date)s"

    elif t == "Card Purchases":
        mop_condition = None
        amount_field = "IFNULL(SUM(per.allocated_amount),0)"
        date_condition += " AND pe.posting_date = %(date)s"

    else:  # Credit Purchases
        mop_condition = None
        amount_field = "pi.grand_total"
        date_condition += """
            AND (
                pi.outstanding_amount = pi.grand_total
                OR NOT EXISTS (
                    SELECT 1 FROM `tabPayment Entry Reference` per2
                    INNER JOIN `tabPayment Entry` pe2
                        ON pe2.name = per2.parent
                    WHERE per2.reference_name = pi.name
                        AND per2.reference_doctype='Purchase Invoice'
                        AND pe2.docstatus=1
                        AND pe2.posting_date = %(date)s
                )
            )
        """

    query = f"""
        SELECT pi.name AS voucher_no,
               {amount_field} AS amount,
               'Purchase Invoice' AS voucher_type
        FROM `tabPurchase Invoice` pi
        LEFT JOIN `tabPayment Entry Reference` per
            ON per.reference_name = pi.name AND per.reference_doctype='Purchase Invoice'
        LEFT JOIN `tabPayment Entry` pe
            ON pe.name = per.parent AND pe.docstatus=1
        WHERE pi.docstatus=1
              AND pi.is_return=0
              {date_condition}
              AND (%(cost_center)s IS NULL OR pi.cost_center = %(cost_center)s)
        GROUP BY pi.name
    """

    return frappe.db.sql(query, {"date": date, "cost_center": cost_center}, as_dict=True)


def get_sales_returns(date, cost_center):
    # Fetch sales returns for the exact filter date only
    data = frappe.db.sql("""
        SELECT
            'Sales Return' AS document,
            si.name AS id,
            CASE
                WHEN si.grand_total - IFNULL(SUM(
                    CASE WHEN pe.posting_date = %(date)s AND pe.docstatus=1 
                         THEN per.allocated_amount ELSE 0 END
                ),0) = 0 THEN 'Paid'
                WHEN SUM(
                    CASE WHEN pe.posting_date = %(date)s AND pe.docstatus=1 
                         THEN per.allocated_amount ELSE 0 END
                ) = 0 THEN 'Unpaid'
                ELSE 'Partially Paid'
            END AS status,
            si.grand_total AS invoice_total,
            IFNULL(SUM(
                CASE WHEN pe.posting_date = %(date)s AND pe.docstatus=1 THEN per.allocated_amount ELSE 0 END
            ),0) AS amount,
            COUNT(si.name) OVER () AS total_count
        FROM `tabSales Invoice` si
        LEFT JOIN `tabPayment Entry Reference` per
            ON per.reference_name=si.name AND per.reference_doctype='Sales Invoice'
        LEFT JOIN `tabPayment Entry` pe
            ON pe.name = per.parent
        WHERE si.docstatus=1 
              AND si.is_return=1
              AND si.posting_date = %(date)s
              AND (%(cost_center)s IS NULL OR si.cost_center = %(cost_center)s)
        GROUP BY si.name, si.grand_total
        ORDER BY si.posting_date ASC
    """, {"date": date, "cost_center": cost_center}, as_dict=True)

    return data


def get_purchase_returns(date, cost_center):
    # Fetch purchase returns for the exact invoice posting date only (like Sales Returns)
    return frappe.db.sql("""
        SELECT
            'Purchase Return' AS document,
            pi.name AS id,
            CASE
                WHEN pi.outstanding_amount = 0 THEN 'Paid'
                WHEN pi.outstanding_amount = pi.grand_total THEN 'Unpaid'
                ELSE 'Partially Paid'
            END AS status,
            pi.grand_total AS invoice_total,
            IFNULL(SUM(
                CASE WHEN pe.docstatus=1 THEN per.allocated_amount ELSE 0 END
            ),0) AS amount
        FROM `tabPurchase Invoice` pi
        LEFT JOIN `tabPayment Entry Reference` per
            ON per.reference_name=pi.name AND per.reference_doctype='Purchase Invoice'
        LEFT JOIN `tabPayment Entry` pe
            ON pe.name = per.parent
        WHERE pi.docstatus=1 AND pi.is_return=1
              AND pi.posting_date = %(date)s
              AND (%(cost_center)s IS NULL OR pi.cost_center = %(cost_center)s)
        GROUP BY pi.name
        ORDER BY pi.posting_date ASC
    """, {"date": date, "cost_center": cost_center}, as_dict=True)


def get_customer_receipts(date, cost_center):
    return frappe.db.sql("""
        SELECT
            'Payment Entry' AS document,
            pe.name AS id,
            'Paid' AS status,
            pe.paid_amount AS invoice_total,
            pe.paid_amount AS amount
        FROM `tabPayment Entry` pe
        LEFT JOIN `tabPayment Entry Reference` per
            ON per.parent = pe.name
            AND per.reference_doctype = 'Sales Invoice'
        LEFT JOIN `tabSales Invoice` si
            ON si.name = per.reference_name
        WHERE pe.docstatus = 1
              AND pe.posting_date = %(date)s
              AND pe.party_type = 'Customer'
              AND (
                    per.name IS NULL
                    OR si.posting_date <= pe.posting_date
                  )
              AND (%(cost_center)s IS NULL OR pe.cost_center = %(cost_center)s)
    """, {"date": date, "cost_center": cost_center}, as_dict=True)


def get_supplier_payments(date, cost_center):
    return frappe.db.sql("""
        SELECT
            'Payment Entry' AS document,
            pe.name AS id,
            'Paid' AS status,
            pe.paid_amount AS invoice_total,
            pe.paid_amount AS amount
        FROM `tabPayment Entry` pe
        LEFT JOIN `tabPayment Entry Reference` per
            ON per.parent=pe.name
        WHERE pe.docstatus=1
              AND pe.posting_date=%(date)s
              AND pe.party_type='Supplier'
              AND per.name IS NULL
              AND (%(cost_center)s IS NULL OR pe.cost_center = %(cost_center)s)
    """, {"date": date, "cost_center": cost_center}, as_dict=True)


def get_journal_entries(date, report_type=None, cost_center=None):
    conditions = ""

    if report_type == "Bank Receipts":
        conditions = "acc.account_type='Bank' AND jea.debit>0"

    elif report_type == "Bank Payments":
        conditions = "acc.account_type='Bank' AND jea.credit>0"

    elif report_type == "Cash Receipts":
        conditions = "acc.account_type='Cash' AND jea.debit>0"

    elif report_type == "Cash Payments":
        conditions = "acc.account_type='Cash' AND jea.credit>0"

    else:  # Journal Entry (Only Non Bank/Cash)
        conditions = """
            acc.account_type NOT IN ('Bank','Cash')
            AND (jea.debit > 0 OR jea.credit > 0)
        """

    return frappe.db.sql(f"""
        SELECT
            'Journal Entry' AS document,
            je.name AS id,
            'Posted' AS status,
            (jea.debit + jea.credit) AS invoice_total,
            CASE WHEN jea.debit>0 THEN jea.debit ELSE jea.credit END AS amount
        FROM `tabJournal Entry` je
        INNER JOIN `tabJournal Entry Account` jea
            ON jea.parent=je.name
        INNER JOIN `tabAccount` acc
            ON acc.name=jea.account
        WHERE je.docstatus=1
              AND je.posting_date=%(date)s
              AND {conditions}
              AND (%(cost_center)s IS NULL OR jea.cost_center = %(cost_center)s)
    """, {"date": date, "cost_center": cost_center}, as_dict=True) 
