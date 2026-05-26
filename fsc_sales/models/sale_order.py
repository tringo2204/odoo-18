from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    fsc_menu_plan_id = fields.Many2one(
        'catering.menu.plan', string='Menu Plan', readonly=True, copy=False,
        index=True,
    )
    fsc_site_id = fields.Many2one(
        'catering.site', string='Site',
        domain="[('customer_id', '=', partner_id)]",
    )
    fsc_meal_date = fields.Date(string='Meal Date', index=True)
    fsc_total_planned = fields.Integer(
        string='Total Planned Meals', compute='_compute_fsc_totals', store=True,
    )
    fsc_total_actual = fields.Integer(
        string='Total Actual Meals', compute='_compute_fsc_totals', store=True,
    )
    fsc_total_variance = fields.Integer(
        compute='_compute_fsc_totals', store=True,
    )

    @api.depends('order_line.fsc_planned_qty', 'order_line.fsc_actual_qty')
    def _compute_fsc_totals(self):
        for so in self:
            so.fsc_total_planned = sum(so.order_line.mapped('fsc_planned_qty'))
            so.fsc_total_actual = sum(so.order_line.mapped('fsc_actual_qty'))
            so.fsc_total_variance = so.fsc_total_actual - so.fsc_total_planned

    @api.onchange('partner_id')
    def _onchange_partner_set_site(self):
        if self.partner_id and self.partner_id.fsc_default_site_id:
            self.fsc_site_id = self.partner_id.fsc_default_site_id


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    fsc_shift_id = fields.Many2one('catering.meal.shift', string='Shift')
    fsc_meal_date = fields.Date(string='Meal Date')
    fsc_planned_qty = fields.Integer(string='Planned Qty', default=0)
    fsc_actual_qty = fields.Integer(string='Actual Qty', default=0)
    fsc_variance_qty = fields.Integer(
        compute='_compute_fsc_variance', store=True,
    )
    fsc_variance_pct = fields.Float(
        compute='_compute_fsc_variance', store=True,
    )
    fsc_customer_recipe_id = fields.Many2one(
        'catering.customer.recipe', string='Customer Recipe',
        domain="[('meal_product_id', '=', product_id), ('state', '=', 'active')]",
    )
    fsc_variance_reason = fields.Char(string='Variance Reason')

    @api.depends('fsc_planned_qty', 'fsc_actual_qty')
    def _compute_fsc_variance(self):
        for ln in self:
            ln.fsc_variance_qty = (ln.fsc_actual_qty or 0) - (ln.fsc_planned_qty or 0)
            ln.fsc_variance_pct = (
                100.0 * ln.fsc_variance_qty / ln.fsc_planned_qty
                if ln.fsc_planned_qty else 0.0
            )
