from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class CateringCustomerRecipe(models.Model):
    """Per-customer portion override for a meal product.

    Spec rule 4: when exploding NVL the priority must be:
        SO Override > Customer Recipe > BOM Master

    This model implements the Customer Recipe level. The SO Override level
    is deferred to MVP 1.1.
    """
    _name = 'catering.customer.recipe'
    _description = 'Catering Customer Recipe'
    _inherit = ['fsc.audit.mixin', 'mail.thread']
    _order = 'effective_from desc, id desc'

    name = fields.Char(string='Reference', required=True, copy=False, default='New')
    customer_id = fields.Many2one(
        'res.partner', string='Customer', required=True, tracking=True,
        domain=[('customer_rank', '>', 0)],
    )
    site_id = fields.Many2one(
        'catering.site', string='Site',
        domain="[('customer_id', '=', customer_id)]",
        help='Leave blank for "any site of this customer".',
    )
    meal_product_id = fields.Many2one(
        'product.product', string='Meal Product', required=True,
        domain="[('fsc_product_type', '=', 'finished')]",
    )
    base_bom_id = fields.Many2one(
        'mrp.bom', string='Base BOM (Master)',
        help='Master BOM this recipe overrides. Auto-resolved if not set.',
    )
    effective_from = fields.Date(string='Effective From', default=fields.Date.context_today,
                                 required=True, tracking=True)
    effective_to = fields.Date(string='Effective To', tracking=True)
    state = fields.Selection(
        [('draft', 'Draft'),
         ('active', 'Active'),
         ('archived', 'Archived')],
        default='draft', required=True, tracking=True,
    )
    line_ids = fields.One2many(
        'catering.customer.recipe.line', 'recipe_id',
        string='Ingredients', copy=True,
    )
    notes = fields.Text()

    _fsc_audit_fields = ('state', 'effective_from', 'effective_to')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'catering.customer.recipe') or 'New'
        return super().create(vals_list)

    @api.constrains('effective_from', 'effective_to')
    def _check_effective_window(self):
        for rec in self:
            if rec.effective_to and rec.effective_from > rec.effective_to:
                raise ValidationError(_(
                    'Effective From (%s) must be on or before Effective To (%s).',
                    rec.effective_from, rec.effective_to,
                ))

    def action_activate(self):
        self.write({'state': 'active'})

    def action_archive_recipe(self):
        self.write({'state': 'archived'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    @api.model
    def _resolve_recipe(self, customer, meal_product, on_date=None, site=None):
        """Return the active customer recipe applicable on a given date.

        Search order: customer+site match > customer-only match.
        Returns an empty recordset if no recipe is configured.
        """
        on_date = on_date or fields.Date.context_today(self)
        domain_common = [
            ('customer_id', '=', customer.id),
            ('meal_product_id', '=', meal_product.id),
            ('state', '=', 'active'),
            ('effective_from', '<=', on_date),
            '|', ('effective_to', '=', False), ('effective_to', '>=', on_date),
        ]
        if site:
            site_match = self.search(
                domain_common + [('site_id', '=', site.id)], limit=1)
            if site_match:
                return site_match
        return self.search(domain_common + [('site_id', '=', False)], limit=1)


class CateringCustomerRecipeLine(models.Model):
    _name = 'catering.customer.recipe.line'
    _description = 'Catering Customer Recipe Line'
    _order = 'recipe_id, sequence, id'

    recipe_id = fields.Many2one(
        'catering.customer.recipe', required=True, ondelete='cascade',
    )
    sequence = fields.Integer(default=10)
    ingredient_id = fields.Many2one(
        'product.product', string='Ingredient', required=True,
        help='Raw or semi-finished product. NOT the meal itself.',
    )
    qty_per_serving = fields.Float(
        string='Qty / Serving', required=True, default=0.0,
        help='Quantity of this ingredient per single meal serving.',
    )
    uom_id = fields.Many2one('uom.uom', string='UoM', required=True)
    note = fields.Char()

    @api.onchange('ingredient_id')
    def _onchange_ingredient(self):
        if self.ingredient_id and not self.uom_id:
            self.uom_id = self.ingredient_id.uom_id
