{
    'name': 'Quản lý Quyết định Nhân sự',
    'version': '18.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Quyết định bổ nhiệm, điều chuyển, điều chỉnh lương, khen thưởng, kỷ luật, chấm dứt HĐ',
    'author': 'SHT',
    'depends': ['hr', 'hr_contract', 'mail'],
    'data': [
        'security/hr_decision_vn_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
        'views/hr_vn_decision_views.xml',
        'views/hr_employee_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
