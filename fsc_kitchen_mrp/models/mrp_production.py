import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    fsc_cooking_batch_ids = fields.One2many(
        'fsc.cooking.batch', 'production_id', string='FSC Cooking Batch',
    )
    fsc_cooking_batch_id = fields.Many2one(
        'fsc.cooking.batch', string='Cooking Batch',
        compute='_compute_fsc_cooking_batch_id', store=False,
    )
    fsc_is_cooking = fields.Boolean(
        string='Is Cooking MO', compute='_compute_fsc_is_cooking', store=True,
    )

    @api.depends('product_id')
    def _compute_fsc_is_cooking(self):
        for mo in self:
            tmpl = mo.product_id.product_tmpl_id
            mo.fsc_is_cooking = tmpl.fsc_processing_type == 'cooking'

    @api.depends('fsc_cooking_batch_ids')
    def _compute_fsc_cooking_batch_id(self):
        for mo in self:
            mo.fsc_cooking_batch_id = mo.fsc_cooking_batch_ids[:1]

    @api.model_create_multi
    def create(self, vals_list):
        mos = super().create(vals_list)
        for mo in mos.filtered('fsc_is_cooking'):
            mo._fsc_ensure_cooking_batch()
        return mos

    def _fsc_ensure_cooking_batch(self):
        """Create the cooking batch shell for this MO if missing."""
        self.ensure_one()
        if self.fsc_cooking_batch_ids:
            return self.fsc_cooking_batch_ids[0]
        kitchen_location = self.location_dest_id
        if not kitchen_location or kitchen_location.usage != 'internal':
            # Fallback: pick any internal location in the company.
            kitchen_location = self.env['stock.location'].search(
                [('usage', '=', 'internal'), ('company_id', '=', self.company_id.id)],
                limit=1,
            )
        return self.env['fsc.cooking.batch'].create({
            'production_id': self.id,
            'meal_product_id': self.product_id.id,
            'kitchen_location_id': kitchen_location.id if kitchen_location else False,
            'expected_meal_qty': self.product_qty,
            'cooking_date': self.date_start or fields.Datetime.now(),
            'state': 'planned',
        })

    def action_confirm(self):
        res = super().action_confirm()
        for mo in self.filtered('fsc_is_cooking'):
            mo._fsc_check_shortage()
        return res

    def _fsc_check_shortage(self):
        """Detect raw shortage on a confirmed cooking MO and create urgent
        consolidation lines for the missing quantities. Idempotent: existing
        urgent lines for the same MO origin are not duplicated.
        """
        self.ensure_one()
        unreserved = self.move_raw_ids.filtered(
            lambda m: m.state in ('confirmed', 'partially_available')
        )
        if not unreserved:
            return False

        shortage_data = []
        for move in unreserved:
            reserved_qty = sum(move.move_line_ids.mapped('quantity'))
            missing = (move.product_uom_qty or 0.0) - reserved_qty
            if missing > 0:
                shortage_data.append((move, missing))

        if not shortage_data:
            return False

        batch = self.fsc_cooking_batch_ids[:1]
        if batch:
            batch.shortage_flag = True

        product_names = ', '.join(m.product_id.display_name for m, _ in shortage_data)
        self.message_post(
            body=_('Shortage detected on cooking MO. Triggering urgent procurement for: %s', product_names)
        )

        Line = self.env['fsc.consolidation.line'].sudo()
        for move, missing in shortage_data:
            already = Line.search([
                ('origin', '=', self.name),
                ('product_id', '=', move.product_id.id),
                ('urgency', '=', 'urgent'),
                ('state', 'not in', ('done', 'cancel')),
            ], limit=1)
            if already:
                continue
            line = Line.create({
                'company_id': self.company_id.id,
                'product_id': move.product_id.id,
                'uom_id': move.product_uom.id,
                'total_qty': missing,
                'required_date': self.date_start or fields.Datetime.now(),
                'origin': self.name,
                'urgency': 'urgent',
                'state': 'open',
            })
            # Try to process immediately. The action is defined by
            # fsc_procurement_engine; tolerate its absence.
            if hasattr(line, 'action_generate_procurement'):
                try:
                    line.action_generate_procurement()
                except Exception:
                    _logger.exception(
                        'FSC: failed to immediately process urgent line %s', line.name,
                    )

        return True

    def button_mark_done(self):
        res = super().button_mark_done()
        for mo in self.filtered(lambda m: m.state == 'done' and m.fsc_is_cooking):
            try:
                mo._fsc_finalize_cooking_batch()
            except Exception:
                _logger.exception('FSC: failed to finalize cooking batch for MO %s', mo.name)
        return res

    def _fsc_finalize_cooking_batch(self):
        self.ensure_one()
        batch = self.fsc_cooking_batch_ids[:1]
        if not batch:
            return False
        batch.write({
            'actual_meal_qty': self.qty_produced,
            'state': 'done',
        })
        return batch
