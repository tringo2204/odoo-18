from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'fsc')
class TestFscKitchenMrp(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.MO = cls.env['mrp.production']
        cls.Batch = cls.env['fsc.cooking.batch']
        cls.Line = cls.env['fsc.consolidation.line']
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.uom_kg = cls.env.ref('uom.product_uom_kgm')

        Location = cls.env['stock.location']
        cls._production_loc = Location.search(
            [('usage', '=', 'production'), ('company_id', '=', cls.env.company.id)], limit=1)
        cls._stock_loc = Location.search(
            [('usage', '=', 'internal'), ('company_id', '=', cls.env.company.id)], limit=1)
        cls.kitchen_loc = Location.create({
            'name': 'FSC Test Kitchen',
            'usage': 'internal',
            'location_id': cls._stock_loc.location_id.id or cls._stock_loc.id,
        })

        # Finished cooking product
        cls.meal = cls.env['product.product'].create({
            'name': 'FSC Test Meal',
            'type': 'consu',
            'is_storable': True,
            'uom_id': cls.uom_unit.id,
            'uom_po_id': cls.uom_unit.id,
            'fsc_product_type': 'finished',
            'fsc_processing_type': 'cooking',
        })
        # Semi raw used as component
        cls.semi_veg = cls.env['product.product'].create({
            'name': 'FSC Test Semi Veg',
            'type': 'consu',
            'is_storable': True,
            'uom_id': cls.uom_kg.id,
            'uom_po_id': cls.uom_kg.id,
            'fsc_product_type': 'semi_finished',
        })
        # Non-cooking product (preprocess) — should NOT auto-create batch
        cls.semi_other = cls.env['product.product'].create({
            'name': 'FSC Test Other Semi',
            'type': 'consu',
            'is_storable': True,
            'uom_id': cls.uom_kg.id,
            'uom_po_id': cls.uom_kg.id,
            'fsc_product_type': 'semi_finished',
            'fsc_processing_type': 'preprocess',
        })

        cls.bom_meal = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.meal.product_tmpl_id.id,
            'product_qty': 1.0,
            'product_uom_id': cls.uom_unit.id,
            'type': 'normal',
            'bom_line_ids': [(0, 0, {
                'product_id': cls.semi_veg.id,
                'product_qty': 0.2,
                'product_uom_id': cls.uom_kg.id,
            })],
        })

    def _create_cooking_mo(self, product_qty=100.0, with_bom=True):
        return self.MO.create({
            'product_id': self.meal.id,
            'product_qty': product_qty,
            'product_uom_id': self.meal.uom_id.id,
            'bom_id': self.bom_meal.id if with_bom else False,
            'location_dest_id': self.kitchen_loc.id,
        })

    def test_cooking_mo_auto_creates_batch(self):
        mo = self._create_cooking_mo(product_qty=100.0)
        self.assertTrue(mo.fsc_is_cooking)
        self.assertEqual(len(mo.fsc_cooking_batch_ids), 1)
        batch = mo.fsc_cooking_batch_ids
        self.assertEqual(batch.expected_meal_qty, 100.0)
        self.assertEqual(batch.kitchen_location_id, self.kitchen_loc)
        self.assertEqual(batch.state, 'planned')
        self.assertEqual(batch.meal_product_id, self.meal)

    def test_non_cooking_mo_no_batch(self):
        mo = self.MO.create({
            'product_id': self.semi_other.id,
            'product_qty': 50.0,
            'product_uom_id': self.semi_other.uom_id.id,
        })
        self.assertFalse(mo.fsc_is_cooking)
        self.assertFalse(mo.fsc_cooking_batch_ids)

    def test_ensure_batch_is_idempotent(self):
        mo = self._create_cooking_mo()
        first = mo.fsc_cooking_batch_ids
        mo._fsc_ensure_cooking_batch()
        self.assertEqual(mo.fsc_cooking_batch_ids, first,
                         'A second call must not duplicate the batch')

    def test_shortage_creates_urgent_line(self):
        mo = self._create_cooking_mo(product_qty=100.0)
        # Build a raw move with demand > zero reserved (no stock).
        self.env['stock.move'].create({
            'name': 'Raw veg required',
            'product_id': self.semi_veg.id,
            'product_uom': self.uom_kg.id,
            'product_uom_qty': 20.0,
            'state': 'confirmed',
            'location_id': self._stock_loc.id,
            'location_dest_id': self._production_loc.id,
            'raw_material_production_id': mo.id,
            'company_id': self.env.company.id,
        })
        mo._fsc_check_shortage()
        urgent = self.Line.search([
            ('origin', '=', mo.name),
            ('urgency', '=', 'urgent'),
        ])
        self.assertEqual(len(urgent), 1)
        self.assertEqual(urgent.product_id, self.semi_veg)
        self.assertEqual(urgent.total_qty, 20.0)
        self.assertEqual(urgent.state, 'open')
        # Batch flagged.
        self.assertTrue(mo.fsc_cooking_batch_ids.shortage_flag)

    def test_shortage_check_idempotent(self):
        mo = self._create_cooking_mo(product_qty=100.0)
        self.env['stock.move'].create({
            'name': 'Raw veg required',
            'product_id': self.semi_veg.id,
            'product_uom': self.uom_kg.id,
            'product_uom_qty': 20.0,
            'state': 'confirmed',
            'location_id': self._stock_loc.id,
            'location_dest_id': self._production_loc.id,
            'raw_material_production_id': mo.id,
            'company_id': self.env.company.id,
        })
        mo._fsc_check_shortage()
        mo._fsc_check_shortage()
        urgent = self.Line.search([
            ('origin', '=', mo.name), ('urgency', '=', 'urgent'),
        ])
        self.assertEqual(len(urgent), 1, 'Repeated shortage checks must not duplicate the urgent line')

    def test_shortage_skipped_when_fully_reserved(self):
        mo = self._create_cooking_mo(product_qty=100.0)
        # Move marked 'assigned' simulates full reservation.
        self.env['stock.move'].create({
            'name': 'Raw veg assigned',
            'product_id': self.semi_veg.id,
            'product_uom': self.uom_kg.id,
            'product_uom_qty': 20.0,
            'state': 'assigned',
            'location_id': self._stock_loc.id,
            'location_dest_id': self._production_loc.id,
            'raw_material_production_id': mo.id,
            'company_id': self.env.company.id,
        })
        mo._fsc_check_shortage()
        urgent = self.Line.search([
            ('origin', '=', mo.name), ('urgency', '=', 'urgent'),
        ])
        self.assertFalse(urgent, 'No urgent line should be created when all moves are assigned')

    def test_finalize_batch_on_done(self):
        mo = self._create_cooking_mo(product_qty=100.0)
        # Create a finished move with picked qty so qty_produced computes.
        self.env['stock.move'].create({
            'name': 'Finished meal',
            'product_id': self.meal.id,
            'product_uom': self.meal.uom_id.id,
            'product_uom_qty': 100.0,
            'quantity': 95.0,
            'picked': True,
            'state': 'done',
            'location_id': self._production_loc.id,
            'location_dest_id': self.kitchen_loc.id,
            'production_id': mo.id,
            'company_id': self.env.company.id,
        })
        mo.write({'state': 'done'})
        mo.invalidate_recordset(['qty_produced'])
        mo._fsc_finalize_cooking_batch()
        batch = mo.fsc_cooking_batch_ids
        self.assertEqual(batch.actual_meal_qty, 95.0)
        self.assertEqual(batch.state, 'done')
        self.assertAlmostEqual(batch.meal_yield_pct, 95.0, places=1)
