
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

    filters["company"] = filters.get("company") if filters.get("company") else None
    filters["cost_center"] = filters.get("cost_center") if filters.get("cost_center") else None

    date = filters.get("date")
    type_filter = filters.get("type")
    cost_center = filters.get("cost_center")
    company = filters.get("company")

    types = [
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
        "Cash Balance",
    ]

    if type_filter:
        types = [type_filter]

    result = []
    totals_map = {}

    for t in types:
        paid_rows = []

        if t == "Opening Cash Balance":
            opening = get_opening_cash_balance(date, company, cost_center)
            totals_map[t] = opening
            result.append({
                "type": t,
                "total": opening,
                "invoice_count": "",
                "indent": 0,
                "bold": 1
            })
            continue

        elif t == "Cash Balance":
            continue

        elif t in ["Cash Sales", "Card/Bank Sales", "Credit Sales"]:
            paid_rows = fetch_sales_invoices(t, date, company, cost_center)

        elif t in ["Cash Purchases", "Card/Bank Purchases", "Credit Purchases"]:
            paid_rows = fetch_purchase_invoices(t, date, company, cost_center)

        elif t in ["Cash Sales Return", "Card/Bank Sales Return", "Credit Sales Return"]:
            paid_rows = fetch_sales_returns(t, date, company, cost_center)

        elif t in ["Cash Purchase Return", "Card/Bank Purchase Return", "Credit Purchase Return"]:
            paid_rows = fetch_purchase_returns(t, date, company, cost_center)

        elif t == "Customer Receipts (Cash)":
            paid_rows = get_customer_receipts(date, company, cost_center, cash_only=True)
        elif t == "Customer Receipts":
            paid_rows = get_customer_receipts(date, company, cost_center, cash_only=False)
        elif t == "Supplier Payments (Cash)":
            paid_rows = get_supplier_payments(date, company, cost_center, cash_only=True)
        elif t == "Supplier Payments":
            paid_rows = get_supplier_payments(date, company, cost_center, cash_only=False)
        elif t == "Internal Transfer":
            paid_rows = get_internal_transfers(date, company, cost_center)
        elif t in ["Bank Receipts", "Bank Payments", "Cash Receipts", "Cash Payments", "Journal Entry"]:
            paid_rows = get_journal_entries(date, t, company, cost_center)

        total = sum(r.get("amount", 0) or 0 for r in paid_rows)
        count = len(paid_rows)
        totals_map[t] = total

        result.append({
            "type": t,
            "total": total,
            "invoice_count": count,
            "indent": 0
        })

        for row in paid_rows:
            result.append({
                "type": f"{row.get('voucher_type', row.get('document', ''))} {row.get('voucher_no', row.get('id', ''))}",
                "total": row.get("amount", 0),
                "invoice_count": "",
                "voucher_type": row.get("voucher_type", row.get("document", "")),
                "voucher_no": row.get("voucher_no", row.get("id", "")),
                "indent": 1
            })

    # Cash Balance = GL sum of all Cash-type accounts through end of day.
    # Using GL directly guarantees this equals the next day's Opening Cash Balance.
    cash_balance = get_closing_cash_balance(date, company, cost_center)

    result.append({
        "type": "Cash Balance",
        "total": cash_balance,
        "invoice_count": "",
        "indent": 0,
        "bold": 1
    })

    return result


# ---------------------------------------------------------------------------
# Sales Invoices (is_return = 0)
# ---------------------------------------------------------------------------

