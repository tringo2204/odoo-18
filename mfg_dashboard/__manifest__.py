{
    'name': 'Manufacturing Dashboard',
    'version': '18.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Real-time KPI dashboard for manufacturing operations',
    'description': """
Requires Odoo Enterprise: quality_control, mrp_plm.
    """,
    'depends': ['mrp', 'mrp_workorder', 'quality_control', 'maintenance', 'mrp_plm'],
    'data': [
        'security/ir.model.access.csv',
        'views/dashboard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'mfg_dashboard/static/src/dashboard.js',
            'mfg_dashboard/static/src/dashboard.xml',
            'mfg_dashboard/static/src/dashboard.scss',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
