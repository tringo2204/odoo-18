from odoo import fields, models


class FscMakeBuyDecision(models.Model):
    _name = 'fsc.make.buy.decision'
    _description = 'FSC Make-vs-Buy Decision'
    _inherit = ['fsc.audit.mixin']
    _order = 'create_date desc, id desc'

    consolidation_line_id = fields.Many2one(
        'fsc.consolidation.line', string='Consolidation Line',
        required=True, ondelete='cascade', index=True,
    )
    product_id = fields.Many2one('product.product', string='Product', required=True, index=True)
    qty = fields.Float(string='Required Qty', required=True)

    cost_make = fields.Float(string='Estimated Make Cost')
    cost_buy = fields.Float(string='Estimated Buy Cost')
    capacity_available = fields.Boolean(string='Internal Capacity Available')

    decision = fields.Selection(
        [('make', 'Manufacture'),
         ('buy', 'Purchase'),
         ('mixed', 'Mixed')],
        string='Decision',
    )
    decision_reason = fields.Text(string='Decision Reason')
    chosen_vendor_id = fields.Many2one('res.partner', string='Chosen Vendor',
                                       domain=[('supplier_rank', '>', 0)])

    _fsc_audit_fields = ('decision', 'chosen_vendor_id')
