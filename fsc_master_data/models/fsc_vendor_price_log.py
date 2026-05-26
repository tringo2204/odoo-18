from odoo import fields, models


class FscVendorPriceLog(models.Model):
    _name = 'fsc.vendor.price.log'
    _description = 'FSC Vendor Price Log'
    _order = 'log_date desc, id desc'

    partner_id = fields.Many2one(
        'res.partner', string='Vendor', required=True, index=True,
        ondelete='cascade', domain=[('supplier_rank', '>', 0)],
    )
    product_id = fields.Many2one(
        'product.product', string='Product', required=True, index=True,
        ondelete='restrict',
    )
    uom_id = fields.Many2one('uom.uom', string='UoM', required=True)
    price_unit = fields.Float(string='Unit Price', required=True)
    currency_id = fields.Many2one(
        'res.currency', string='Currency', required=True,
        default=lambda self: self.env.company.currency_id,
    )
    log_date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    source = fields.Selection(
        [('po', 'Purchase Order'),
         ('rfq', 'RFQ'),
         ('manual', 'Manual Entry')],
        string='Source', default='manual', required=True,
    )
    source_ref = fields.Char(string='Source Reference')
    note = fields.Text(string='Note')
