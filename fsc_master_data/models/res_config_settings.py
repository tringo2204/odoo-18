from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    fsc_consolidation_debounce_minutes = fields.Integer(
        string='Consolidation Debounce (minutes)',
        config_parameter='fsc.consolidation.debounce_minutes',
        default=15,
        help='Time the consolidation engine waits without new demand on a line '
             'before transitioning it from "Accumulating" to "Open for processing".',
    )
    fsc_default_loss_threshold_semi = fields.Float(
        string='Default Loss Threshold for Semi-finished (%)',
        config_parameter='fsc.default_loss_threshold.semi',
        default=15.0,
        help='Default value pre-filled when creating a new semi-finished product.',
    )
    fsc_vendor_weight_on_time = fields.Float(
        string='Vendor Rating Weight: On-time',
        config_parameter='fsc.vendor_rating.weight_on_time',
        default=0.4,
    )
    fsc_vendor_weight_price = fields.Float(
        string='Vendor Rating Weight: Price',
        config_parameter='fsc.vendor_rating.weight_price',
        default=0.4,
    )
    fsc_vendor_weight_defect = fields.Float(
        string='Vendor Rating Weight: Defect',
        config_parameter='fsc.vendor_rating.weight_defect',
        default=0.2,
        help='Weights are used by the procurement engine to rank vendors. '
             'Recommended sum = 1.0.',
    )
