# apps/hatco_ext/hatco_ext/tests/test_cost_center.py
"""Tests for the Cost Center auto-fill hook.

Run:
    bench --site hatco run-tests --app hatco_ext --module hatco_ext.tests.test_cost_center
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from hatco_ext.cost_center import set_missing_cost_center


class _Row(frappe._dict):
	"""Minimal stand-in for a child doc: needs .get() and .meta.get_field()."""

	def __init__(self, has_cost_center=True, **kwargs):
		super().__init__(**kwargs)
		self.meta = frappe._dict(
			get_field=lambda fieldname: True if (fieldname == "cost_center" and has_cost_center) else None
		)


class _Doc(frappe._dict):
	"""Minimal stand-in for a parent doc with items/taxes tables."""

	def __init__(self, tables=("items", "taxes"), **kwargs):
		super().__init__(**kwargs)
		self.meta = frappe._dict(get_field=lambda fieldname: True if fieldname in tables else None)


class TestCostCenterAutofill(FrappeTestCase):
	def test_blank_tax_rows_get_parent_cost_center(self):
		doc = _Doc(
			cost_center="Hafer Al Batin - H",
			items=[_Row(cost_center="Hafer Al Batin - H")],
			taxes=[_Row(cost_center=""), _Row(cost_center=None)],
		)

		set_missing_cost_center(doc)

		self.assertEqual([t.cost_center for t in doc.taxes], ["Hafer Al Batin - H"] * 2)

	def test_row_set_by_user_is_not_overwritten(self):
		doc = _Doc(
			cost_center="Hafer Al Batin - H",
			items=[_Row(cost_center="Dawadmi - H")],
			taxes=[_Row(cost_center="Riyadh PS - H")],
		)

		set_missing_cost_center(doc)

		self.assertEqual(doc.items[0].cost_center, "Dawadmi - H")
		self.assertEqual(doc.taxes[0].cost_center, "Riyadh PS - H")

	def test_no_parent_cost_center_is_a_noop(self):
		doc = _Doc(cost_center="", items=[_Row(cost_center="")], taxes=[_Row(cost_center="")])

		set_missing_cost_center(doc)

		self.assertEqual(doc.taxes[0].cost_center, "")

	def test_child_without_cost_center_field_is_skipped(self):
		doc = _Doc(
			cost_center="Hafer Al Batin - H",
			items=[],
			taxes=[_Row(has_cost_center=False)],
		)

		set_missing_cost_center(doc)

		self.assertIsNone(doc.taxes[0].get("cost_center"))

	def test_is_idempotent_across_before_validate_and_validate(self):
		doc = _Doc(cost_center="Hafer Al Batin - H", items=[], taxes=[_Row(cost_center="")])

		set_missing_cost_center(doc, "before_validate")
		doc.taxes.append(_Row(cost_center=""))  # ERPNext appends from the tax template
		set_missing_cost_center(doc, "validate")

		self.assertEqual([t.cost_center for t in doc.taxes], ["Hafer Al Batin - H"] * 2)


class TestPurchaseInvoiceCostCenter(FrappeTestCase):
	"""End-to-end check against a real Purchase Invoice with a tax template."""

	def test_tax_row_from_template_gets_cost_center_on_save(self):
		company = frappe.db.get_value("Company", {"name": ("like", "%")}, "name")
		cost_center = frappe.db.get_value("Cost Center", {"company": company, "is_group": 0}, "name")
		template = frappe.db.get_value("Purchase Taxes and Charges Template", {"company": company}, "name")
		supplier = frappe.db.get_value("Supplier", {}, "name")
		item = frappe.db.get_value("Item", {"is_stock_item": 0}, "name") or frappe.db.get_value("Item", {}, "name")

		if not all([company, cost_center, template, supplier, item]):
			self.skipTest("site has no company/cost center/tax template/supplier/item to test with")

		pi = frappe.get_doc(
			{
				"doctype": "Purchase Invoice",
				"company": company,
				"supplier": supplier,
				"cost_center": cost_center,
				"taxes_and_charges": template,
				"update_stock": 0,
				"items": [{"item_code": item, "qty": 1, "rate": 100}],
			}
		)
		pi.insert(ignore_permissions=True)

		self.assertTrue(pi.taxes, "tax template produced no rows — nothing to assert")
		for tax in pi.taxes:
			self.assertEqual(tax.cost_center, cost_center)
		for row in pi.items:
			self.assertEqual(row.cost_center, cost_center)