def fetch_sales_invoices(t, date, company, cost_center):

    if t == "Cash Sales":
        amount_field = """
            IFNULL(
                CASE
                    WHEN si.is_pos = 1 THEN SUM(sip.amount)
                    ELSE SUM(per.allocated_amount)
                END
            ,0)
        """
        date_condition = """
            AND si.posting_date = %(date)s
            AND (
                (
                    si.is_pos = 0
                    AND pe.posting_date <= si.posting_date
                    AND pe.mode_of_payment IN (
                        SELECT name FROM `tabMode of Payment` WHERE type = 'Cash'
                    )
                )
                OR
                (
                    si.is_pos = 1
                    AND sip.mode_of_payment IN (
                        SELECT name FROM `tabMode of Payment` WHERE type = 'Cash'
                    )
                )
            )
        """

    elif t == "Card/Bank Sales":
        amount_field = """
            IFNULL(
                CASE
                    WHEN si.is_pos = 1 THEN SUM(sip.amount)
                    ELSE SUM(per.allocated_amount)
                END
            ,0)
        """
        date_condition = """
            AND si.posting_date = %(date)s
            AND (
                (
                    si.is_pos = 0
                    AND pe.posting_date = %(date)s
                    AND pe.mode_of_payment IN (
                        SELECT name FROM `tabMode of Payment`
                        WHERE type IN ('Bank','Card')
                    )
                )
                OR
                (
                    si.is_pos = 1
                    AND sip.mode_of_payment IN (
                        SELECT name FROM `tabMode of Payment`
                        WHERE type IN ('Bank','Card')
                    )
                )
            )
        """

    else:  # Credit Sales
        amount_field = "si.grand_total"
        date_condition = """
            AND si.posting_date = %(date)s
            AND si.is_pos = 0
            AND NOT EXISTS (
                SELECT 1
                FROM `tabPayment Entry Reference` per2
                INNER JOIN `tabPayment Entry` pe2
                    ON pe2.name = per2.parent
                WHERE per2.reference_name = si.name
                    AND per2.reference_doctype = 'Sales Invoice'
                    AND pe2.docstatus = 1
                    AND pe2.posting_date = si.posting_date
            )
        """

    query = f"""
        SELECT si.name AS voucher_no,
               {amount_field} AS amount,
               'Sales Invoice' AS voucher_type
        FROM `tabSales Invoice` si
        LEFT JOIN `tabPayment Entry Reference` per
            ON per.reference_name = si.name
            AND per.reference_doctype = 'Sales Invoice'
        LEFT JOIN `tabPayment Entry` pe
            ON pe.name = per.parent
            AND pe.docstatus = 1
        LEFT JOIN `tabSales Invoice Payment` sip
            ON sip.parent = si.name
        WHERE si.docstatus = 1
              AND si.is_return = 0
              {date_condition}
              AND ( %(company)s IS NULL OR %(company)s = '' OR si.company = %(company)s )
              AND ( %(cost_center)s IS NULL OR %(cost_center)s = '' OR si.cost_center = %(cost_center)s )
        GROUP BY si.name
    """
    return frappe.db.sql(query, {"date": date, "company": company, "cost_center": cost_center}, as_dict=True)


# ---------------------------------------------------------------------------
# Sales Returns (is_return = 1) — same MoP split as Sales Invoices
# ---------------------------------------------------------------------------

