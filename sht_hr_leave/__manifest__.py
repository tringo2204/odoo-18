# -*- coding: utf-8 -*-
{
    'name': 'Vietnam HR Leave',
    'version': '18.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Vietnam labor law leave types and seniority bonus hints',
    'depends': ['hr_holidays'],
    'data': [
        'data/sht_hr_leave_type_data.xml',
        'views/hr_leave_type_views.xml',
        'views/hr_leave_allocation_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
