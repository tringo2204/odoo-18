from odoo import api, fields, models


class FscMealCost(models.Model):
    _name = 'fsc.meal.cost'
    _description = 'FSC Meal Cost'
    _inherit = ['fsc.audit.mixin']
    _order = 'create_date desc, id desc'

    production_id = fields.Many2one('mrp.production', string='Manufacturing Order',
                                    required=True, ondelete='cascade', index=True)
    meal_product_id = fields.Many2one(
        'product.product', string='Meal Product', required=True,
        domain="[('fsc_product_type','=','finished')]",
    )
    meal_qty = fields.Float(string='Meals Produced', required=True)

    raw_cost = fields.Float(string='Raw Material Cost')
    labor_cost = fields.Float(string='Labor Cost')
    overhead_cost = fields.Float(string='Overhead Cost')
    planned_cost_total = fields.Float(string='Planned Cost (Total)')
    actual_cost_total = fields.Float(string='Actual Cost (Total)',
                                     compute='_compute_actual_total', store=True)

    cost_per_meal_planned = fields.Float(string='Planned Cost / Meal',
                                         compute='_compute_per_meal', store=True)
    cost_per_meal_actual = fields.Float(string='Actual Cost / Meal',
                                        compute='_compute_per_meal', store=True)
    variance = fields.Float(string='Variance', compute='_compute_variance', store=True)
    variance_pct = fields.Float(string='Variance (%)',
                                compute='_compute_variance', store=True)

    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
    )

    fsc_auto = fields.Boolean(string='Auto-recorded', default=False, readonly=True,
                              help='True when this record was created automatically '
                                   'on MO done.')

    _fsc_audit_fields = ('raw_cost', 'labor_cost', 'overhead_cost', 'planned_cost_total')

    @api.depends('raw_cost', 'labor_cost', 'overhead_cost')
    def _compute_actual_total(self):
        for rec in self:
            rec.actual_cost_total = (rec.raw_cost or 0.0) + (rec.labor_cost or 0.0) + (rec.overhead_cost or 0.0)

    @api.depends('planned_cost_total', 'actual_cost_total', 'meal_qty')
    def _compute_per_meal(self):
        for rec in self:
            rec.cost_per_meal_planned = (
                rec.planned_cost_total / rec.meal_qty if rec.meal_qty else 0.0
            )
            rec.cost_per_meal_actual = (
                rec.actual_cost_total / rec.meal_qty if rec.meal_qty else 0.0
            )

    @api.depends('planned_cost_total', 'actual_cost_total')
    def _compute_variance(self):
        for rec in self:
            rec.variance = (rec.actual_cost_total or 0.0) - (rec.planned_cost_total or 0.0)
            rec.variance_pct = (
                100.0 * rec.variance / rec.planned_cost_total if rec.planned_cost_total else 0.0
            )