def fetch_sales_returns(t, date, company, cost_center):
    """
    Cash Sales Return   — POS: SIP cash amount; non-POS: PE allocated_amount with Cash MoP on same day
    Card/Bank Sales Return — same but Bank/Card MoP
    Credit Sales Return — no payment on invoice date → grand_total (outstanding credit)
    """

    if t == "Cash Sales Return":
        # per.allocated_amount and sip.amount are already stored as negative
        # in ERPNext for return/refund documents — no negation needed
        amount_field = """
            IFNULL(
                CASE
                    WHEN si.is_pos = 1 THEN SUM(sip.amount)
                    ELSE SUM(per.allocated_amount)
                END
            ,0)
        """
        date_condition = """
            AND si.posting_date = %(date)s
            AND (
                (
                    si.is_pos = 0
                    AND pe.posting_date <= si.posting_date
                    AND pe.payment_type = 'Pay'
                    AND pe.mode_of_payment IN (
                        SELECT name FROM `tabMode of Payment` WHERE type = 'Cash'
                    )
                )
                OR
                (
                    si.is_pos = 1
                    AND sip.mode_of_payment IN (
                        SELECT name FROM `tabMode of Payment` WHERE type = 'Cash'
                    )
                )
            )
        """

    elif t == "Card/Bank Sales Return":
        amount_field = """
            IFNULL(
                CASE
                    WHEN si.is_pos = 1 THEN SUM(sip.amount)
                    ELSE SUM(per.allocated_amount)
                END
            ,0)
        """
        date_condition = """
            AND si.posting_date = %(date)s
            AND (
                (
                    si.is_pos = 0
                    AND pe.posting_date = %(date)s
                    AND pe.payment_type = 'Pay'
                    AND pe.mode_of_payment IN (
                        SELECT name FROM `tabMode of Payment`
                        WHERE type IN ('Bank','Card')
                    )
                )
                OR
                (
                    si.is_pos = 1
                    AND sip.mode_of_payment IN (
                        SELECT name FROM `tabMode of Payment`
                        WHERE type IN ('Bank','Card')
                    )
                )
            )
        """

    else:  # Credit Sales Return — return with no refund yet
        amount_field = "si.grand_total"
        date_condition = """
            AND si.posting_date = %(date)s
            AND si.is_pos = 0
            AND NOT EXISTS (
                SELECT 1
                FROM `tabPayment Entry Reference` per2
                INNER JOIN `tabPayment Entry` pe2
                    ON pe2.name = per2.parent
                WHERE per2.reference_name = si.name
                    AND per2.reference_doctype = 'Sales Invoice'
                    AND pe2.docstatus = 1
                    AND pe2.posting_date = si.posting_date
            )
        """

    query = f"""
        SELECT si.name AS voucher_no,
               {amount_field} AS amount,
               'Sales Invoice' AS voucher_type
        FROM `tabSales Invoice` si
        LEFT JOIN `tabPayment Entry Reference` per
            ON per.reference_name = si.name
            AND per.reference_doctype = 'Sales Invoice'
        LEFT JOIN `tabPayment Entry` pe
            ON pe.name = per.parent
            AND pe.docstatus = 1
        LEFT JOIN `tabSales Invoice Payment` sip
            ON sip.parent = si.name
        WHERE si.docstatus = 1
              AND si.is_return = 1
              {date_condition}
              AND ( %(company)s IS NULL OR %(company)s = '' OR si.company = %(company)s )
              AND ( %(cost_center)s IS NULL OR %(cost_center)s = '' OR si.cost_center = %(cost_center)s )
        GROUP BY si.name
    """
    return frappe.db.sql(query, {"date": date, "company": company, "cost_center": cost_center}, as_dict=True)


# ---------------------------------------------------------------------------
# Purchase Invoices (is_return = 0)
# ---------------------------------------------------------------------------

def fetch_purchase_invoices(t, date, company, cost_center):

    if t == "Cash Purchases":
        amount_field = "IFNULL(SUM(per.allocated_amount),0)"
        date_condition = """
            AND pi.posting_date = %(date)s
            AND pe.posting_date = %(date)s
            AND pe.mode_of_payment IN (
                SELECT name FROM `tabMode of Payment` WHERE type = 'Cash'
            )
        """

    elif t == "Card/Bank Purchases":
        amount_field = "IFNULL(SUM(per.allocated_amount),0)"
        date_condition = """
            AND pi.posting_date = %(date)s
            AND pe.posting_date = %(date)s
            AND pe.mode_of_payment IN (
                SELECT name FROM `tabMode of Payment` WHERE type IN ('Bank','Card')
            )
        """

    else:  # Credit Purchases
        amount_field = "pi.grand_total"
        date_condition = """
            AND pi.posting_date = %(date)s
            AND NOT EXISTS (
                SELECT 1
                FROM `tabPayment Entry Reference` per2
                INNER JOIN `tabPayment Entry` pe2
                    ON pe2.name = per2.parent
                WHERE per2.reference_name = pi.name
                    AND per2.reference_doctype = 'Purchase Invoice'
                    AND pe2.docstatus = 1
                    AND pe2.posting_date = %(date)s
            )
        """

    query = f"""
        SELECT pi.name AS voucher_no,
               {amount_field} AS amount,
               'Purchase Invoice' AS voucher_type
        FROM `tabPurchase Invoice` pi
        LEFT JOIN `tabPayment Entry Reference` per
            ON per.reference_name = pi.name AND per.reference_doctype = 'Purchase Invoice'
        LEFT JOIN `tabPayment Entry` pe
            ON pe.name = per.parent
            AND pe.docstatus = 1
        WHERE pi.docstatus = 1
              AND pi.is_return = 0
              {date_condition}
              AND ( %(company)s IS NULL OR %(company)s = '' OR pi.company = %(company)s )
              AND ( %(cost_center)s IS NULL OR %(cost_center)s = '' OR pi.cost_center = %(cost_center)s )
        GROUP BY pi.name
    """
    return frappe.db.sql(query, {"date": date, "company": company, "cost_center": cost_center}, as_dict=True)


