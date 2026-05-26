from odoo import fields, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    fsc_warehouse_qty = fields.Float(
        string='FSC Warehouse Dispatched Qty', readonly=True, copy=False,
        help='Quantity snapshot taken when the warehouse user confirms dispatch.',
    )
    fsc_kitchen_qty = fields.Float(
        string='FSC Kitchen Received Qty', readonly=True, copy=False,
        help='Quantity snapshot taken when the kitchen user confirms receipt.',
    )
