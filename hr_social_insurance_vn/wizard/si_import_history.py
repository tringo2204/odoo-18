import base64
import io

from odoo import api, fields, models, _
from odoo.exceptions import UserError

try:
    import openpyxl
except ImportError:
    openpyxl = None


class SiImportHistory(models.TransientModel):
    _name = 'hr.vn.si.import.history'
    _description = 'Import lịch sử biến động BHXH'

    file = fields.Binary(string='File Excel/CSV', required=True)
    filename = fields.Char(string='Tên file')
    import_type = fields.Selection([
        ('increase', 'Tăng'),
        ('decrease', 'Giảm'),
        ('adjust', 'Điều chỉnh'),
    ], string='Loại biến động', required=True, default='increase')

    def action_import(self):
        self.ensure_one()
        if not self.file:
            raise UserError(_('Vui lòng chọn file để import.'))

        data = base64.b64decode(self.file)
        rows = self._parse_file(data)

        if not rows:
            raise UserError(_('File không có dữ liệu hợp lệ.'))

        created = self._create_history_records(rows)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Import thành công'),
                'message': _('Đã tạo %d biến động.') % len(created),
                'type': 'success',
                'sticky': False,
            },
        }

    def _parse_file(self, data):
        """Parse Excel file.
        Expected columns: Số sổ BHXH | Mức lương cũ | Mức lương mới | Ngày hiệu lực | Lý do
        """
        if not openpyxl:
            raise UserError(
                _('Thư viện openpyxl chưa được cài đặt. '
                  'Chạy: pip install openpyxl')
            )
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True)
        ws = wb.active
        rows = []
        for idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True)):
            if not row or not row[0]:
                continue
            rows.append({
                'bhxh_number': str(row[0]).strip(),
                'old_salary': float(row[1] or 0),
                'new_salary': float(row[2] or 0),
                'effective_date': row[3],
                'reason': str(row[4] or '') if len(row) > 4 else '',
            })
        return rows

    def _create_history_records(self, rows):
        SiRecord = self.env['hr.vn.si.record']
        History = self.env['hr.vn.si.history']
        created = History
        errors = []

        for idx, row in enumerate(rows, start=2):
            record = SiRecord.search([
                ('bhxh_number', '=', row['bhxh_number']),
                ('company_id', '=', self.env.company.id),
            ], limit=1)
            if not record:
                errors.append(
                    _('Dòng %d: Không tìm thấy hồ sơ BH với số sổ %s')
                    % (idx, row['bhxh_number'])
                )
                continue
            effective_date = row['effective_date']
            if isinstance(effective_date, str):
                effective_date = fields.Date.from_string(effective_date)

            created |= History.create({
                'record_id': record.id,
                'change_type': self.import_type,
                'old_salary': row['old_salary'],
                'new_salary': row['new_salary'],
                'effective_date': effective_date,
                'reason': row.get('reason', ''),
            })

        if errors:
            raise UserError('\n'.join(errors))
        return created