# ---------------------------------------------------------------------------
# Purchase Returns (is_return = 1) — same MoP split as Purchase Invoices
# ---------------------------------------------------------------------------

def fetch_purchase_returns(t, date, company, cost_center):
    """
    Cash Purchase Return     — PE allocated_amount with Cash MoP on same day (cash back from supplier)
    Card/Bank Purchase Return — same but Bank/Card MoP
    Credit Purchase Return   — no payment on invoice date → grand_total (outstanding debit note)
    """

    if t == "Cash Purchase Return":
        # payment_type='Receive' because the company receives cash back from supplier
        # allocated_amount stays positive — this is cash coming IN
        amount_field = "IFNULL(SUM(per.allocated_amount),0)"
        date_condition = """
            AND pi.posting_date = %(date)s
            AND pe.posting_date = %(date)s
            AND pe.payment_type = 'Receive'
            AND pe.mode_of_payment IN (
                SELECT name FROM `tabMode of Payment` WHERE type = 'Cash'
            )
        """

    elif t == "Card/Bank Purchase Return":
        amount_field = "IFNULL(SUM(per.allocated_amount),0)"
        date_condition = """
            AND pi.posting_date = %(date)s
            AND pe.posting_date = %(date)s
            AND pe.payment_type = 'Receive'
            AND pe.mode_of_payment IN (
                SELECT name FROM `tabMode of Payment` WHERE type IN ('Bank','Card')
            )
        """

    else:  # Credit Purchase Return — debit note with no settlement yet
        amount_field = "pi.grand_total"
        date_condition = """
            AND pi.posting_date = %(date)s
            AND NOT EXISTS (
                SELECT 1
                FROM `tabPayment Entry Reference` per2
                INNER JOIN `tabPayment Entry` pe2
                    ON pe2.name = per2.parent
                WHERE per2.reference_name = pi.name
                    AND per2.reference_doctype = 'Purchase Invoice'
                    AND pe2.docstatus = 1
                    AND pe2.posting_date = %(date)s
            )
        """

    query = f"""
        SELECT pi.name AS voucher_no,
               {amount_field} AS amount,
               'Purchase Invoice' AS voucher_type
        FROM `tabPurchase Invoice` pi
        LEFT JOIN `tabPayment Entry Reference` per
            ON per.reference_name = pi.name AND per.reference_doctype = 'Purchase Invoice'
        LEFT JOIN `tabPayment Entry` pe
            ON pe.name = per.parent
            AND pe.docstatus = 1
        WHERE pi.docstatus = 1
              AND pi.is_return = 1
              {date_condition}
              AND ( %(company)s IS NULL OR %(company)s = '' OR pi.company = %(company)s )
              AND ( %(cost_center)s IS NULL OR %(cost_center)s = '' OR pi.cost_center = %(cost_center)s )
        GROUP BY pi.name
    """
    return frappe.db.sql(query, {"date": date, "company": company, "cost_center": cost_center}, as_dict=True)


# ---------------------------------------------------------------------------
# Customer Receipts & Supplier Payments
# ---------------------------------------------------------------------------

def get_customer_receipts(date, company=None, cost_center=None, cash_only=None):
    if cash_only is True:
        cash_condition = """AND pe.mode_of_payment IN (
                SELECT name FROM `tabMode of Payment` WHERE type = 'Cash'
            )"""
    elif cash_only is False:
        cash_condition = """AND pe.mode_of_payment NOT IN (
                SELECT name FROM `tabMode of Payment` WHERE type = 'Cash'
            )"""
    else:
        cash_condition = ""

    return frappe.db.sql(f"""
        SELECT
            'Payment Entry' AS document,
            pe.name AS id,
            'Paid' AS status,
            pe.paid_amount AS invoice_total,
            pe.paid_amount AS amount
        FROM `tabPayment Entry` pe
        INNER JOIN `tabPayment Entry Reference` per
            ON per.parent = pe.name
            AND per.reference_doctype = 'Sales Invoice'
        INNER JOIN `tabSales Invoice` si
            ON si.name = per.reference_name
        WHERE pe.docstatus = 1
              AND pe.posting_date = %(date)s
              AND pe.party_type = 'Customer'
              AND pe.posting_date != si.posting_date
              {cash_condition}
              AND ( %(company)s IS NULL OR %(company)s = '' OR pe.company = %(company)s )
              AND ( %(cost_center)s IS NULL OR %(cost_center)s = '' OR pe.cost_center = %(cost_center)s )
    """, {
        "date": date,
        "company": company,
        "cost_center": cost_center
    }, as_dict=True)


