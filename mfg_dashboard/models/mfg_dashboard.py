from odoo import models, api, fields
from datetime import date


class MfgDashboard(models.AbstractModel):
    _name = 'mfg.dashboard'
    _description = 'Manufacturing Dashboard'

    @api.model
    def get_dashboard_data(self):
        today = date.today()
        month_start = today.replace(day=1).strftime('%Y-%m-%d')
        now = fields.Datetime.now()

        # --- Production Orders ---
        MO = self.env['mrp.production']
        production = {
            'draft':     MO.search_count([('state', '=', 'draft')]),
            'confirmed': MO.search_count([('state', '=', 'confirmed')]),
            'progress':  MO.search_count([('state', 'in', ['progress', 'to_close'])]),
            'done':      MO.search_count([('state', '=', 'done'), ('date_finished', '>=', month_start)]),
            'late':      MO.search_count([
                ('state', 'in', ['confirmed', 'progress', 'to_close']),
                ('date_deadline', '<', now),
                ('date_deadline', '!=', False),
            ]),
        }

        # --- Work Orders ---
        WO = self.env['mrp.workorder']
        workorders = {
            'ready':    WO.search_count([('state', '=', 'ready')]),
            'progress': WO.search_count([('state', '=', 'progress')]),
            'pending':  WO.search_count([('state', '=', 'pending')]),
            'waiting':  WO.search_count([('state', '=', 'waiting')]),
        }

        # --- Quality Checks ---
        QC = self.env['quality.check']
        quality = {
            'pending': QC.search_count([('quality_state', '=', 'none')]),
            'failed':  QC.search_count([('quality_state', '=', 'fail')]),
            'passed':  QC.search_count([('quality_state', '=', 'pass'), ('create_date', '>=', month_start)]),
        }

        # --- Quality Alerts ---
        QA = self.env['quality.alert']
        alerts = {
            'open':        QA.search_count([('stage_id.done', '=', False)]),
            'critical':    QA.search_count([('stage_id.done', '=', False), ('priority', '=', '1')]),
        }

        # --- Maintenance Requests ---
        MR = self.env['maintenance.request']
        maintenance = {
            'open':     MR.search_count([('stage_id.done', '=', False), ('archive', '=', False)]),
            'urgent':   MR.search_count([
                ('stage_id.done', '=', False),
                ('priority', '=', '3'),
                ('archive', '=', False),
            ]),
            'done':     MR.search_count([('stage_id.done', '=', True), ('write_date', '>=', month_start)]),
        }

        # --- PLM / ECO ---
        ECO = self.env['mrp.eco']
        ecos = {
            'new':      ECO.search_count([('state', '=', 'confirmed')]),
            'progress': ECO.search_count([('state', '=', 'progress')]),
            'done':     ECO.search_count([('state', '=', 'done'), ('write_date', '>=', month_start)]),
        }

        return {
            'production':  production,
            'workorders':  workorders,
            'quality':     quality,
            'alerts':      alerts,
            'maintenance': maintenance,
            'ecos':        ecos,
            'month_label': today.strftime('%B %Y'),
        }
