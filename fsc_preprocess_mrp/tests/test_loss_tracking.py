from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'fsc')
class TestFscLossTracking(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.MO = cls.env['mrp.production']
        cls.LossRec = cls.env['fsc.loss.record']
        Location = cls.env['stock.location']
        cls._production_location = Location.search(
            [('usage', '=', 'production'), ('company_id', '=', cls.env.company.id)], limit=1)
        cls._stock_location = Location.search(
            [('usage', '=', 'internal'), ('company_id', '=', cls.env.company.id)], limit=1)
        cls.uom_kg = cls.env.ref('uom.product_uom_kgm')
        cls.uom_gram = cls.env.ref('uom.product_uom_gram')
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')

        # Preprocess product (semi-finished): raw kg → semi kg, expected 15% loss.
        cls.semi = cls.env['product.product'].create({
            'name': 'FSC Test Semi Veg Cleaned',
            'type': 'consu',
            'is_storable': True,
            'uom_id': cls.uom_kg.id,
            'uom_po_id': cls.uom_kg.id,
            'fsc_product_type': 'semi_finished',
            'fsc_processing_type': 'preprocess',
            'fsc_loss_threshold': 15.0,
        })
        cls.raw_veg = cls.env['product.product'].create({
            'name': 'FSC Test Raw Veg',
            'type': 'consu',
            'is_storable': True,
            'uom_id': cls.uom_kg.id,
            'uom_po_id': cls.uom_kg.id,
            'fsc_product_type': 'raw',
        })
        cls.spice = cls.env['product.product'].create({
            'name': 'FSC Test Spice',
            'type': 'consu',
            'is_storable': True,
            'uom_id': cls.uom_gram.id,
            'uom_po_id': cls.uom_gram.id,
            'fsc_product_type': 'raw',
        })
        # Finished product (not preprocess - should NOT auto-create loss record)
        cls.meal = cls.env['product.product'].create({
            'name': 'FSC Test Meal',
            'type': 'consu',
            'is_storable': True,
            'uom_id': cls.uom_unit.id,
            'uom_po_id': cls.uom_unit.id,
            'fsc_product_type': 'finished',
            'fsc_processing_type': 'cooking',
        })

        cls.bom_semi = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.semi.product_tmpl_id.id,
            'product_qty': 1.0,
            'product_uom_id': cls.uom_kg.id,
            'type': 'normal',
            'fsc_expected_loss': 15.0,
            'bom_line_ids': [(0, 0, {
                'product_id': cls.raw_veg.id,
                'product_qty': 1.18,
                'product_uom_id': cls.uom_kg.id,
            })],
        })

    def _make_done_mo(self, product, qty_produced=100.0, raw_consumed=120.0,
                      bom=None, raw_product=None, raw_uom=None):
        raw_product = raw_product or self.raw_veg
        raw_uom = raw_uom or self.uom_kg
        mo = self.MO.create({
            'product_id': product.id,
            'product_qty': qty_produced,
            'product_uom_id': product.uom_id.id,
            'bom_id': bom.id if bom else False,
        })
        # Inject a raw move directly so we can simulate the consumed quantity
        # without running the full procurement / reservation flow.
        self.env['stock.move'].create({
            'name': 'FSC test raw',
            'product_id': raw_product.id,
            'product_uom': raw_uom.id,
            'product_uom_qty': raw_consumed,
            'quantity': raw_consumed,
            'location_id': self._stock_location.id,
            'location_dest_id': self._production_location.id,
            'raw_material_production_id': mo.id,
            'company_id': self.env.company.id,
        })
        # Inject a finished move so the computed qty_produced lands on the MO.
        self.env['stock.move'].create({
            'name': 'FSC test finished',
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'product_uom_qty': qty_produced,
            'quantity': qty_produced,
            'picked': True,
            'state': 'done',
            'location_id': self._production_location.id,
            'location_dest_id': self._stock_location.id,
            'production_id': mo.id,
            'company_id': self.env.company.id,
        })
        mo.write({'state': 'done', 'qty_producing': qty_produced})
        mo.invalidate_recordset(['qty_produced'])
        return mo

    def test_compute_input_qty_same_uom(self):
        mo = self._make_done_mo(self.semi, raw_consumed=120.0)
        self.assertEqual(mo._fsc_compute_input_qty(), 120.0)

    def test_compute_input_qty_skips_different_category(self):
        mo = self._make_done_mo(self.semi, raw_consumed=100.0)
        # Add a spice move in gram (different category from kg)
        self.env['stock.move'].create({
            'name': 'FSC test spice',
            'product_id': self.spice.id,
            'product_uom': self.uom_gram.id,
            'product_uom_qty': 50.0,
            'quantity': 50.0,
            'location_id': self._stock_location.id,
            'location_dest_id': self._production_location.id,
            'raw_material_production_id': mo.id,
            'company_id': self.env.company.id,
        })
        # Total should be 100 kg veg (spice ignored, different UoM category)
        self.assertEqual(mo._fsc_compute_input_qty(), 100.0)

    def test_auto_record_on_done_within_threshold(self):
        # 117.6 kg in, 100 kg out → loss = 17.6/117.6 ≈ 14.97% < 15% threshold.
        mo = self._make_done_mo(self.semi, qty_produced=100.0,
                                raw_consumed=117.6, bom=self.bom_semi)
        record = mo._fsc_record_loss_on_done()
        self.assertTrue(record)
        self.assertEqual(record.production_id, mo)
        self.assertEqual(record.input_qty, 117.6)
        self.assertEqual(record.output_qty, 100.0)
        self.assertAlmostEqual(record.loss_pct, 14.966, places=2)
        self.assertFalse(record.over_threshold)
        self.assertFalse(record.alerted)
        self.assertTrue(record.fsc_auto)

    def test_auto_record_on_done_over_threshold(self):
        # 130 kg in, 100 kg out → loss = 30/130 ≈ 23.08% > 15%.
        mo = self._make_done_mo(self.semi, qty_produced=100.0,
                                raw_consumed=130.0, bom=self.bom_semi)
        record = mo._fsc_record_loss_on_done()
        self.assertTrue(record.over_threshold)
        self.assertTrue(record.alerted, 'Should have sent an alert')
        # Alert posted to MO chatter
        messages = mo.message_ids.filtered(
            lambda m: 'Loss alert' in (m.body or ''))
        self.assertTrue(messages, 'Alert message should appear on MO chatter')

    def test_record_idempotent(self):
        mo = self._make_done_mo(self.semi, qty_produced=100.0,
                                raw_consumed=120.0, bom=self.bom_semi)
        r1 = mo._fsc_record_loss_on_done()
        r2 = mo._fsc_record_loss_on_done()
        self.assertEqual(r1, r2, 'Second call must return the same record, not create another')
        self.assertEqual(len(mo.fsc_loss_record_ids.filtered('fsc_auto')), 1)

    def test_non_preprocess_product_skipped(self):
        mo = self._make_done_mo(self.meal, qty_produced=50.0, raw_consumed=60.0)
        result = mo._fsc_record_loss_on_done()
        self.assertFalse(result)
        self.assertFalse(mo.fsc_loss_record_ids)

    def test_record_uses_bom_threshold_when_present(self):
        # BOM threshold is 15. Force a product threshold of 5 to confirm BOM wins.
        self.semi.product_tmpl_id.fsc_loss_threshold = 5.0
        mo = self._make_done_mo(self.semi, qty_produced=100.0,
                                raw_consumed=110.0, bom=self.bom_semi)
        record = mo._fsc_record_loss_on_done()
        self.assertEqual(record.threshold_pct, 15.0)

    def test_record_uses_product_threshold_when_no_bom(self):
        mo = self._make_done_mo(self.semi, qty_produced=100.0,
                                raw_consumed=110.0, bom=None)
        record = mo._fsc_record_loss_on_done()
        self.assertEqual(record.threshold_pct, 15.0)

    def test_alert_idempotent(self):
        mo = self._make_done_mo(self.semi, qty_produced=100.0,
                                raw_consumed=130.0, bom=self.bom_semi)
        record = mo._fsc_record_loss_on_done()
        self.assertTrue(record.alerted)
        msg_count = len(mo.message_ids.filtered(lambda m: 'Loss alert' in (m.body or '')))
        record._fsc_send_alert()
        msg_count2 = len(mo.message_ids.filtered(lambda m: 'Loss alert' in (m.body or '')))
        self.assertEqual(msg_count, msg_count2, 'Second alert call must not post again')

    def test_total_loss_pct_aggregates(self):
        mo = self._make_done_mo(self.semi, qty_produced=100.0,
                                raw_consumed=120.0, bom=self.bom_semi)
        mo._fsc_record_loss_on_done()
        # Manually add a second stage record.
        self.LossRec.create({
            'production_id': mo.id,
            'stage': 'cutting',
            'input_qty': 50.0,
            'output_qty': 45.0,
            'threshold_pct': 0.0,
        })
        # Aggregate: input 120+50=170, loss 20+5=25, pct = 25/170 ≈ 14.7%
        mo.invalidate_recordset(['fsc_total_loss_pct'])
        self.assertAlmostEqual(mo.fsc_total_loss_pct, 14.70, places=1)
