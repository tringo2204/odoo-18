from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = ['res.partner', 'fsc.audit.mixin']
    _name = 'res.partner'

    fsc_on_time_rate = fields.Float(
        string='On-time Delivery Rate (%)',
        help='Computed from purchase order history (overridden by procurement engine).',
        default=0.0,
    )
    fsc_defect_rate = fields.Float(
        string='Defect Rate (%)',
        help='Computed from QC rejection history.',
        default=0.0,
    )
    fsc_rating_score = fields.Float(
        string='Vendor Rating Score',
        compute='_compute_fsc_rating_score',
        store=True,
        help='Composite score: on_time*0.4 + price*0.4 + (100-defect)*0.2.',
    )
    fsc_price_log_ids = fields.One2many(
        'fsc.vendor.price.log',
        'partner_id',
        string='Price History',
    )

    _fsc_audit_fields = (
        'fsc_on_time_rate',
        'fsc_defect_rate',
    )

    @api.depends('fsc_on_time_rate', 'fsc_defect_rate')
    def _compute_fsc_rating_score(self):
        # Placeholder weighting: procurement engine will replace this with the
        # full formula incorporating price competitiveness.
        for partner in self:
            on_time = partner.fsc_on_time_rate or 0.0
            defect = partner.fsc_defect_rate or 0.0
            partner.fsc_rating_score = on_time * 0.4 + (100.0 - defect) * 0.2
