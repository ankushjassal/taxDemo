def calculate_old_regime(data):
    # Extract values and convert to float (default 0)
    gross_salary = float(data.get('gross_salary', 0) or 0)
    basic_salary = float(data.get('basic_salary', 0) or 0)
    hra_received = float(data.get('hra_received', 0) or 0)
    rent_paid = float(data.get('rent_paid', 0) or 0)
    deduction_80c = float(data.get('deduction_80c', 0) or 0)
    deduction_80d = float(data.get('deduction_80d', 0) or 0)
    standard_deduction = float(data.get('standard_deduction', 50000) or 50000)
    professional_tax = float(data.get('professional_tax', 0) or 0)
    tds = float(data.get('tds', 0) or 0)

    # HRA exemption (simplified):
    hra_exemption = min(
        hra_received,
        0.5 * gross_salary,  # Assume metro city for simplicity
        rent_paid - 0.1 * basic_salary if rent_paid > 0 else 0
    )
    hra_exemption = max(hra_exemption, 0)

    # Deductions
    total_deductions = (
        standard_deduction + hra_exemption + professional_tax + deduction_80c + deduction_80d
    )
    taxable_income = max(gross_salary - total_deductions, 0)

    # Old regime slabs
    tax = 0
    slabs = [
        (250000, 0.0),
        (500000, 0.05),
        (1000000, 0.2),
        (float('inf'), 0.3)
    ]
    prev_limit = 0
    for limit, rate in slabs:
        if taxable_income > limit:
            tax += (limit - prev_limit) * rate
            prev_limit = limit
        else:
            tax += (taxable_income - prev_limit) * rate
            break
    tax = max(tax, 0)
    tax += 0.04 * tax  # 4% cess
    return round(tax, 2)

def calculate_new_regime(data):
    gross_salary = float(data.get('gross_salary', 0) or 0)
    standard_deduction = float(data.get('standard_deduction', 50000) or 50000)
    taxable_income = max(gross_salary - standard_deduction, 0)
    # New regime slabs
    tax = 0
    slabs = [
        (300000, 0.0),
        (600000, 0.05),
        (900000, 0.1),
        (1200000, 0.15),
        (1500000, 0.2),
        (float('inf'), 0.3)
    ]
    prev_limit = 0
    for limit, rate in slabs:
        if taxable_income > limit:
            tax += (limit - prev_limit) * rate
            prev_limit = limit
        else:
            tax += (taxable_income - prev_limit) * rate
            break
    tax = max(tax, 0)
    tax += 0.04 * tax  # 4% cess
    return round(tax, 2)

def calculate_tax_comparison(data):
    tax_old = calculate_old_regime(data)
    tax_new = calculate_new_regime(data)
    best_regime = 'old' if tax_old < tax_new else 'new'
    return {
        'tax_old_regime': tax_old,
        'tax_new_regime': tax_new,
        'best_regime': best_regime
    } 