from odoo import _, api, fields, models


class FscLossRecord(models.Model):
    _name = 'fsc.loss.record'
    _description = 'FSC Preprocess Loss Record'
    _inherit = ['fsc.audit.mixin', 'mail.thread']
    _order = 'create_date desc, id desc'

    production_id = fields.Many2one('mrp.production', string='Manufacturing Order',
                                    required=True, ondelete='cascade', index=True)
    product_id = fields.Many2one(related='production_id.product_id',
                                 string='Product', store=True, index=True)
    stage = fields.Selection(
        [('cleaning', 'Cleaning'),
         ('cutting', 'Cutting'),
         ('washing', 'Washing'),
         ('blanching', 'Blanching'),
         ('packing', 'Packing'),
         ('other', 'Other')],
        string='Stage', required=True,
    )
    input_qty = fields.Float(string='Input Qty', required=True)
    output_qty = fields.Float(string='Output Qty', required=True)
    loss_qty = fields.Float(string='Loss Qty', compute='_compute_loss', store=True)
    loss_pct = fields.Float(string='Loss (%)', compute='_compute_loss', store=True)
    threshold_pct = fields.Float(string='Threshold (%)')
    over_threshold = fields.Boolean(string='Over Threshold',
                                    compute='_compute_loss', store=True)
    alerted = fields.Boolean(string='Alerted', default=False, readonly=True)
    fsc_auto = fields.Boolean(string='Auto-recorded', default=False, readonly=True,
                              help='True when this record was created automatically '
                                   'when the parent MO was marked done.')
    note = fields.Text(string='Note')

    _fsc_audit_fields = ('input_qty', 'output_qty', 'threshold_pct')

    @api.depends('input_qty', 'output_qty', 'threshold_pct')
    def _compute_loss(self):
        for rec in self:
            rec.loss_qty = (rec.input_qty or 0.0) - (rec.output_qty or 0.0)
            rec.loss_pct = (
                100.0 * rec.loss_qty / rec.input_qty if rec.input_qty else 0.0
            )
            rec.over_threshold = rec.loss_pct > (rec.threshold_pct or 0.0)

    def _fsc_send_alert(self):
        """Post a chatter message on the MO when loss exceeds threshold.

        Idempotent: once alerted, subsequent calls are no-ops.
        """
        for rec in self:
            if rec.alerted or not rec.production_id:
                continue
            mo = rec.production_id
            uom_name = mo.product_uom_id.name if mo.product_uom_id else ''
            body = _(
                'Loss alert on MO %(mo)s: actual %(actual).2f%% loss exceeds '
                'threshold %(thr).2f%%. Input %(inp).4f %(u)s, output %(out).4f %(u)s.',
                mo=mo.name, actual=rec.loss_pct, thr=rec.threshold_pct,
                inp=rec.input_qty, out=rec.output_qty, u=uom_name,
            )
            mo.message_post(body=body, subtype_xmlid='mail.mt_comment')
            rec.alerted = True
        return True
