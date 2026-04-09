# -*- coding: utf-8 -*-
{
    'name': 'SHT HR Reward & Discipline',
    'version': '18.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Employee Reward and Discipline Management',
    'description': 'Manage employee rewards (khen thưởng) and disciplinary actions (kỷ luật) with decision tracking.',
    'author': 'SHT',
    'depends': ['hr'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sht_hr_rd_type_data.xml',
        'views/sht_hr_rd_views.xml',
        'views/sht_hr_rd_type_views.xml',
        'views/hr_employee_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
