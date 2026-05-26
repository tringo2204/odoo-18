{
    'name': 'FSC Procurement Engine',
    'version': '18.0.1.0.0',
    'category': 'Food Supply Chain',
    'summary': 'Make-vs-buy decision, vendor ranking, auto RFQ generation',
    'description': """
Procurement engine consuming consolidation lines:
  * fsc.make.buy.decision — per-line decision record (cost_make, cost_buy, capacity, decision).
  * Vendor selection via product._select_seller(); UoM-aware price conversion.
  * Auto-generate RFQ (purchase.order) from locked consolidation lines, grouping
    multiple lines under a single PO per (company, vendor) pair.
  * Auto-generate MO when product is flagged as internal supplier with a BOM.
  * Cron picks up 'open' consolidation lines every 10 minutes.
    """,
    'author': 'FSC',
    'depends': [
        'fsc_demand_consolidation',
        'purchase',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'views/fsc_consolidation_line_views.xml',
        'views/fsc_make_buy_decision_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
