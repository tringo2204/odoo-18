from odoo import api, fields, models


class CateringSite(models.Model):
    _name = 'catering.site'
    _description = 'Catering Site (Kitchen / Construction site / Canteen)'
    _inherit = ['fsc.audit.mixin', 'mail.thread']
    _order = 'name'

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(string='Code', help='Internal short code, e.g. KITCHEN-A')
    customer_id = fields.Many2one(
        'res.partner', string='Customer', required=True, tracking=True,
        domain=[('customer_rank', '>', 0)],
        help='B2B customer this site belongs to.',
    )
    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Warehouse',
        help='Warehouse that supplies this site.',
    )
    location_id = fields.Many2one(
        'stock.location', string='Kitchen Location',
        domain=[('usage', '=', 'internal')],
        help='Stock location representing this kitchen.',
    )
    site_manager_id = fields.Many2one('res.users', string='Site Manager')
    default_delivery_time = fields.Float(
        string='Default Delivery Time',
        help='Default time of day for meal delivery (decimal hour).',
    )
    meal_shift_ids = fields.Many2many(
        'catering.meal.shift', string='Active Meal Shifts',
    )
    notes = fields.Text()
    active = fields.Boolean(default=True)

    _fsc_audit_fields = ('customer_id', 'warehouse_id', 'location_id', 'site_manager_id', 'active')

    @api.depends('name', 'customer_id')
    def _compute_display_name(self):
        for s in self:
            if s.customer_id:
                s.display_name = f'{s.customer_id.name} / {s.name}'
            else:
                s.display_name = s.name or ''
