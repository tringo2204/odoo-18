# -*- coding: utf-8 -*-

{
    'name': 'SHT HR Training',
    'version': '18.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Employee Training Management',
    'description': 'Manage training courses, enrollment, and completion tracking for employees.',
    'author': 'SHT',
    'depends': ['hr', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/training_course_data.xml',
        'views/sht_hr_training_plan_views.xml',
        'views/sht_hr_training_course_views.xml',
        'views/sht_hr_training_views.xml',
        'views/hr_employee_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
