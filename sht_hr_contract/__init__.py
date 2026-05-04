# -*- coding: utf-8 -*-
from . import models


def post_init_hook(env):
    """Rename the default Odoo work schedule to Vietnamese (#32)."""
    cal = env.ref('resource.resource_calendar_std', raise_if_not_found=False)
    if cal and cal.name == 'Standard 40 hours/week':
        cal.sudo().write({'name': 'Tiêu chuẩn 40 giờ/tuần'})
