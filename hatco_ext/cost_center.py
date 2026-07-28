# apps/hatco_ext/hatco_ext/cost_center.py
"""Keep child-row Cost Centers in sync with the parent transaction.

Why this exists
---------------
ERPNext appends tax rows from the Taxes and Charges Template *programmatically*
(`erpnext/controllers/accounts_controller.py::append_taxes_from_master`, which
just extends `taxes` with the template rows verbatim). Two consequences:

1. The client-side `taxes_add` grid event never fires for those rows, so the
   Cost Center auto-fill in `public/js/*.js` never touches them.
2. Hatco's tax templates carry a blank `cost_center`, and both companies have no
   Default Cost Center, so the `:Company` default on
   `Purchase/Sales Taxes and Charges.cost_center` resolves to blank too.

Result: the tax row saves and submits with an empty Cost Center, and the VAT GL
Entry posts with no Cost Center (verified on hatco: 37 Purchase Invoice tax rows,
including HF-PI-26-000931). It only looked "fixed" afterwards because the old
client-side `onload` hack silently re-stamped the rows on reopen — which is also
what marked a freshly-opened document as "Not Saved" and surfaced Update.

This module does the stamping server-side, on every save, before GL is written.
"""

import frappe

CHILD_TABLES = ("items", "taxes")

BACKFILL_TARGETS = (
	("Sales Invoice", "Sales Taxes and Charges", "Sales Invoice Item"),
	("Purchase Invoice", "Purchase Taxes and Charges", "Purchase Invoice Item"),
	("Sales Order", "Sales Taxes and Charges", "Sales Order Item"),
	("Purchase Order", "Purchase Taxes and Charges", "Purchase Order Item"),
	("Delivery Note", "Sales Taxes and Charges", "Delivery Note Item"),
	("Purchase Receipt", "Purchase Taxes and Charges", "Purchase Receipt Item"),
)


def set_missing_cost_center(doc, method=None):
	"""Copy the parent Cost Center into item/tax rows that have none.

	Registered on both `before_validate` and `validate` in hooks.py: rows can be
	appended *during* the controller's own validate (`set_missing_values` ->
	`set_taxes`), so a single pass before validate is not enough. The function is
	idempotent — it only ever fills blanks, never overwrites a row the user set.
	"""
	parent_cc = doc.get("cost_center")
	if not parent_cc:
		return

	for table in CHILD_TABLES:
		if not doc.meta.get_field(table):
			continue

		for row in doc.get(table) or []:
			if not row.meta.get_field("cost_center"):
				break
			if not row.get("cost_center"):
				row.cost_center = parent_cc


def _blank_cost_center_rows(parent_dt, child_dt):
	"""Child rows with no Cost Center whose parent has one (docstatus 0 or 1)."""
	child = frappe.qb.DocType(child_dt)
	parent = frappe.qb.DocType(parent_dt)

	return (
		frappe.qb.from_(child)
		.inner_join(parent)
		.on(parent.name == child.parent)
		.select(child.name, child.parent, parent.cost_center)
		.where(
			(child.parenttype == parent_dt)
			& ((child.cost_center.isnull()) | (child.cost_center == ""))
			& (parent.cost_center.isnotnull())
			& (parent.cost_center != "")
			& (parent.docstatus < 2)
		)
		.orderby(child.parent)
		.run(as_dict=True)
	)


def backfill_blank_cost_centers(dry_run=True, limit=None):
	"""Fill blank child-row Cost Centers on existing documents.

	Not wired into patches.txt on purpose — run it deliberately from the bench
	console after taking a backup:

	    bench --site hatco console
	    >>> from hatco_ext.cost_center import backfill_blank_cost_centers
	    >>> backfill_blank_cost_centers(dry_run=True)          # report only
	    >>> backfill_blank_cost_centers(dry_run=False); frappe.db.commit()

	Only the child rows are touched. GL Entries already posted with a blank Cost
	Center are NOT repaired here — those need a Repost Accounting Ledger (or a
	cancel/amend) per voucher, which is a separate, reviewed operation.
	"""
	summary = {}

	for parent_dt, tax_dt, item_dt in BACKFILL_TARGETS:
		for child_dt in (tax_dt, item_dt):
			rows = _blank_cost_center_rows(parent_dt, child_dt)
			if limit:
				rows = rows[:limit]

			summary[f"{parent_dt} / {child_dt}"] = len(rows)

			if dry_run or not rows:
				continue

			for row in rows:
				frappe.db.set_value(
					child_dt, row.name, "cost_center", row.cost_center, update_modified=False
				)

	for key, count in summary.items():
		print(f"{key}: {count} row(s){' (dry run)' if dry_run else ' updated'}")

	return summary
