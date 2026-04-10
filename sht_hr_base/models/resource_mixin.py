import pytz

from odoo import api, models, _
from odoo.exceptions import ValidationError

VALID_TIMEZONES = set(pytz.all_timezones)


class ResourceResource(models.Model):
    _inherit = 'resource.resource'

    @api.constrains('tz')
    def _check_timezone(self):
        for rec in self:
            if rec.tz and rec.tz not in VALID_TIMEZONES:
                raise ValidationError(
                    _('Timezone "%s" không hợp lệ cho resource "%s".') % (rec.tz, rec.name)
                )


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    @api.constrains('tz')
    def _check_timezone(self):
        for rec in self:
            if rec.tz and rec.tz not in VALID_TIMEZONES:
                raise ValidationError(
                    _('Timezone "%s" không hợp lệ cho lịch "%s".') % (rec.tz, rec.name)
                )
