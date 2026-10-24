"""Pure business logic (no Streamlit) so it can be unit-tested."""
def emi_calc(p, n, rate=11.5):
    """Standard amortisation: P*r*(1+r)^n / ((1+r)^n - 1), r = annual rate / 12 / 100."""
    r = rate / 1200
    return p * r * (1 + r) ** n / ((1 + r) ** n - 1)

def foir(income, existing_emi, new_emi):
    """Fixed-obligation-to-income % = (existing EMIs + proposed EMI) / gross monthly income."""
    return (existing_emi + new_emi) / income * 100
