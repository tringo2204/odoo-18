# SHT HRM Custom Addons

Custom Odoo 18 modules for SHT HRM system.

## Modules

| Module | Description | Status |
|--------|-------------|--------|
| `sht_hr_base` | Employee base: Vietnam fields, documents | ✅ Done |
| `sht_hr_reward_discipline` | Rewards & disciplinary actions | ✅ Done |
| `sht_hr_training` | Training courses & records | ✅ Done |
| `sht_hr_contract` | Vietnam contracts, probation | 🔲 Wave 2 |
| `sht_hr_recruitment` | Headcount planning, recruitment | 🔲 Wave 2 |
| `sht_hr_onboarding` | Onboarding/offboarding checklists | 🔲 Wave 2 |
| `sht_hr_leave` | Vietnam leave types | 🔲 Wave 2 |
| `sht_hr_attendance` | Attendance + payroll integration | 🔲 Wave 3 |
| `sht_hr_health_check` | Health check records | 🔲 Wave 3 |
| `sht_hr_payroll` | Salary rules, OT, allowances | 🔲 Wave 3 |
| `sht_hr_kpi` | KPI management | 🔲 Wave 4 |
| `sht_hr_ivan` | IVAN reports | 🔲 Wave 4 |
| `sht_hr_dashboard` | Dashboards & alerts | 🔲 Wave 4 |

## Theme

`theme_omux/` — Custom Omux theme sub-modules.

## Development Workflow

1. Develop and test locally on `http://127.0.0.1:8069`
2. Commit and push to this repo
3. SSH to server and pull latest code
4. Restart Odoo service

## Deployment (Remote Server)

```bash
ssh -i .ssh/github-personal root@165.245.182.237
cd /opt/odoo18/custom_addons
git pull origin main
sudo systemctl restart odoo18
```
