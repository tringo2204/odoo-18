from odoo import api, fields, models


class FscCookingBatch(models.Model):
    _name = 'fsc.cooking.batch'
    _description = 'FSC Kitchen Cooking Batch'
    _inherit = ['fsc.audit.mixin', 'mail.thread']
    _order = 'cooking_date desc, id desc'

    name = fields.Char(string='Reference', required=True, default='New', copy=False)
    production_id = fields.Many2one('mrp.production', string='Manufacturing Order',
                                    required=True, ondelete='cascade', index=True)
    kitchen_location_id = fields.Many2one(
        'stock.location', string='Kitchen Location', required=True,
        domain=[('usage', '=', 'internal')], index=True,
    )
    meal_product_id = fields.Many2one(
        'product.product', string='Meal Product', required=True,
        domain="[('fsc_product_type','=','finished')]",
    )

    cooking_date = fields.Datetime(string='Cooking Date', required=True,
                                   default=fields.Datetime.now)
    expected_meal_qty = fields.Float(string='Expected Meals', required=True)
    actual_meal_qty = fields.Float(string='Actual Meals')
    meal_yield_pct = fields.Float(string='Meal Yield (%)',
                                  compute='_compute_meal_yield', store=True)

    shortage_flag = fields.Boolean(string='Had Shortage', default=False)
    state = fields.Selection(
        [('planned', 'Planned'),
         ('cooking', 'Cooking'),
         ('done', 'Done'),
         ('cancel', 'Cancelled')],
        string='State', default='planned', required=True, tracking=True,
    )

    _fsc_audit_fields = ('expected_meal_qty', 'actual_meal_qty', 'state', 'shortage_flag')

    @api.depends('expected_meal_qty', 'actual_meal_qty')
    def _compute_meal_yield(self):
        for rec in self:
            rec.meal_yield_pct = (
                100.0 * (rec.actual_meal_qty or 0.0) / rec.expected_meal_qty
                if rec.expected_meal_qty else 0.0
            )
