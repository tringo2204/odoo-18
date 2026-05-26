from odoo import api, fields, models


class FscReceiptDeviation(models.Model):
    _name = 'fsc.receipt.deviation'
    _description = 'FSC Receipt Deviation'
    _inherit = ['fsc.audit.mixin', 'mail.thread']
    _order = 'create_date desc, id desc'

    picking_id = fields.Many2one('stock.picking', string='Picking', required=True,
                                 ondelete='cascade', index=True)
    move_line_id = fields.Many2one('stock.move.line', string='Move Line', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True, index=True)

    expected_qty = fields.Float(string='Expected Qty', required=True)
    actual_qty = fields.Float(string='Actual Qty', required=True)
    deviation_qty = fields.Float(string='Deviation', compute='_compute_deviation', store=True)
    deviation_pct = fields.Float(string='Deviation (%)', compute='_compute_deviation', store=True)

    deviation_type = fields.Selection(
        [('short', 'Short Delivery'),
         ('over', 'Over Delivery'),
         ('wrong_lot', 'Wrong Lot'),
         ('damage', 'Damaged'),
         ('qc_fail', 'QC Failed')],
        string='Type', required=True,
    )
    reason = fields.Text(string='Reason')
    photo = fields.Binary(string='Photo', attachment=True)
    reviewer_id = fields.Many2one('res.users', string='Reviewer')

    state = fields.Selection(
        [('open', 'Open'), ('accepted', 'Accepted'), ('rejected', 'Rejected')],
        string='State', default='open', required=True, tracking=True,
    )

    _fsc_audit_fields = ('actual_qty', 'deviation_type', 'state')

    @api.depends('expected_qty', 'actual_qty')
    def _compute_deviation(self):
        for rec in self:
            rec.deviation_qty = (rec.actual_qty or 0.0) - (rec.expected_qty or 0.0)
            rec.deviation_pct = (
                100.0 * rec.deviation_qty / rec.expected_qty if rec.expected_qty else 0.0
            )
