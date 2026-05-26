from odoo import api, fields, models


FSC_PRODUCT_TYPE = [
    ('raw', 'Raw'),
    ('semi_finished', 'Semi-finished'),
    ('finished', 'Finished'),
]

FSC_PROCESSING_TYPE = [
    ('none', 'None'),
    ('preprocess', 'Preprocess'),
    ('cooking', 'Cooking'),
    ('thawing', 'Thawing'),
]


class ProductTemplate(models.Model):
    _inherit = ['product.template', 'fsc.audit.mixin']
    _name = 'product.template'

    fsc_product_type = fields.Selection(
        FSC_PRODUCT_TYPE,
        string='FSC Product Type',
        help='Classification used by the FSC supply chain: raw material, semi-finished output of preprocess, or finished meal.',
    )
    fsc_processing_type = fields.Selection(
        FSC_PROCESSING_TYPE,
        string='Processing Type',
        default='none',
    )
    fsc_yield_expected = fields.Float(
        string='Expected Yield (%)',
        help='Expected output ratio after processing. 100 = no loss.',
        default=100.0,
    )
    fsc_loss_threshold = fields.Float(
        string='Loss Threshold (%)',
        help='Alert when actual loss exceeds this percentage.',
        default=0.0,
    )
    fsc_is_internal_supplier = fields.Boolean(
        string='Internal Supplier',
        help='Can be produced internally (eligible for make-vs-buy comparison).',
        default=False,
    )
    fsc_use_consolidation = fields.Boolean(
        string='Use Demand Consolidation',
        help='When set, purchases for this product are intercepted by the FSC '
             'consolidation engine instead of generating an RFQ directly. The '
             'consolidation cron then groups demand across kitchens.',
        default=False,
    )

    _fsc_audit_fields = (
        'fsc_product_type',
        'fsc_processing_type',
        'fsc_yield_expected',
        'fsc_loss_threshold',
        'fsc_is_internal_supplier',
        'fsc_use_consolidation',
    )

    @api.onchange('fsc_product_type')
    def _onchange_fsc_product_type(self):
        """Default raw products to consolidation; clear it for finished meals."""
        if self.fsc_product_type == 'raw':
            self.fsc_use_consolidation = True
        elif self.fsc_product_type == 'finished':
            self.fsc_use_consolidation = False
