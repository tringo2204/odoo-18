from odoo import fields, models


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

    _fsc_audit_fields = (
        'fsc_product_type',
        'fsc_processing_type',
        'fsc_yield_expected',
        'fsc_loss_threshold',
        'fsc_is_internal_supplier',
    )
