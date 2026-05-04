{
    'name': 'Chấm công ca làm việc',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Attendances',
    'summary': 'Xác thực ca làm, đánh dấu OT, đưa giờ OT vào bảng lương',
    'author': 'SHT',
    'depends': ['hr_attendance', 'hr_payroll'],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_attendance_vn_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
