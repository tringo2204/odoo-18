from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class CateringMenuPlan(models.Model):
    _name = 'catering.menu.plan'
    _description = 'Catering Weekly Menu Plan'
    _inherit = ['fsc.audit.mixin', 'mail.thread']
    _order = 'week_start_date desc, id desc'

    name = fields.Char(required=True, copy=False, default='New')
    customer_id = fields.Many2one(
        'res.partner', string='Customer', required=True, tracking=True,
        domain=[('customer_rank', '>', 0)],
    )
    site_id = fields.Many2one(
        'catering.site', string='Site', tracking=True,
        domain="[('customer_id', '=', customer_id)]",
    )
    week_start_date = fields.Date(
        string='Week Start (Mon)', required=True, tracking=True,
        default=lambda self: self._default_week_start(),
    )
    week_end_date = fields.Date(
        string='Week End (Sun)', compute='_compute_week_end', store=True,
    )
    state = fields.Selection(
        [('draft', 'Draft'),
         ('submitted', 'Submitted'),
         ('approved', 'Approved'),
         ('locked', 'Locked'),
         ('changed', 'Change Requested'),
         ('cancelled', 'Cancelled')],
        default='draft', required=True, tracking=True,
    )
    line_ids = fields.One2many(
        'catering.menu.plan.line', 'plan_id', string='Menu Lines', copy=True,
    )
    sale_order_ids = fields.One2many(
        'sale.order', 'fsc_menu_plan_id', string='Generated Sales Orders',
    )
    sale_order_count = fields.Integer(compute='_compute_sale_order_count')
    line_count = fields.Integer(compute='_compute_line_count')
    notes = fields.Text()

    _fsc_audit_fields = ('state', 'week_start_date')

    @api.model
    def _default_week_start(self):
        today = fields.Date.context_today(self)
        # Monday this week
        return today - timedelta(days=today.weekday())

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'catering.menu.plan') or 'New'
        return super().create(vals_list)

    @api.depends('week_start_date')
    def _compute_week_end(self):
        for plan in self:
            plan.week_end_date = (
                plan.week_start_date + timedelta(days=6)
                if plan.week_start_date else False
            )

    @api.depends('sale_order_ids')
    def _compute_sale_order_count(self):
        for p in self:
            p.sale_order_count = len(p.sale_order_ids)

    @api.depends('line_ids')
    def _compute_line_count(self):
        for p in self:
            p.line_count = len(p.line_ids)

    @api.constrains('week_start_date')
    def _check_monday(self):
        for plan in self:
            if plan.week_start_date and plan.week_start_date.weekday() != 0:
                raise ValidationError(_(
                    'Week Start must be a Monday. Got %s (weekday=%s).',
                    plan.week_start_date, plan.week_start_date.weekday(),
                ))

    # --- State transitions ---
    def action_submit(self):
        for p in self:
            if not p.line_ids:
                raise UserError(_('Cannot submit %s: no menu lines.', p.name))
        self.write({'state': 'submitted'})

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_lock(self):
        self.write({'state': 'locked'})

    def action_request_change(self):
        self.write({'state': 'changed'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    # --- SO generation ---
    def action_generate_sales_orders(self):
        """Create one SO per (customer, site, meal_date), with lines per line.

        Skips lines that already generated an SO line. Idempotent — safe to
        re-run after adding more menu lines.
        """
        for plan in self:
            if plan.state not in ('approved', 'locked'):
                raise UserError(_(
                    'Menu plan %s must be approved or locked before generating SOs '
                    '(current state: %s).', plan.name, plan.state,
                ))
            plan._generate_sales_orders()

    def _generate_sales_orders(self):
        self.ensure_one()
        SO = self.env['sale.order']
        SOL = self.env['sale.order.line']

        # Group lines by date.
        lines_by_date = {}
        for ln in self.line_ids.filtered(lambda x: not x.sale_order_line_id):
            lines_by_date.setdefault(ln.meal_date, []).append(ln)

        for meal_date, lines in sorted(lines_by_date.items()):
            so = SO.search([
                ('fsc_menu_plan_id', '=', self.id),
                ('fsc_meal_date', '=', meal_date),
                ('partner_id', '=', self.customer_id.id),
                ('state', '=', 'draft'),
            ], limit=1)
            if not so:
                so = SO.create({
                    'partner_id': self.customer_id.id,
                    'fsc_menu_plan_id': self.id,
                    'fsc_site_id': self.site_id.id if self.site_id else False,
                    'fsc_meal_date': meal_date,
                    'date_order': fields.Datetime.now(),
                    'commitment_date': fields.Datetime.to_datetime(meal_date),
                    'origin': self.name,
                })
            for ln in lines:
                sol = SOL.create({
                    'order_id': so.id,
                    'product_id': ln.meal_product_id.id,
                    'product_uom_qty': ln.planned_qty,
                    'fsc_shift_id': ln.shift_id.id,
                    'fsc_meal_date': meal_date,
                    'fsc_planned_qty': ln.planned_qty,
                    'fsc_actual_qty': ln.actual_qty,
                    'fsc_customer_recipe_id': ln.customer_recipe_id.id,
                })
                ln.sale_order_line_id = sol.id
        return True

    def action_view_sales_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Generated Sales Orders'),
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [('fsc_menu_plan_id', '=', self.id)],
        }


class CateringMenuPlanLine(models.Model):
    _name = 'catering.menu.plan.line'
    _description = 'Catering Menu Plan Line'
    _order = 'plan_id, meal_date, shift_id, id'

    plan_id = fields.Many2one(
        'catering.menu.plan', required=True, ondelete='cascade',
    )
    plan_customer_id = fields.Many2one(
        related='plan_id.customer_id', store=False, readonly=True,
    )
    meal_date = fields.Date(string='Meal Date', required=True)
    weekday = fields.Char(compute='_compute_weekday', store=True)
    shift_id = fields.Many2one(
        'catering.meal.shift', string='Shift', required=True,
    )
    meal_product_id = fields.Many2one(
        'product.product', string='Meal', required=True,
        domain="[('fsc_product_type', '=', 'finished')]",
    )
    planned_qty = fields.Integer(string='Planned Qty', required=True, default=0)
    actual_qty = fields.Integer(string='Actual Qty', default=0,
                                help='Filled when customer confirms count.')
    variance_qty = fields.Integer(
        string='Variance', compute='_compute_variance', store=True,
    )
    variance_pct = fields.Float(
        string='Variance (%)', compute='_compute_variance', store=True,
    )
    customer_recipe_id = fields.Many2one(
        'catering.customer.recipe', string='Customer Recipe',
        help='Per-customer portion override. Auto-resolved if not set.',
    )
    sale_order_line_id = fields.Many2one(
        'sale.order.line', string='Generated SO Line', readonly=True, copy=False,
    )
    note = fields.Char()

    @api.depends('meal_date')
    def _compute_weekday(self):
        names = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN']
        for ln in self:
            ln.weekday = names[ln.meal_date.weekday()] if ln.meal_date else ''

    @api.depends('planned_qty', 'actual_qty')
    def _compute_variance(self):
        for ln in self:
            ln.variance_qty = (ln.actual_qty or 0) - (ln.planned_qty or 0)
            ln.variance_pct = (
                100.0 * ln.variance_qty / ln.planned_qty
                if ln.planned_qty else 0.0
            )

    @api.constrains('meal_date', 'plan_id')
    def _check_date_in_week(self):
        for ln in self:
            if not (ln.plan_id.week_start_date and ln.plan_id.week_end_date):
                continue
            if not (ln.plan_id.week_start_date <= ln.meal_date <= ln.plan_id.week_end_date):
                raise ValidationError(_(
                    'Meal date %s must fall within plan week %s..%s.',
                    ln.meal_date, ln.plan_id.week_start_date, ln.plan_id.week_end_date,
                ))
