# SHT HRM Custom Addons

Custom Odoo 18 modules for SHT HRM system.

## Modules

### Core HR Modules

| Module | Description | Status | Enterprise Required |
|--------|-------------|--------|:---:|
| `sht_hr_base` | Employee base: Vietnam fields, documents | Done | No |
| `sht_hr_reward_discipline` | Rewards & disciplinary actions | Done | No |
| `sht_hr_training` | Training courses & records | Done | No |
| `sht_hr_contract` | Vietnam contracts, probation, renewal alerts | Done | No |
| `sht_hr_recruitment` | Headcount planning, recruitment | Done | No |
| `sht_hr_onboarding` | Onboarding/offboarding checklists | Done | No |
| `sht_hr_leave` | Vietnam leave types, seniority bonus | Done | No |

### Vietnam HR Modules

| Module | Description | Status | Enterprise Required |
|--------|-------------|--------|:---:|
| `hr_payroll_vietnam` | BHXH, PIT (7-bracket), gross-up, salary simulation | Done | Yes (`hr_payroll`, `hr_work_entry_contract_enterprise`) |
| `hr_social_insurance_vn` | Social insurance records, D02-LT reports, C12 lookup | Done | Yes (via `hr_payroll_vietnam`) |
| `hr_request_vn` | Requests & approvals: leave, OT, check-in, shift swap, business trip, resignation | Done | No |
| `hr_decision_vn` | HR decisions: appointment, transfer, salary adjustment, termination | Done | No |
| `hr_asset_vn` | Employee asset management: allocation, return, depreciation | Done | No |

### Manufacturing

| Module | Description | Status | Enterprise Required |
|--------|-------------|--------|:---:|
| `mfg_dashboard` | Real-time KPI dashboard for manufacturing | Done | Yes (`quality_control`, `mrp_plm`) |

## Theme

`theme_omux/` — Omux backend theme for Community Edition (excludes `web_enterprise`). Contains sub-modules:
`udoo_om_ux`, `omux_shared_lib`, `omux_config_base`, `omux_state_manager`, `omux_web_refresher`,
`omux_view_action`, `omux_list_indicator`, `omux_list_density`, `omux_border_radius`, `omux_input_style`.

## Development Workflow

1. Develop and test locally on `http://127.0.0.1:8069`
2. Commit and push to this repo
3. CI runs lint checks on pull requests
4. Merge to `main` triggers auto-deploy via GitHub Actions

## Deployment (Automated)

Pushing to `main` triggers the **Deploy to Odoo Server** workflow which:
1. Selectively checks out custom module folders on the server
2. Restarts the Odoo service
3. Optionally upgrades specified modules (via `workflow_dispatch`)

### Manual Deployment

```bash
ssh -i .ssh/github-personal root@<server-host>
cd /opt/odoo18
git fetch https://github.com/tringo2204/odoo-18.git main
git checkout FETCH_HEAD -- sht_hr_base sht_hr_training ...
sudo systemctl restart odoo18
```
# Mon May  4 15:50:10 +07 2026
