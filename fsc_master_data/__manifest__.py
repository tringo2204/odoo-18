{
    'name': 'FSC Master Data',
    'version': '18.0.1.0.0',
    'category': 'Food Supply Chain',
    'summary': 'Product / BOM / Vendor / Location extensions for industrial catering ERP',
    'description': """
Master data layer for the Food Supply Chain ERP:
  * product.template: product_type (raw/semi/finished), processing_type, yield_expected,
    loss_threshold, is_internal_supplier.
  * mrp.bom: expected_yield, expected_loss, processing_time.
  * res.partner (vendor): on_time_rate, defect_rate, rating_score, price history.
  * fsc.vendor.price.log: append-only vendor price history.
  * fsc.location.config: seed for warehouse location structure (INPUT/QC/RAU/THIT/...).
    """,
    'author': 'FSC',
    'depends': [
        'fsc_audit_log',
        'product',
        'stock',
        'purchase',
        'mrp',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
        'views/mrp_bom_views.xml',
        'views/res_partner_views.xml',
        'views/fsc_vendor_price_log_views.xml',
        'views/res_config_settings_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
