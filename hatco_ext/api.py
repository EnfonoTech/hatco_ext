import frappe


@frappe.whitelist()
def get_price_history(item_code, company=None, cost_center=None):
    conditions = ""
    if company:
        conditions += " AND si.company = %(company)s"
    if cost_center:
        conditions += " AND sii.cost_center = %(cost_center)s"

    return frappe.db.sql(f"""
        SELECT
            sii.item_code,
            sii.item_name,
            si.customer,
            sii.rate AS sales_rate,
            sii.qty AS sales_qty,
            si.name AS sales_invoice,
            si.posting_date AS date
        FROM
            `tabSales Invoice Item` sii
            JOIN `tabSales Invoice` si ON si.name = sii.parent
        WHERE
            sii.item_code = %(item_code)s
            AND si.docstatus = 1
            {conditions}
        ORDER BY
            si.posting_date DESC
        LIMIT 30
    """, {"item_code": item_code, "company": company, "cost_center": cost_center}, as_dict=True)


@frappe.whitelist()
def get_purchase_history(item_code, company=None, cost_center=None):
    conditions = ""
    if company:
        conditions += " AND pi.company = %(company)s"
    if cost_center:
        conditions += " AND pii.cost_center = %(cost_center)s"

    return frappe.db.sql(f"""
        SELECT
            pii.item_name,
            pi.supplier,
            pii.rate AS purchase_rate,
            pii.qty AS purchase_qty,
            pi.name AS purchase_invoice,
            pi.posting_date AS date
        FROM
            `tabPurchase Invoice Item` pii
            JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
        WHERE
            pii.item_code = %(item_code)s
            AND pi.docstatus = 1
            {conditions}
        ORDER BY
            pi.posting_date DESC
        LIMIT 30
    """, {"item_code": item_code, "company": company, "cost_center": cost_center}, as_dict=True)
