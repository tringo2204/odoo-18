from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'fsc')
class TestFscProcurementEngine(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Line = cls.env['fsc.consolidation.line']
        cls.PO = cls.env['purchase.order']
        cls.uom_kg = cls.env.ref('uom.product_uom_kgm')

        cls.vendor_a = cls.env['res.partner'].create({
            'name': 'FSC Test Vendor A',
            'supplier_rank': 1,
        })
        cls.vendor_b = cls.env['res.partner'].create({
            'name': 'FSC Test Vendor B',
            'supplier_rank': 1,
        })

        cls.product_with_vendor = cls.env['product.product'].create({
            'name': 'FSC Test Raw With Vendor',
            'type': 'consu',
            'is_storable': True,
            'uom_id': cls.uom_kg.id,
            'uom_po_id': cls.uom_kg.id,
            'fsc_product_type': 'raw',
            'seller_ids': [(0, 0, {
                'partner_id': cls.vendor_a.id,
                'price': 10.0,
                'min_qty': 0.0,
                'product_uom': cls.uom_kg.id,
            })],
        })
        cls.product_other_vendor = cls.env['product.product'].create({
            'name': 'FSC Test Raw Other Vendor',
            'type': 'consu',
            'is_storable': True,
            'uom_id': cls.uom_kg.id,
            'uom_po_id': cls.uom_kg.id,
            'fsc_product_type': 'raw',
            'seller_ids': [(0, 0, {
                'partner_id': cls.vendor_b.id,
                'price': 20.0,
                'min_qty': 0.0,
                'product_uom': cls.uom_kg.id,
            })],
        })
        cls.product_no_vendor = cls.env['product.product'].create({
            'name': 'FSC Test Raw No Vendor',
            'type': 'consu',
            'is_storable': True,
            'uom_id': cls.uom_kg.id,
            'uom_po_id': cls.uom_kg.id,
            'fsc_product_type': 'raw',
        })

    def _open_line(self, product, qty=10.0, required_date=None):
        line = self.Line.create({
            'product_id': product.id,
            'uom_id': self.uom_kg.id,
            'total_qty': qty,
            'required_date': required_date or fields.Datetime.now(),
            'state': 'open',
        })
        return line

    def test_buy_decision_created(self):
        line = self._open_line(self.product_with_vendor, qty=10.0)
        line.action_generate_procurement()
        decisions = self.env['fsc.make.buy.decision'].search(
            [('consolidation_line_id', '=', line.id)])
        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions.decision, 'buy')
        self.assertEqual(decisions.chosen_vendor_id, self.vendor_a)
        self.assertEqual(decisions.cost_buy, 100.0)

    def test_rfq_created_with_vendor_and_line(self):
        line = self._open_line(self.product_with_vendor, qty=10.0)
        line.action_generate_procurement()
        self.assertEqual(line.state, 'rfq_created')
        po = line.purchase_order_id
        self.assertTrue(po, 'PO should be linked to consolidation line')
        self.assertEqual(po.partner_id, self.vendor_a)
        self.assertEqual(po.state, 'draft')
        self.assertEqual(len(po.order_line), 1)
        pol = po.order_line
        self.assertEqual(pol.product_id, self.product_with_vendor)
        self.assertEqual(pol.product_qty, 10.0)
        self.assertEqual(pol.price_unit, 10.0)

    def test_same_vendor_lines_share_one_po(self):
        line1 = self._open_line(self.product_with_vendor, qty=10.0)
        line2 = self._open_line(self.product_with_vendor, qty=5.0)
        (line1 | line2).action_generate_procurement()
        self.assertEqual(line1.purchase_order_id, line2.purchase_order_id,
                         'Both lines for same vendor should share one PO')
        self.assertEqual(len(line1.purchase_order_id.order_line), 2)

    def test_different_vendors_produce_separate_pos(self):
        line1 = self._open_line(self.product_with_vendor, qty=10.0)
        line2 = self._open_line(self.product_other_vendor, qty=5.0)
        (line1 | line2).action_generate_procurement()
        self.assertNotEqual(line1.purchase_order_id, line2.purchase_order_id)
        self.assertEqual(line1.purchase_order_id.partner_id, self.vendor_a)
        self.assertEqual(line2.purchase_order_id.partner_id, self.vendor_b)

    def test_no_vendor_raises(self):
        line = self._open_line(self.product_no_vendor, qty=10.0)
        with self.assertRaises(UserError):
            line.action_generate_procurement()
        self.assertEqual(line.state, 'open', 'State must stay open on failure')
        self.assertFalse(line.purchase_order_id)

    def test_non_open_lines_skipped(self):
        line = self._open_line(self.product_with_vendor, qty=10.0)
        line.write({'state': 'draft'})
        result = line.action_generate_procurement()
        self.assertFalse(result)
        self.assertFalse(line.purchase_order_id)

    def test_cron_processes_open_lines(self):
        line_ok = self._open_line(self.product_with_vendor, qty=10.0)
        line_bad = self._open_line(self.product_no_vendor, qty=5.0)
        processed = self.Line._cron_process_open_lines()
        # Good line succeeds, bad line raises and is skipped (no crash).
        self.assertEqual(line_ok.state, 'rfq_created')
        self.assertEqual(line_bad.state, 'open')
        self.assertEqual(processed, 1)

    def test_po_origin_concatenated(self):
        line1 = self._open_line(self.product_with_vendor, qty=10.0)
        line2 = self._open_line(self.product_with_vendor, qty=5.0)
        (line1 | line2).action_generate_procurement()
        po = line1.purchase_order_id
        self.assertIn(line1.name, po.origin)
        self.assertIn(line2.name, po.origin)

    def test_existing_draft_po_is_reused(self):
        # First batch creates PO.
        line1 = self._open_line(self.product_with_vendor, qty=10.0)
        line1.action_generate_procurement()
        po1 = line1.purchase_order_id

        # Second batch for same vendor should reuse the same draft PO.
        line2 = self._open_line(self.product_with_vendor, qty=5.0)
        line2.action_generate_procurement()
        self.assertEqual(line2.purchase_order_id, po1,
                         'Same-vendor draft PO should be reused')
        self.assertEqual(len(po1.order_line), 2)
