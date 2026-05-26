from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'fsc')
class TestFscInternalTransfer(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Picking = cls.env['stock.picking']
        cls.Move = cls.env['stock.move']
        cls.Discrepancy = cls.env['fsc.transfer.discrepancy']
        cls.uom_kg = cls.env.ref('uom.product_uom_kgm')

        Location = cls.env['stock.location']
        cls.warehouse = cls.env['stock.warehouse'].search(
            [('company_id', '=', cls.env.company.id)], limit=1)
        cls.stock_loc = cls.warehouse.lot_stock_id
        cls.kitchen_loc = Location.create({
            'name': 'FSC Test Kitchen',
            'usage': 'internal',
            'location_id': cls.stock_loc.location_id.id or cls.stock_loc.id,
        })

        # Dedicated picking type with FSC dual confirm.
        cls.picking_type_dual = cls.env['stock.picking.type'].create({
            'name': 'FSC Test WH→Kitchen',
            'code': 'internal',
            'sequence_code': 'FSCT/',
            'warehouse_id': cls.warehouse.id,
            'default_location_src_id': cls.stock_loc.id,
            'default_location_dest_id': cls.kitchen_loc.id,
            'fsc_dual_confirm': True,
        })
        # Same setup but no dual confirm — control group.
        cls.picking_type_plain = cls.env['stock.picking.type'].create({
            'name': 'FSC Test WH→Kitchen Plain',
            'code': 'internal',
            'sequence_code': 'FSCTP/',
            'warehouse_id': cls.warehouse.id,
            'default_location_src_id': cls.stock_loc.id,
            'default_location_dest_id': cls.kitchen_loc.id,
            'fsc_dual_confirm': False,
        })

        cls.product = cls.env['product.product'].create({
            'name': 'FSC Test Transfer Product',
            'type': 'consu',
            'is_storable': True,
            'uom_id': cls.uom_kg.id,
            'uom_po_id': cls.uom_kg.id,
            'fsc_product_type': 'semi_finished',
        })

    def _make_picking(self, picking_type, demand_qty=10.0):
        picking = self.Picking.create({
            'picking_type_id': picking_type.id,
            'location_id': self.stock_loc.id,
            'location_dest_id': self.kitchen_loc.id,
            'move_ids': [(0, 0, {
                'name': self.product.name,
                'product_id': self.product.id,
                'product_uom': self.uom_kg.id,
                'product_uom_qty': demand_qty,
                'location_id': self.stock_loc.id,
                'location_dest_id': self.kitchen_loc.id,
            })],
        })
        return picking

    def test_dual_confirm_flag_propagates_to_picking(self):
        picking_dual = self._make_picking(self.picking_type_dual)
        picking_plain = self._make_picking(self.picking_type_plain)
        self.assertTrue(picking_dual.fsc_dual_confirm_required)
        self.assertFalse(picking_plain.fsc_dual_confirm_required)

    def test_warehouse_confirm_snapshots_qty(self):
        picking = self._make_picking(self.picking_type_dual)
        picking.move_ids.write({'quantity': 10.0})
        picking.action_fsc_warehouse_confirm()
        self.assertTrue(picking.fsc_warehouse_confirmed)
        self.assertEqual(picking.fsc_warehouse_confirmed_by, self.env.user)
        self.assertTrue(picking.fsc_warehouse_confirmed_at)
        self.assertEqual(picking.move_ids.fsc_warehouse_qty, 10.0)

    def test_warehouse_confirm_blocked_on_plain_type(self):
        picking = self._make_picking(self.picking_type_plain)
        with self.assertRaises(UserError):
            picking.action_fsc_warehouse_confirm()

    def test_warehouse_confirm_idempotent(self):
        picking = self._make_picking(self.picking_type_dual)
        picking.move_ids.write({'quantity': 10.0})
        picking.action_fsc_warehouse_confirm()
        with self.assertRaises(UserError):
            picking.action_fsc_warehouse_confirm()

    def test_kitchen_confirm_requires_warehouse_first(self):
        picking = self._make_picking(self.picking_type_dual)
        picking.move_ids.write({'quantity': 10.0})
        with self.assertRaises(UserError):
            picking.action_fsc_kitchen_confirm()

    def test_kitchen_confirm_matching_qty_no_discrepancy(self):
        picking = self._make_picking(self.picking_type_dual, demand_qty=10.0)
        picking.move_ids.write({'quantity': 10.0})
        picking.action_fsc_warehouse_confirm()
        # Kitchen also reports 10kg received — no discrepancy.
        picking.move_ids.write({'quantity': 10.0})
        picking.action_fsc_kitchen_confirm()
        self.assertTrue(picking.fsc_kitchen_confirmed)
        self.assertEqual(picking.move_ids.fsc_kitchen_qty, 10.0)
        self.assertFalse(picking.fsc_transfer_discrepancy_ids)
        self.assertEqual(picking.fsc_discrepancy_count, 0)

    def test_kitchen_confirm_short_qty_creates_discrepancy(self):
        picking = self._make_picking(self.picking_type_dual, demand_qty=10.0)
        picking.move_ids.write({'quantity': 10.0})
        picking.action_fsc_warehouse_confirm()
        # Kitchen reports only 9.5kg — shortage of 0.5kg.
        picking.move_ids.write({'quantity': 9.5})
        picking.action_fsc_kitchen_confirm()
        discrepancies = picking.fsc_transfer_discrepancy_ids
        self.assertEqual(len(discrepancies), 1)
        d = discrepancies[0]
        self.assertEqual(d.warehouse_qty, 10.0)
        self.assertEqual(d.kitchen_qty, 9.5)
        self.assertEqual(d.discrepancy_qty, -0.5)
        self.assertAlmostEqual(d.discrepancy_pct, -5.0, places=2)
        self.assertEqual(d.state, 'open')
        self.assertEqual(d.warehouse_confirmed_by, self.env.user)
        self.assertEqual(d.kitchen_confirmed_by, self.env.user)

    def test_kitchen_confirm_over_qty_creates_discrepancy(self):
        picking = self._make_picking(self.picking_type_dual, demand_qty=10.0)
        picking.move_ids.write({'quantity': 10.0})
        picking.action_fsc_warehouse_confirm()
        picking.move_ids.write({'quantity': 10.5})  # over-receipt
        picking.action_fsc_kitchen_confirm()
        d = picking.fsc_transfer_discrepancy_ids
        self.assertEqual(len(d), 1)
        self.assertEqual(d.discrepancy_qty, 0.5)

    def test_kitchen_confirm_idempotent(self):
        picking = self._make_picking(self.picking_type_dual)
        picking.move_ids.write({'quantity': 10.0})
        picking.action_fsc_warehouse_confirm()
        picking.action_fsc_kitchen_confirm()
        with self.assertRaises(UserError):
            picking.action_fsc_kitchen_confirm()

    def test_validate_blocked_without_dual_confirm(self):
        picking = self._make_picking(self.picking_type_dual)
        picking.action_confirm()
        picking.move_ids.write({'quantity': 10.0})
        with self.assertRaises(UserError):
            picking.button_validate()

    def test_validate_blocked_with_only_wh_confirm(self):
        picking = self._make_picking(self.picking_type_dual)
        picking.action_confirm()
        picking.move_ids.write({'quantity': 10.0})
        picking.action_fsc_warehouse_confirm()
        with self.assertRaises(UserError):
            picking.button_validate()

    def test_plain_picking_type_validates_normally(self):
        # No dual confirm requirement → button_validate path is unaffected.
        picking = self._make_picking(self.picking_type_plain)
        # No FSC fields, so super().button_validate would proceed normally if stock allows.
        # Here we only assert our guard does NOT raise — actual stock validation
        # may still complain about no quantity. So just verify the guard logic
        # returns the super response (which may itself raise, but not our UserError).
        try:
            picking.button_validate()
        except UserError as e:
            self.assertNotIn('requires both warehouse and kitchen confirmation', str(e))
