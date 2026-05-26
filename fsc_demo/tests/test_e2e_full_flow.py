from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'fsc', 'fsc_e2e')
class TestFscE2EFullFlow(TransactionCase):
    """End-to-end smoke test crossing six FSC modules:

      fsc_demand_consolidation  → consolidation line creation
      fsc_procurement_engine    → make-vs-buy decision + PO generation
      fsc_preprocess_mrp        → preprocess MO + loss tracking
      fsc_kitchen_mrp           → cooking batch auto-creation
      fsc_costing_engine        → meal cost record auto-creation
      fsc_audit_log             → audit entries on state changes

    The test builds its own fixtures (vendor, products, BOMs) — it is
    independent of the post_init demo data, so it remains reproducible.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.uom_kg = cls.env.ref('uom.product_uom_kgm')
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')

        Location = cls.env['stock.location']
        cls.production_loc = Location.search(
            [('usage', '=', 'production'), ('company_id', '=', cls.env.company.id)], limit=1)
        cls.stock_loc = Location.search(
            [('usage', '=', 'internal'), ('company_id', '=', cls.env.company.id)], limit=1)

        # Vendor
        cls.vendor = cls.env['res.partner'].create({
            'name': 'FSC E2E Vendor',
            'is_company': True,
            'supplier_rank': 1,
            'fsc_on_time_rate': 95.0,
            'fsc_defect_rate': 2.0,
        })

        # Raw kg → semi kg → meal unit
        cls.raw = cls.env['product.product'].create({
            'name': 'FSC E2E Raw',
            'type': 'consu',
            'is_storable': True,
            'uom_id': cls.uom_kg.id,
            'uom_po_id': cls.uom_kg.id,
            'fsc_product_type': 'raw',
            'standard_price': 15000.0,
            'seller_ids': [(0, 0, {
                'partner_id': cls.vendor.id,
                'price': 20000.0,
                'min_qty': 0.0,
                'product_uom': cls.uom_kg.id,
            })],
        })
        cls.semi = cls.env['product.product'].create({
            'name': 'FSC E2E Semi',
            'type': 'consu',
            'is_storable': True,
            'uom_id': cls.uom_kg.id,
            'uom_po_id': cls.uom_kg.id,
            'fsc_product_type': 'semi_finished',
            'fsc_processing_type': 'preprocess',
            'fsc_loss_threshold': 15.0,
            'standard_price': 22000.0,
        })
        cls.meal = cls.env['product.product'].create({
            'name': 'FSC E2E Meal',
            'type': 'consu',
            'is_storable': True,
            'uom_id': cls.uom_unit.id,
            'uom_po_id': cls.uom_unit.id,
            'fsc_product_type': 'finished',
            'fsc_processing_type': 'cooking',
            'standard_price': 35000.0,
        })

        cls.bom_semi = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.semi.product_tmpl_id.id,
            'product_qty': 1.0,
            'product_uom_id': cls.uom_kg.id,
            'type': 'normal',
            'fsc_expected_loss': 15.0,
            'bom_line_ids': [(0, 0, {
                'product_id': cls.raw.id,
                'product_qty': 1.18,
                'product_uom_id': cls.uom_kg.id,
            })],
        })
        cls.bom_meal = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.meal.product_tmpl_id.id,
            'product_qty': 1.0,
            'product_uom_id': cls.uom_unit.id,
            'type': 'normal',
            'bom_line_ids': [(0, 0, {
                'product_id': cls.semi.id,
                'product_qty': 0.15,
                'product_uom_id': cls.uom_kg.id,
            })],
        })

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _create_consumption_move(self, mo, product, uom, qty):
        return self.env['stock.move'].create({
            'name': f'{product.name} consumption',
            'product_id': product.id,
            'product_uom': uom.id,
            'product_uom_qty': qty,
            'quantity': qty,
            'state': 'done',
            'picked': True,
            'location_id': self.stock_loc.id,
            'location_dest_id': self.production_loc.id,
            'raw_material_production_id': mo.id,
            'company_id': self.env.company.id,
        })

    def _create_finished_move(self, mo, product, uom, qty):
        return self.env['stock.move'].create({
            'name': f'{product.name} output',
            'product_id': product.id,
            'product_uom': uom.id,
            'product_uom_qty': qty,
            'quantity': qty,
            'state': 'done',
            'picked': True,
            'location_id': self.production_loc.id,
            'location_dest_id': self.stock_loc.id,
            'production_id': mo.id,
            'company_id': self.env.company.id,
        })

    # ------------------------------------------------------------------
    # The E2E test
    # ------------------------------------------------------------------
    def test_full_chain_consolidation_to_meal_cost(self):
        """One scenario, five module hooks, asserts each layer end-to-end."""
        AuditLog = self.env['fsc.audit.log']
        ConsoLine = self.env['fsc.consolidation.line']
        MakeBuy = self.env['fsc.make.buy.decision']
        LossRecord = self.env['fsc.loss.record']
        CookingBatch = self.env['fsc.cooking.batch']
        MealCost = self.env['fsc.meal.cost']

        # 1) Kitchen needs raw — simulate consolidated demand and run procurement.
        cl = ConsoLine.create({
            'product_id': self.raw.id,
            'uom_id': self.uom_kg.id,
            'total_qty': 50.0,
            'required_date': fields.Datetime.now(),
            'state': 'open',
            'origin': 'E2E-KITCHEN-DEMAND',
        })
        cl.action_generate_procurement()

        # → PO created, line transitioned, decision recorded
        self.assertEqual(cl.state, 'rfq_created',
                         'Consolidation line should advance to rfq_created')
        po = cl.purchase_order_id
        self.assertTrue(po, 'PO should be generated')
        self.assertEqual(po.partner_id, self.vendor)
        self.assertEqual(po.state, 'draft')
        self.assertEqual(len(po.order_line), 1)
        self.assertEqual(po.order_line.product_id, self.raw)
        self.assertEqual(po.order_line.product_qty, 50.0)

        decision = MakeBuy.search([('consolidation_line_id', '=', cl.id)])
        self.assertEqual(len(decision), 1)
        self.assertEqual(decision.decision, 'buy')
        self.assertEqual(decision.chosen_vendor_id, self.vendor)

        # 2) Preprocess MO: raw → semi. Simulate consumption + production then done.
        mo_semi = self.env['mrp.production'].create({
            'product_id': self.semi.id,
            'product_qty': 100.0,
            'product_uom_id': self.semi.uom_id.id,
            'bom_id': self.bom_semi.id,
        })
        # 130 kg raw consumed, 100 kg semi produced → 23.08% loss (over 15%)
        self._create_consumption_move(mo_semi, self.raw, self.uom_kg, 130.0)
        self._create_finished_move(mo_semi, self.semi, self.uom_kg, 100.0)
        mo_semi.write({'state': 'done'})
        mo_semi.invalidate_recordset(['qty_produced'])
        mo_semi._fsc_record_loss_on_done()

        loss_rec = LossRecord.search([('production_id', '=', mo_semi.id)])
        self.assertEqual(len(loss_rec), 1)
        self.assertEqual(loss_rec.input_qty, 130.0)
        self.assertEqual(loss_rec.output_qty, 100.0)
        self.assertTrue(loss_rec.over_threshold,
                        'Loss should be flagged as over threshold')
        self.assertTrue(loss_rec.alerted,
                        'Alert should have been posted to MO chatter')
        self.assertTrue(loss_rec.fsc_auto)
        alert_msgs = mo_semi.message_ids.filtered(
            lambda m: 'Loss alert' in (m.body or ''))
        self.assertTrue(alert_msgs, 'MO chatter should contain a loss alert')

        # 3) Cooking MO: semi → meal. Cooking batch auto-created on create().
        mo_meal = self.env['mrp.production'].create({
            'product_id': self.meal.id,
            'product_qty': 200.0,
            'product_uom_id': self.meal.uom_id.id,
            'bom_id': self.bom_meal.id,
        })
        cooking_batch = CookingBatch.search([('production_id', '=', mo_meal.id)])
        self.assertEqual(len(cooking_batch), 1,
                         'Cooking batch must be auto-created on MO create()')
        self.assertEqual(cooking_batch.expected_meal_qty, 200.0)
        self.assertEqual(cooking_batch.state, 'planned')

        # 200 meals × 0.15 kg = 30 kg semi consumed; produce 195 meals (5 short).
        self._create_consumption_move(mo_meal, self.semi, self.uom_kg, 30.0)
        self._create_finished_move(mo_meal, self.meal, self.uom_unit, 195.0)
        mo_meal.write({'state': 'done'})
        mo_meal.invalidate_recordset(['qty_produced'])
        mo_meal._fsc_finalize_cooking_batch()
        mo_meal._fsc_record_meal_cost()

        cooking_batch.invalidate_recordset(['actual_meal_qty', 'state', 'meal_yield_pct'])
        self.assertEqual(cooking_batch.actual_meal_qty, 195.0)
        self.assertEqual(cooking_batch.state, 'done')
        self.assertAlmostEqual(cooking_batch.meal_yield_pct, 97.5, places=1)

        # 4) Meal cost record auto-built.
        meal_cost = MealCost.search([('production_id', '=', mo_meal.id)])
        self.assertEqual(len(meal_cost), 1)
        # actual raw cost = 30 kg × 22000 = 660000 (semi standard_price)
        self.assertEqual(meal_cost.raw_cost, 30.0 * 22000.0)
        self.assertEqual(meal_cost.meal_qty, 195.0)
        # planned cost = 200 meals × 0.15 kg × 22000 = 660000 (same here)
        self.assertEqual(meal_cost.planned_cost_total, 200.0 * 0.15 * 22000.0)
        self.assertTrue(meal_cost.fsc_auto)

        # 5) Audit log captured at least the state transitions on the consolidation line.
        audit = AuditLog.search([
            ('model_name', '=', 'fsc.consolidation.line'),
            ('res_id', '=', cl.id),
            ('field_name', '=', 'state'),
        ])
        self.assertTrue(audit, 'Audit log must contain at least one state transition '
                               'on the consolidation line')

        # 6) Sanity: chained data references resolve cleanly.
        self.assertEqual(po.order_line.product_id, self.raw)
        self.assertEqual(loss_rec.production_id, mo_semi)
        self.assertEqual(cooking_batch.production_id, mo_meal)
        self.assertEqual(meal_cost.production_id, mo_meal)
