# -*- coding: utf-8 -*-
{
    'name': 'SHT HR Recruitment',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Recruitment',
    'summary': 'Headcount planning and recruitment extensions',
    'depends': ['hr_recruitment', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
        'data/ir_cron.xml',
        'views/sht_hr_headcount_plan_views.xml',
        'views/sht_hr_headcount_allocation_views.xml',
        'views/sht_hr_headcount_line_views.xml',
        'views/sht_hr_recruitment_request_views.xml',
        'views/sht_hr_recruitment_campaign_views.xml',
        'views/sht_hr_applicant_evaluation_views.xml',
        'views/hr_applicant_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
