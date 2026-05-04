# -*- coding: utf-8 -*-
"""Migration: fix leave_type_absence request_unit to 'hour' for correct duration display (#64)."""


def migrate(cr, version):
    cr.execute("""
        UPDATE hr_leave_type
        SET request_unit = 'hour'
        WHERE id IN (
            SELECT res_id FROM ir_model_data
            WHERE module = 'hr_request_vn' AND name = 'leave_type_absence'
        )
        AND request_unit != 'hour'
    """)
