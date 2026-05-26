{
    'name': 'FSC Demand Consolidation',
    'version': '18.0.1.0.0',
    'category': 'Food Supply Chain',
    'summary': 'Consolidate multi-kitchen demand into optimal procurement units',
    'description': """
Demand consolidation engine — the core differentiator of the FSC ERP.

Groups demand from multiple kitchens/locations by (product, required_date, uom)
into fsc.consolidation.line records. The stock.rule._run_buy() override pushes
demand into consolidation lines instead of creating an RFQ directly when the
buy rule has fsc_consolidate=True. A debounce cron then transitions accumulating
lines to 'open' state, ready for the procurement engine to convert into RFQs.

Urgent procurements (priority=1) bypass consolidation and go straight to the
standard RFQ flow.
    """,
    'author': 'FSC',
    'depends': [
        'fsc_master_data',
        'stock',
        'purchase',
        'purchase_stock',
        'mrp',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
        'data/ir_cron.xml',
        'views/fsc_consolidation_line_views.xml',
        'views/stock_rule_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
