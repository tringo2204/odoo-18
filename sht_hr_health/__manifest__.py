# -*- coding: utf-8 -*-
{
    'name': 'HR Health Records',
    'version': '18.0.1.0.0',
    'summary': 'Quản lý hồ sơ sức khoẻ và khám sức khoẻ định kỳ cho nhân viên',
    'category': 'Human Resources',
    'author': 'SHT',
    'depends': ['hr', 'sht_hr_base'],
    'data': [
        'security/sht_hr_health_security.xml',
        'security/ir.model.access.csv',
        'views/sht_hr_health_views.xml',
        'views/hr_employee_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