def get_supplier_payments(date, company, cost_center, cash_only=None):
    if cash_only is True:
        cash_condition = """AND pe.mode_of_payment IN (
                SELECT name FROM `tabMode of Payment` WHERE type = 'Cash'
            )"""
    elif cash_only is False:
        cash_condition = """AND pe.mode_of_payment NOT IN (
                SELECT name FROM `tabMode of Payment` WHERE type = 'Cash'
            )"""
    else:
        cash_condition = ""

    return frappe.db.sql(f"""
        SELECT
            'Payment Entry' AS document,
            pe.name AS id,
            'Paid' AS status,
            pe.paid_amount AS invoice_total,
            pe.paid_amount AS amount
        FROM `tabPayment Entry` pe
        LEFT JOIN `tabPayment Entry Reference` per
            ON per.parent = pe.name
            AND per.reference_doctype = 'Purchase Invoice'
        LEFT JOIN `tabPurchase Invoice` pi
            ON pi.name = per.reference_name
        WHERE pe.docstatus = 1
              AND pe.posting_date = %(date)s
              AND pe.party_type = 'Supplier'
              {cash_condition}
              AND ( %(company)s IS NULL OR %(company)s = '' OR pe.company = %(company)s )
              AND (
                    per.name IS NULL
                    OR pi.posting_date < pe.posting_date
                  )
              AND ( %(cost_center)s IS NULL OR %(cost_center)s = '' OR pe.cost_center = %(cost_center)s )
        GROUP BY pe.name, pe.paid_amount
        ORDER BY pe.posting_date ASC
    """, {
        "date": date,
        "company": company,
        "cost_center": cost_center
    }, as_dict=True)


# ---------------------------------------------------------------------------
# Journal Entries
# ---------------------------------------------------------------------------

def get_journal_entries(date, report_type=None, company=None, cost_center=None):
    if report_type in ("Bank Receipts", "Bank Payments", "Cash Receipts", "Cash Payments"):
        if report_type == "Bank Receipts":
            conditions = "acc.account_type='Bank' AND jea.debit>0"
        elif report_type == "Bank Payments":
            conditions = "acc.account_type='Bank' AND jea.credit>0"
        elif report_type == "Cash Receipts":
            conditions = "acc.account_type='Cash' AND jea.debit>0"
        elif report_type == "Cash Payments":
            conditions = "acc.account_type='Cash' AND jea.credit>0"

        return frappe.db.sql(f"""
            SELECT
                'Journal Entry' AS document,
                je.name AS id,
                'Posted' AS status,
                (jea.debit + jea.credit) AS invoice_total,
                CASE WHEN jea.debit>0 THEN jea.debit ELSE jea.credit END AS amount
            FROM `tabJournal Entry` je
            INNER JOIN `tabJournal Entry Account` jea
                ON jea.parent = je.name
            INNER JOIN `tabAccount` acc
                ON acc.name = jea.account
            WHERE je.docstatus = 1
                  AND je.posting_date = %(date)s
                  AND {conditions}
                  AND (%(company)s IS NULL OR je.company = %(company)s)
                  AND (%(cost_center)s IS NULL OR jea.cost_center = %(cost_center)s)
        """, {"date": date, "company": company, "cost_center": cost_center}, as_dict=True)

    else:
        # Journal Entry → only entries with no Bank/Cash account lines
        return frappe.db.sql("""
            SELECT
                'Journal Entry' AS document,
                je.name AS id,
                'Posted' AS status,
                SUM(jea.debit + jea.credit) AS invoice_total,
                SUM(CASE WHEN jea.debit>0 THEN jea.debit ELSE jea.credit END) AS amount
            FROM `tabJournal Entry` je
            INNER JOIN `tabJournal Entry Account` jea
                ON jea.parent = je.name
            INNER JOIN `tabAccount` acc
                ON acc.name = jea.account
            WHERE je.docstatus = 1
                  AND je.posting_date = %(date)s
                  AND (%(company)s IS NULL OR je.company = %(company)s)
                  AND (%(cost_center)s IS NULL OR jea.cost_center = %(cost_center)s)
            GROUP BY je.name
            HAVING SUM(CASE WHEN acc.account_type IN ('Bank','Cash') THEN 1 ELSE 0 END) = 0
        """, {"date": date, "company": company, "cost_center": cost_center}, as_dict=True)


