import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    fsc_meal_cost_ids = fields.One2many(
        'fsc.meal.cost', 'production_id', string='FSC Meal Cost Records',
    )

    def button_mark_done(self):
        res = super().button_mark_done()
        for mo in self.filtered(lambda m: m.state == 'done'):
            try:
                mo._fsc_record_meal_cost()
            except Exception:
                _logger.exception('FSC: failed to record meal cost for MO %s', mo.name)
        return res

    def _fsc_record_meal_cost(self):
        """Create an aggregate meal-cost record for a finished-product MO.

        Skips MOs whose product is not a finished meal. Idempotent: an auto
        record is created at most once per MO.
        """
        self.ensure_one()
        if self.state != 'done':
            return False
        product_tmpl = self.product_id.product_tmpl_id
        if product_tmpl.fsc_product_type != 'finished':
            return False
        existing = self.fsc_meal_cost_ids.filtered(lambda r: r.fsc_auto)
        if existing:
            return existing

        meal_qty = self.qty_produced or 0.0
        raw_cost = self._fsc_compute_actual_raw_cost()
        planned_cost = self._fsc_compute_planned_cost()

        return self.env['fsc.meal.cost'].create({
            'production_id': self.id,
            'meal_product_id': self.product_id.id,
            'meal_qty': meal_qty,
            'raw_cost': raw_cost,
            'labor_cost': 0.0,
            'overhead_cost': 0.0,
            'planned_cost_total': planned_cost,
            'fsc_auto': True,
        })

    def _fsc_compute_actual_raw_cost(self):
        """Sum of consumed components × their standard price."""
        self.ensure_one()
        total = 0.0
        for move in self.move_raw_ids:
            qty = move.quantity or 0.0
            price = move.product_id.standard_price or 0.0
            total += qty * price
        return total

    def _fsc_compute_planned_cost(self):
        """Compute planned cost from the BOM, scaled to the MO's product_qty.

        For each BOM line: (line.product_qty / bom.product_qty) × mo.product_qty
        × line.product.standard_price. Returns 0 when no BOM is set.
        """
        self.ensure_one()
        bom = self.bom_id
        if not bom or not bom.product_qty:
            return 0.0
        ratio = (self.product_qty or 0.0) / bom.product_qty
        total = 0.0
        for line in bom.bom_line_ids:
            qty = (line.product_qty or 0.0) * ratio
            price = line.product_id.standard_price or 0.0
            total += qty * price
        return total
