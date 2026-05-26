from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    fsc_site_ids = fields.One2many(
        'catering.site', 'customer_id', string='Catering Sites',
    )
    fsc_default_site_id = fields.Many2one(
        'catering.site', string='Default Site',
        domain="[('customer_id', '=', id)]",
        help='Default site/kitchen used when creating menu plans or SOs.',
    )
    fsc_default_shift_ids = fields.Many2many(
        'catering.meal.shift', string='Default Meal Shifts',
        help='Shifts this customer typically subscribes to.',
    )
    fsc_allowed_variance_qty = fields.Integer(
        string='Allowed Variance (qty)',
        help='Maximum |actual - planned| absolute qty per shift before requiring '
             'approval.',
        default=0,
    )
    fsc_allowed_variance_pct = fields.Float(
        string='Allowed Variance (%)',
        help='Maximum |actual - planned| / planned percentage per shift.',
        default=10.0,
    )
    fsc_site_count = fields.Integer(
        compute='_compute_fsc_site_count',
    )

    def _compute_fsc_site_count(self):
        for p in self:
            p.fsc_site_count = len(p.fsc_site_ids)
