from odoo import fields, models


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    fsc_dual_confirm = fields.Boolean(
        string='FSC Dual Confirmation',
        help='Require two-step warehouse-then-kitchen confirmation for pickings '
             'of this operation type. Discrepancies between dispatched and '
             'received quantities are captured automatically.',
    )
