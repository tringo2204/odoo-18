import logging

from odoo import _, fields, models

_logger = logging.getLogger(__name__)


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    fsc_loss_record_ids = fields.One2many(
        'fsc.loss.record', 'production_id', string='FSC Loss Records',
    )
    fsc_total_loss_pct = fields.Float(
        string='Total Loss (%)', compute='_compute_fsc_total_loss',
    )

    def _compute_fsc_total_loss(self):
        for mo in self:
            records = mo.fsc_loss_record_ids
            if not records:
                mo.fsc_total_loss_pct = 0.0
                continue
            total_input = sum(records.mapped('input_qty'))
            total_loss = sum(records.mapped('loss_qty'))
            mo.fsc_total_loss_pct = 100.0 * total_loss / total_input if total_input else 0.0

    def button_mark_done(self):
        res = super().button_mark_done()
        # Pre-button may return a wizard action; only record when self transitions to done.
        for mo in self:
            if mo.state == 'done':
                try:
                    mo._fsc_record_loss_on_done()
                except Exception:
                    _logger.exception('FSC: failed to record loss for MO %s', mo.name)
        return res

    def _fsc_record_loss_on_done(self):
        """Create an aggregate loss record when the MO transitions to done.

        Only acts on MOs whose finished product is a preprocess product.
        Idempotent: an auto record is created once per MO.
        """
        self.ensure_one()
        if self.state != 'done':
            return False
        product_tmpl = self.product_id.product_tmpl_id
        if product_tmpl.fsc_processing_type != 'preprocess':
            return False

        existing_auto = self.fsc_loss_record_ids.filtered(lambda r: r.fsc_auto)
        if existing_auto:
            return existing_auto

        input_qty = self._fsc_compute_input_qty()
        output_qty = self.qty_produced or 0.0
        threshold = (self.bom_id and self.bom_id.fsc_expected_loss) or product_tmpl.fsc_loss_threshold or 0.0

        record = self.env['fsc.loss.record'].create({
            'production_id': self.id,
            'stage': 'other',
            'input_qty': input_qty,
            'output_qty': output_qty,
            'threshold_pct': threshold,
            'fsc_auto': True,
        })
        if record.over_threshold:
            record._fsc_send_alert()
        return record

    def _fsc_compute_input_qty(self):
        """Sum consumed component quantities measured in the production product's UoM.

        Only components whose UoM is exactly the production product's UoM are
        counted. This excludes minor secondary ingredients (e.g. spices in grams
        when the main veg is in kg) and process additives (e.g. brine in litres)
        from the yield calculation, which matches typical preprocess BOMs where
        loss = main_ingredient_in - main_ingredient_equivalent_out.

        Override this method on subclassed MOs when a multi-ingredient yield
        formula is needed.
        """
        self.ensure_one()
        prod_uom = self.product_uom_id
        return sum(
            move.quantity or 0.0
            for move in self.move_raw_ids
            if move.product_uom == prod_uom
        )
