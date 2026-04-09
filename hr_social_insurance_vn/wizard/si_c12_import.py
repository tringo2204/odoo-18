import base64
import io

from odoo import api, fields, models, _
from odoo.exceptions import UserError

try:
    import openpyxl
except ImportError:
    openpyxl = None


class SiC12Import(models.TransientModel):
    _name = 'hr.vn.si.c12.import'
    _description = 'Import tra cứu C12'

    file = fields.Binary(string='File C12 (Excel)', required=True)
    filename = fields.Char(string='Tên file')
    month = fields.Selection([
        ('1', 'Tháng 1'), ('2', 'Tháng 2'), ('3', 'Tháng 3'),
        ('4', 'Tháng 4'), ('5', 'Tháng 5'), ('6', 'Tháng 6'),
        ('7', 'Tháng 7'), ('8', 'Tháng 8'), ('9', 'Tháng 9'),
        ('10', 'Tháng 10'), ('11', 'Tháng 11'), ('12', 'Tháng 12'),
    ], string='Tháng', required=True)
    year = fields.Integer(
        string='Năm', required=True,
        default=lambda self: fields.Date.today().year,
    )

    def action_import(self):
        self.ensure_one()
        if not self.file:
            raise UserError(_('Vui lòng chọn file C12.'))

        data = base64.b64decode(self.file)
        rows = self._parse_file(data)
        if not rows:
            raise UserError(_('File không có dữ liệu hợp lệ.'))

        created = self._create_c12_records(rows)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Import C12 thành công'),
                'message': _('Đã tạo %d bản ghi tra cứu.') % len(created),
                'type': 'success',
                'sticky': False,
            },
        }

    def _parse_file(self, data):
        """Parse Excel C12 file.
        Expected columns: Số sổ BHXH | Tình trạng | BHXH | BHYT | BHTN
        """
        if not openpyxl:
            raise UserError(
                _('Thư viện openpyxl chưa được cài đặt. '
                  'Chạy: pip install openpyxl')
            )
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True)
        ws = wb.active
        rows = []
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row or not row[0]:
                continue
            rows.append({
                'bhxh_number': str(row[0]).strip(),
                'bhxh_status': str(row[1] or ''),
                'bhxh_amount': float(row[2] or 0),
                'bhyt_amount': float(row[3] or 0),
                'bhtn_amount': float(row[4] or 0),
            })
        return rows

    def _create_c12_records(self, rows):
        Employee = self.env['hr.employee']
        C12 = self.env['hr.vn.si.c12.lookup']
        created = C12
        errors = []

        for idx, row in enumerate(rows, start=2):
            employee = Employee.search([
                ('social_insurance_id', '=', row['bhxh_number']),
                ('company_id', '=', self.env.company.id),
            ], limit=1)
            if not employee:
                errors.append(
                    _('Dòng %d: Không tìm thấy NV với số sổ BHXH %s')
                    % (idx, row['bhxh_number'])
                )
                continue

            # Xóa bản ghi cũ cùng tháng/năm/NV nếu có
            existing = C12.search([
                ('employee_id', '=', employee.id),
                ('month', '=', self.month),
                ('year', '=', self.year),
            ])
            existing.unlink()

            created |= C12.create({
                'employee_id': employee.id,
                'month': self.month,
                'year': self.year,
                'bhxh_status': row['bhxh_status'],
                'bhxh_amount': row['bhxh_amount'],
                'bhyt_amount': row['bhyt_amount'],
                'bhtn_amount': row['bhtn_amount'],
            })

        if errors:
            raise UserError('\n'.join(errors))
        return created
