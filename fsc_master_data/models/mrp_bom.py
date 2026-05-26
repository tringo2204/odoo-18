from odoo import fields, models


class MrpBom(models.Model):
    _inherit = ['mrp.bom', 'fsc.audit.mixin']
    _name = 'mrp.bom'

    fsc_expected_yield = fields.Float(
        string='Expected Yield (%)',
        help='Expected output ratio for this BOM. Used by preprocess loss tracking.',
        default=100.0,
    )
    fsc_expected_loss = fields.Float(
        string='Expected Loss (%)',
        help='Acceptable loss percentage during processing.',
        default=0.0,
    )
    fsc_processing_time = fields.Float(
        string='Processing Time (hours)',
        help='Expected time to complete one batch.',
        default=0.0,
    )

    _fsc_audit_fields = (
        'fsc_expected_yield',
        'fsc_expected_loss',
        'fsc_processing_time',
    )