# ---------------------------------------------------------------------------
# Internal Transfers
# ---------------------------------------------------------------------------

def get_internal_transfers(date, company=None, cost_center=None):
    return frappe.db.sql("""
        SELECT
            'Payment Entry' AS voucher_type,
            pe.name AS voucher_no,
            'Internal Transfer' AS status,
            pe.paid_amount AS amount,
            pe.paid_amount AS invoice_total
        FROM `tabPayment Entry` pe
        WHERE pe.docstatus = 1
              AND pe.payment_type = 'Internal Transfer'
              AND pe.posting_date = %(date)s
              AND ( %(company)s IS NULL OR pe.company = %(company)s )
              AND ( %(cost_center)s IS NULL OR pe.cost_center = %(cost_center)s )
    """, {
        "date": date,
        "company": company,
        "cost_center": cost_center
    }, as_dict=True)


# ---------------------------------------------------------------------------
# Opening Cash Balance & Internal Transfer Cash Net
# ---------------------------------------------------------------------------

def get_opening_cash_balance(date, company=None, cost_center=None):
    result = frappe.db.sql("""
        SELECT IFNULL(SUM(gle.debit - gle.credit), 0) AS balance
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON acc.name = gle.account
        WHERE gle.posting_date < %(date)s
          AND acc.account_type = 'Cash'
          AND gle.is_cancelled = 0
          AND ( %(company)s IS NULL OR %(company)s = '' OR gle.company = %(company)s )
          AND ( %(cost_center)s IS NULL OR %(cost_center)s = '' OR gle.cost_center = %(cost_center)s )
    """, {"date": date, "company": company, "cost_center": cost_center}, as_dict=True)
    return result[0].get("balance", 0) if result else 0


def get_closing_cash_balance(date, company=None, cost_center=None):
    """GL sum of all Cash-type accounts through end of day — always equals next day's Opening."""
    result = frappe.db.sql("""
        SELECT IFNULL(SUM(gle.debit - gle.credit), 0) AS balance
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON acc.name = gle.account
        WHERE gle.posting_date <= %(date)s
          AND acc.account_type = 'Cash'
          AND gle.is_cancelled = 0
          AND ( %(company)s IS NULL OR %(company)s = '' OR gle.company = %(company)s )
          AND ( %(cost_center)s IS NULL OR %(cost_center)s = '' OR gle.cost_center = %(cost_center)s )
    """, {"date": date, "company": company, "cost_center": cost_center}, as_dict=True)
    return result[0].get("balance", 0) if result else 0


def get_internal_transfer_cash_net(date, company=None, cost_center=None):
    """Net cash effect of internal transfers: +inflow (cash received), -outflow (cash sent)."""
    result = frappe.db.sql("""
        SELECT IFNULL(SUM(
            CASE
                WHEN pa_from.account_type = 'Cash' THEN -pe.paid_amount
                WHEN pa_to.account_type   = 'Cash' THEN  pe.paid_amount
                ELSE 0
            END
        ), 0) AS net
        FROM `tabPayment Entry` pe
        LEFT JOIN `tabAccount` pa_from ON pa_from.name = pe.paid_from
        LEFT JOIN `tabAccount` pa_to   ON pa_to.name   = pe.paid_to
        WHERE pe.docstatus = 1
          AND pe.payment_type = 'Internal Transfer'
          AND pe.posting_date = %(date)s
          AND ( %(company)s IS NULL OR pe.company = %(company)s )
          AND ( %(cost_center)s IS NULL OR pe.cost_center = %(cost_center)s )
    """, {"date": date, "company": company, "cost_center": cost_center}, as_dict=True)
    return result[0].get("net", 0) if result else 0
