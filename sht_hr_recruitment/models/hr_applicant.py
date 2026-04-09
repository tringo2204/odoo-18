# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    headcount_plan_id = fields.Many2one(
        'sht.hr.headcount.plan',
        string='Headcount Plan',
        domain="['&', '|', ('company_id', '=', False), ('company_id', '=', company_id), ('state', '!=', 'closed')]",
    )
    is_over_budget = fields.Boolean(
        related='headcount_plan_id.is_over_budget',
        string='Over Budget',
    )

    @api.model_create_multi
    def create(self, vals_list):
        applicants = super().create(vals_list)
        for applicant in applicants:
            if applicant.headcount_plan_id and applicant.is_over_budget:
                _logger.warning(
                    'Applicant %s created with headcount plan over budget.',
                    applicant.display_name,
                )
                applicant.activity_schedule(
                    act_type_xmlid='mail.mail_activity_data_warning',
                    summary=_('Headcount over budget'),
                    note=_(
                        'The selected headcount plan is over budget (current headcount exceeds planned).'
                    ),
                    user_id=applicant.user_id.id or self.env.user.id,
                )
        return applicants
