{
    'name': 'Ký số Nhân sự',
    'version': '18.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Quản lý hồ sơ ký số — HĐ lao động, quyết định, phụ lục',
    'author': 'SHT',
    'depends': ['hr', 'mail'],
    'data': [
        'security/hr_digital_sign_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
        'views/hr_sign_request_views.xml',
        'views/hr_sign_template_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
