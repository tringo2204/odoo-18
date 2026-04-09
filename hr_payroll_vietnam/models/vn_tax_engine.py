"""Vietnamese tax calculation engine — pure Python, no ORM dependency.

All functions are stateless and unit-testable.
Monetary amounts are in VND (integer-safe floats).
"""


def calculate_pit_progressive(taxable_income, brackets):
    """Calculate Personal Income Tax using 7-bracket progressive table.

    Args:
        taxable_income: Thu nhập chịu thuế (after all deductions).
        brackets: list of (income_from, income_to, rate_percent).
                  income_to=0 means unlimited (last bracket).

    Returns:
        Total PIT amount.
    """
    if taxable_income <= 0:
        return 0.0

    total_tax = 0.0
    for income_from, income_to, rate in brackets:
        if taxable_income <= income_from:
            break
        upper = taxable_income if (income_to == 0 or taxable_income < income_to) else income_to
        taxable_in_bracket = upper - income_from
        total_tax += taxable_in_bracket * rate / 100.0

    return round(total_tax)


def calculate_pit_non_resident(taxable_income):
    """Flat 20% PIT for non-tax-residents."""
    if taxable_income <= 0:
        return 0.0
    return round(taxable_income * 0.20)


def calculate_insurance(salary, bhxh_cap, bhtn_cap, employee_rates):
    """Calculate BHXH + BHYT + BHTN employee contribution with caps.

    Args:
        salary: Mức lương đóng BHXH (insurance_salary on contract).
        bhxh_cap: Mức trần BHXH (20 x lương cơ sở).
        bhtn_cap: Mức trần BHTN (20 x lương vùng).
        employee_rates: dict {bhxh: 8.0, bhyt: 1.5, bhtn: 1.0} (percent).

    Returns:
        dict {bhxh, bhyt, bhtn, total}.
    """
    bhxh_base = min(salary, bhxh_cap)
    bhtn_base = min(salary, bhtn_cap)

    bhxh = round(bhxh_base * employee_rates.get('bhxh', 8.0) / 100.0)
    bhyt = round(bhxh_base * employee_rates.get('bhyt', 1.5) / 100.0)
    bhtn = round(bhtn_base * employee_rates.get('bhtn', 1.0) / 100.0)

    return {
        'bhxh': bhxh,
        'bhyt': bhyt,
        'bhtn': bhtn,
        'total': bhxh + bhyt + bhtn,
    }


def calculate_gross_up(net_desired, insurance_employee, self_deduction,
                       dependent_count, dependent_deduction, brackets):
    """Reverse-calculate GROSS from desired NET when employer bears tax.

    The employer pays the PIT on behalf of the employee.
    We solve: NET = GROSS - INSURANCE_employee - PIT(GROSS - INSURANCE - deductions)

    Args:
        net_desired: Lương NET mong muốn.
        insurance_employee: Tổng BHXH+BHYT+BHTN phần NV.
        self_deduction: Giảm trừ bản thân (11,000,000).
        dependent_count: Số NPT đã duyệt.
        dependent_deduction: Giảm trừ mỗi NPT (4,400,000).
        brackets: list of (income_from, income_to, rate_percent).

    Returns:
        dict {gross, pit, net, taxable_income}.
    """
    total_deduction = self_deduction + dependent_count * dependent_deduction

    # Taxable income before PIT = GROSS - insurance - deductions
    # NET = GROSS - insurance - PIT
    # So: GROSS = NET + insurance + PIT
    # And: taxable = GROSS - insurance - deductions = NET + PIT - deductions
    # We need to find PIT such that PIT = f(NET + PIT - deductions)

    # Iterative approach: solve bracket by bracket
    net_plus_insurance = net_desired + insurance_employee
    taxable_from_net = net_desired - total_deduction  # approximate taxable

    if taxable_from_net <= 0:
        # No tax needed
        return {
            'gross': net_plus_insurance,
            'pit': 0.0,
            'net': net_desired,
            'taxable_income': 0.0,
        }

    # Solve: find gross such that gross - insurance - pit(gross - insurance - deductions) = net
    # Use Newton-like iteration
    gross = net_plus_insurance  # initial guess (no tax)
    for _i in range(50):
        taxable = gross - insurance_employee - total_deduction
        pit = calculate_pit_progressive(max(taxable, 0), brackets)
        new_gross = net_desired + insurance_employee + pit
        if abs(new_gross - gross) < 1.0:
            gross = new_gross
            break
        gross = new_gross

    taxable_income = gross - insurance_employee - total_deduction
    pit = calculate_pit_progressive(max(taxable_income, 0), brackets)

    return {
        'gross': round(gross),
        'pit': round(pit),
        'net': round(gross - insurance_employee - pit),
        'taxable_income': round(max(taxable_income, 0)),
    }
