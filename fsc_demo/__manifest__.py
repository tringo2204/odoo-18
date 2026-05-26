{
    'name': 'FSC Demo Data + End-to-End Tests',
    'version': '18.0.1.0.0',
    'category': 'Food Supply Chain',
    'summary': 'Demo data (vendor, products, BOMs) and integration tests',
    'description': """
Installs a small set of demo records (Vietnamese industrial-catering theme) so
the Food Supply Chain modules can be exercised in the UI without any manual
setup:
  * Vendor: Công ty Rau Xanh ABC
  * Products: Rau muống tươi (raw), Rau muống sạch (semi), Cơm rau muống (meal)
  * BOMs linking the three levels with expected yields/losses
  * A dedicated picking type "WH → Kitchen" with FSC dual confirmation enabled

Also ships a single end-to-end integration test that exercises the full chain:
consolidation → procurement (PO) → preprocess MO + loss tracking →
cooking MO + cooking batch + meal cost.

Install this module to play with the system in the UI. Demo records are
idempotent (matched by default_code / name) so re-installing is safe.
    """,
    'author': 'FSC',
    'depends': [
        'fsc_demand_consolidation',
        'fsc_procurement_engine',
        'fsc_preprocess_mrp',
        'fsc_kitchen_mrp',
        'fsc_costing_engine',
        'fsc_internal_transfer',
    ],
    'data': [],
    'post_init_hook': '_post_init_hook',
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
