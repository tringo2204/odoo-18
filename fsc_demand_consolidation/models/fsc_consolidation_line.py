from odoo import api, fields, models


class FscConsolidationLine(models.Model):
    _name = 'fsc.consolidation.line'
    _description = 'FSC Demand Consolidation Line'
    _inherit = ['fsc.audit.mixin', 'mail.thread']
    _order = 'required_date, product_id'

    name = fields.Char(string='Reference', required=True, copy=False,
                       default=lambda self: self._default_name(), index=True)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True, index=True,
        default=lambda self: self.env.company,
    )
    product_id = fields.Many2one('product.product', string='Product', required=True, index=True)
    uom_id = fields.Many2one('uom.uom', string='UoM', required=True)
    total_qty = fields.Float(string='Total Qty', required=True)
    required_date = fields.Datetime(string='Required Date', required=True, index=True)

    origin = fields.Char(string='Source', help='Comma-separated origins of merged demand.')
    demand_move_ids = fields.Many2many(
        'stock.move', string='Source Demand Moves',
        help='Downstream stock moves whose demand this line satisfies.',
    )
    source_location_ids = fields.Many2many(
        'stock.location', string='Source Locations',
        help='Destination locations of original demand (kitchens).',
    )

    state = fields.Selection(
        [('draft', 'Accumulating'),
         ('open', 'Open for Processing'),
         ('locked', 'Locked'),
         ('rfq_created', 'RFQ Created'),
         ('mo_created', 'MO Created'),
         ('done', 'Done'),
         ('cancel', 'Cancelled')],
        string='State', default='draft', required=True, tracking=True,
    )
    urgency = fields.Selection(
        [('normal', 'Normal'), ('urgent', 'Urgent')],
        string='Urgency', default='normal', required=True,
    )

    purchase_order_id = fields.Many2one('purchase.order', string='Generated PO', readonly=True)
    production_id = fields.Many2one('mrp.production', string='Generated MO', readonly=True)

    _fsc_audit_fields = ('total_qty', 'required_date', 'state', 'urgency')

    @api.model
    def _default_name(self):
        return self.env['ir.sequence'].next_by_code('fsc.consolidation.line') or 'New'

    def action_open(self):
        self.filtered(lambda r: r.state == 'draft').write({'state': 'open'})

    def action_lock(self):
        self.filtered(lambda r: r.state == 'open').write({'state': 'locked'})

    def action_cancel(self):
        self.filtered(lambda r: r.state not in ('done', 'cancel')).write({'state': 'cancel'})

    def action_reset_to_draft(self):
        self.filtered(lambda r: r.state == 'cancel').write({'state': 'draft'})

    @api.model
    def _cron_consolidate_demand(self):
        """Transition draft lines whose accumulation window has elapsed to 'open'.

        Debounce window is governed by ir.config_parameter
        `fsc.consolidation.debounce_minutes` (default 15). Lines stay in draft
        until no new demand has been merged into them for this duration.
        """
        from datetime import timedelta
        ICP = self.env['ir.config_parameter'].sudo()
        debounce = int(ICP.get_param('fsc.consolidation.debounce_minutes', '15'))
        cutoff = fields.Datetime.now() - timedelta(minutes=debounce)
        to_open = self.sudo().search([
            ('state', '=', 'draft'),
            ('write_date', '<=', cutoff),
        ])
        if to_open:
            to_open.write({'state': 'open'})
        return len(to_open)
