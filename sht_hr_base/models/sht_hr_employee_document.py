from odoo import _, models, fields, api
from odoo.exceptions import ValidationError


class ShtHrEmployeeDocument(models.Model):
    _name = 'sht.hr.employee.document'
    _description = 'Employee Document'
    _order = 'employee_id, name'

    name = fields.Char(string='Document Name', required=True)
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        ondelete='cascade',
        index=True,
    )
    document_type_id = fields.Many2one(
        'sht.hr.document.type',
        string='Document Type',
        required=True,
        ondelete='restrict',
    )
    issue_date = fields.Date(string='Issue Date')
    expiry_date = fields.Date(string='Expiry Date')
    attachment = fields.Binary(string='Attachment')
    attachment_filename = fields.Char(string='Attachment Filename')
    state = fields.Selection(
        [
            ('valid', 'Valid'),
            ('expired', 'Expired'),
            ('missing', 'Missing'),
        ],
        string='State',
        default='valid',
        required=True,
    )
    note = fields.Text(string='Note')
    is_expired = fields.Boolean(
        string='Is Expired',
        compute='_compute_is_expired',
        store=True,
    )

    @api.depends('expiry_date')
    def _compute_is_expired(self):
        today = fields.Date.today()
        for doc in self:
            doc.is_expired = bool(doc.expiry_date and doc.expiry_date < today)

    @api.depends('is_expired', 'expiry_date')
    def _compute_state_from_expiry(self):
        """#107: auto-sync state to 'expired' when is_expired becomes True."""
        for doc in self:
            if doc.is_expired and doc.state == 'valid':
                doc.state = 'expired'

    def write(self, vals):
        res = super().write(vals)
        # #107: when expiry_date changes, sync state
        if 'expiry_date' in vals or 'is_expired' in vals:
            for doc in self:
                if doc.is_expired and doc.state == 'valid':
                    doc.state = 'expired'
                elif not doc.is_expired and doc.state == 'expired':
                    doc.state = 'valid'
        return res

    @api.constrains('issue_date', 'expiry_date')
    def _check_issue_expiry_dates(self):
        for doc in self:
            if doc.issue_date and doc.expiry_date and doc.expiry_date < doc.issue_date:
                raise ValidationError(
                    _('Expiry date cannot be earlier than issue date.')
                )
