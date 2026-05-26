from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'fsc')
class TestFscMealCosting(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.MO = cls.env['mrp.production']
        cls.MealCost = cls.env['fsc.meal.cost']
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.uom_kg = cls.env.ref('uom.product_uom_kgm')

        Location = cls.env['stock.location']
        cls._production_loc = Location.search(
            [('usage', '=', 'production'), ('company_id', '=', cls.env.company.id)], limit=1)
        cls._stock_loc = Location.search(
            [('usage', '=', 'internal'), ('company_id', '=', cls.env.company.id)], limit=1)

        cls.semi_veg = cls.env['product.product'].create({
            'name': 'FSC Cost Test Semi Veg',
            'type': 'consu',
            'is_storable': True,
            'uom_id': cls.uom_kg.id,
            'uom_po_id': cls.uom_kg.id,
            'fsc_product_type': 'semi_finished',
            'standard_price': 50.0,
        })
        cls.protein = cls.env['product.product'].create({
            'name': 'FSC Cost Test Protein',
            'type': 'consu',
            'is_storable': True,
            'uom_id': cls.uom_kg.id,
            'uom_po_id': cls.uom_kg.id,
            'fsc_product_type': 'semi_finished',
            'standard_price': 200.0,
        })
        cls.meal = cls.env['product.product'].create({
            'name': 'FSC Cost Test Meal',
            'type': 'consu',
            'is_storable': True,
            'uom_id': cls.uom_unit.id,
            'uom_po_id': cls.uom_unit.id,
            'fsc_product_type': 'finished',
            'fsc_processing_type': 'cooking',
        })
        cls.raw_for_preprocess = cls.env['product.product'].create({
            'name': 'FSC Cost Test Raw For Preprocess',
            'type': 'consu',
            'is_storable': True,
            'uom_id': cls.uom_kg.id,
            'uom_po_id': cls.uom_kg.id,
            'fsc_product_type': 'semi_finished',  # NOT finished
        })

        cls.bom_meal = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.meal.product_tmpl_id.id,
            'product_qty': 1.0,
            'product_uom_id': cls.uom_unit.id,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {
                    'product_id': cls.semi_veg.id,
                    'product_qty': 0.2,
                    'product_uom_id': cls.uom_kg.id,
                }),
                (0, 0, {
                    'product_id': cls.protein.id,
                    'product_qty': 0.15,
                    'product_uom_id': cls.uom_kg.id,
                }),
            ],
        })

    def _make_cooking_mo(self, product_qty=100.0, qty_produced=100.0,
                        veg_consumed=22.0, protein_consumed=16.0):
        mo = self.MO.create({
            'product_id': self.meal.id,
            'product_qty': product_qty,
            'product_uom_id': self.meal.uom_id.id,
            'bom_id': self.bom_meal.id,
        })
        self.env['stock.move'].create({
            'name': 'Veg',
            'product_id': self.semi_veg.id,
            'product_uom': self.uom_kg.id,
            'product_uom_qty': veg_consumed,
            'quantity': veg_consumed,
            'state': 'done',
            'picked': True,
            'location_id': self._stock_loc.id,
            'location_dest_id': self._production_loc.id,
            'raw_material_production_id': mo.id,
            'company_id': self.env.company.id,
        })
        self.env['stock.move'].create({
            'name': 'Protein',
            'product_id': self.protein.id,
            'product_uom': self.uom_kg.id,
            'product_uom_qty': protein_consumed,
            'quantity': protein_consumed,
            'state': 'done',
            'picked': True,
            'location_id': self._stock_loc.id,
            'location_dest_id': self._production_loc.id,
            'raw_material_production_id': mo.id,
            'company_id': self.env.company.id,
        })
        self.env['stock.move'].create({
            'name': 'Finished',
            'product_id': self.meal.id,
            'product_uom': self.meal.uom_id.id,
            'product_uom_qty': qty_produced,
            'quantity': qty_produced,
            'picked': True,
            'state': 'done',
            'location_id': self._production_loc.id,
            'location_dest_id': self._stock_loc.id,
            'production_id': mo.id,
            'company_id': self.env.company.id,
        })
        mo.write({'state': 'done'})
        mo.invalidate_recordset(['qty_produced'])
        return mo

    def test_planned_cost_computed_from_bom(self):
        mo = self._make_cooking_mo(product_qty=100.0)
        planned = mo._fsc_compute_planned_cost()
        # 100 meals × (0.2 kg veg × 50 + 0.15 kg protein × 200) = 100 × (10 + 30) = 4000
        self.assertEqual(planned, 4000.0)

    def test_actual_cost_computed_from_moves(self):
        mo = self._make_cooking_mo(product_qty=100.0,
                                   veg_consumed=22.0,  # +10% over plan
                                   protein_consumed=16.0)  # +6.7% over plan
        actual = mo._fsc_compute_actual_raw_cost()
        # 22 × 50 + 16 × 200 = 1100 + 3200 = 4300
        self.assertEqual(actual, 4300.0)

    def test_meal_cost_record_on_done(self):
        mo = self._make_cooking_mo(product_qty=100.0,
                                   qty_produced=100.0,
                                   veg_consumed=22.0,
                                   protein_consumed=16.0)
        record = mo._fsc_record_meal_cost()
        self.assertTrue(record)
        self.assertEqual(record.production_id, mo)
        self.assertEqual(record.meal_qty, 100.0)
        self.assertEqual(record.raw_cost, 4300.0)
        self.assertEqual(record.planned_cost_total, 4000.0)
        self.assertEqual(record.actual_cost_total, 4300.0)
        self.assertEqual(record.variance, 300.0)
        self.assertAlmostEqual(record.variance_pct, 7.5, places=2)
        self.assertEqual(record.cost_per_meal_planned, 40.0)
        self.assertEqual(record.cost_per_meal_actual, 43.0)
        self.assertTrue(record.fsc_auto)

    def test_record_idempotent(self):
        mo = self._make_cooking_mo()
        r1 = mo._fsc_record_meal_cost()
        r2 = mo._fsc_record_meal_cost()
        self.assertEqual(r1, r2)
        self.assertEqual(len(mo.fsc_meal_cost_ids.filtered('fsc_auto')), 1)

    def test_non_finished_product_skipped(self):
        # Create a MO for a semi-finished product (preprocess output) — no meal cost expected.
        mo = self.MO.create({
            'product_id': self.raw_for_preprocess.id,
            'product_qty': 50.0,
            'product_uom_id': self.raw_for_preprocess.uom_id.id,
        })
        mo.write({'state': 'done'})
        result = mo._fsc_record_meal_cost()
        self.assertFalse(result)
        self.assertFalse(mo.fsc_meal_cost_ids)

    def test_planned_cost_zero_without_bom(self):
        mo = self.MO.create({
            'product_id': self.meal.id,
            'product_qty': 100.0,
            'product_uom_id': self.meal.uom_id.id,
            'bom_id': False,
        })
        self.assertEqual(mo._fsc_compute_planned_cost(), 0.0)

    def test_planned_cost_scales_with_mo_qty(self):
        # BOM produces 1, so for product_qty=250 should scale ×250.
        mo = self._make_cooking_mo(product_qty=250.0)
        planned = mo._fsc_compute_planned_cost()
        self.assertEqual(planned, 10000.0)

    def test_variance_computation(self):
        # Higher actual than planned → positive variance.
        mo = self._make_cooking_mo(product_qty=100.0,
                                   veg_consumed=30.0,    # +50% over plan
                                   protein_consumed=20.0)  # +33% over plan
        record = mo._fsc_record_meal_cost()
        # planned=4000, actual = 30×50 + 20×200 = 1500+4000 = 5500
        self.assertEqual(record.planned_cost_total, 4000.0)
        self.assertEqual(record.actual_cost_total, 5500.0)
        self.assertEqual(record.variance, 1500.0)
        self.assertAlmostEqual(record.variance_pct, 37.5, places=2)
