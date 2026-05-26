from odoo import api, fields, models


class CateringMealShift(models.Model):
    _name = 'catering.meal.shift'
    _description = 'Catering Meal Shift'
    _order = 'sequence, id'
    _rec_name = 'name'

    name = fields.Char(string='Shift Name', required=True, translate=True)
    code = fields.Char(string='Code', required=True, help='Stable code (BREAKFAST, LUNCH, ...)')
    sequence = fields.Integer(default=10)
    start_time = fields.Float(string='Start Time', help='Decimal hour, e.g. 6.5 = 06:30.')
    end_time = fields.Float(string='End Time')
    cutoff_offset_hours = fields.Float(
        string='Cut-off Offset (h)',
        default=12.0,
        help='How many hours before shift start the demand is locked. '
             'Changes after cut-off require special handling.',
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Shift code must be unique.'),
    ]

    @api.depends('name', 'start_time', 'end_time')
    def _compute_display_name(self):
        for s in self:
            if s.start_time and s.end_time:
                s.display_name = f'{s.name} ({s.start_time:04.1f}-{s.end_time:04.1f})'
            else:
                s.display_name = s.name
