# Deploy notes — manual server patches

Patches áp dụng thủ công trên `/opt/odoo18/...` không thể đưa vào git custom_addons.
Khi rebuild server hoặc re-fetch enterprise-18.0, cần apply lại các patch dưới đây.

---

## 1. `enterprise-18.0/web_gantt/__manifest__.py` — line 32

**Vấn đề:** Bundle `web.dark_mode_variables` declare:
```python
('before', 'web_enterprise/static/src/**/*.variables.scss', 'web_gantt/static/src/**/*.variables.dark.scss'),
```

`web_enterprise` bị `udoo_om_ux` (Community theme) excludes → uninstalled. Khi load
bất kỳ page nào dùng dark mode → Odoo raise:

```
Unallowed to fetch files from addon web_enterprise. Addon web_enterprise is not installed
```

→ HTTP 500 cho cả page bình thường (Contacts) lẫn Gantt (Planning).

**Fix manual server:** comment out dòng đó.

```bash
ssh root@<server>
sed -i "s|('before', 'web_enterprise/static/src/\*\*/\*.variables.scss', 'web_gantt/static/src/\*\*/\*.variables.dark.scss'),|# Patched: web_enterprise not installed (Community theme) — see hr_request_vn/data/asset_fix.xml|" /opt/odoo18/enterprise-18.0/web_gantt/__manifest__.py
systemctl restart odoo18
```

**Verify:**
```bash
grep -n 'Patched\|web_enterprise/static/src/\*\*' /opt/odoo18/enterprise-18.0/web_gantt/__manifest__.py
# Line 32 phải là # Patched: ... (không phải 'before' ... web_enterprise ...)
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8069/odoo/action-298
# Phải trả 303 (redirect login), không phải 500
```

Tradeoff: mất dark-mode styling cho Gantt charts. Light mode Gantt vẫn hoạt động bình thường.

**Long-term:** install `web_enterprise` (nhưng phải gỡ `udoo_om_ux` trước vì exclude).
