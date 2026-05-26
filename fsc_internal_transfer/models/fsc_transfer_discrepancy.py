from odoo import api, fields, models


class FscTransferDiscrepancy(models.Model):
    _name = 'fsc.transfer.discrepancy'
    _description = 'FSC Internal Transfer Discrepancy'
    _inherit = ['fsc.audit.mixin', 'mail.thread']
    _order = 'create_date desc, id desc'

    picking_id = fields.Many2one('stock.picking', string='Picking', required=True,
                                 ondelete='cascade', index=True)
    product_id = fields.Many2one('product.product', string='Product', required=True, index=True)

    warehouse_qty = fields.Float(string='Warehouse Dispatched Qty', required=True)
    kitchen_qty = fields.Float(string='Kitchen Received Qty', required=True)
    discrepancy_qty = fields.Float(string='Discrepancy', compute='_compute_discrepancy', store=True)
    discrepancy_pct = fields.Float(string='Discrepancy (%)',
                                   compute='_compute_discrepancy', store=True)

    warehouse_confirmed_by = fields.Many2one('res.users', string='Warehouse Confirmed By')
    kitchen_confirmed_by = fields.Many2one('res.users', string='Kitchen Confirmed By')
    reason = fields.Text(string='Reason')
    resolution = fields.Selection(
        [('accept_kitchen', 'Accept Kitchen Qty'),
         ('accept_warehouse', 'Accept Warehouse Qty'),
         ('reweigh', 'Re-weigh Required'),
         ('escalate', 'Escalate')],
        string='Resolution',
    )
    state = fields.Selection(
        [('open', 'Open'), ('resolved', 'Resolved')],
        string='State', default='open', required=True, tracking=True,
    )

    _fsc_audit_fields = ('warehouse_qty', 'kitchen_qty', 'resolution', 'state')

    @api.depends('warehouse_qty', 'kitchen_qty')
    def _compute_discrepancy(self):
        for rec in self:
            rec.discrepancy_qty = (rec.kitchen_qty or 0.0) - (rec.warehouse_qty or 0.0)
            rec.discrepancy_pct = (
                100.0 * rec.discrepancy_qty / rec.warehouse_qty if rec.warehouse_qty else 0.0
            )
