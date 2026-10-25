"""Mock external services. Local, deterministic, synthetic. Every response is labelled MOCK. No real system is called."""
import hashlib

SCENARIOS = {"PL-1007": {"fraud": "flagged"}, "PL-1008": {"bureau": "unavailable"}}  # reliable demo cases


def _h(k, m): return int(hashlib.md5(k.encode()).hexdigest(), 16) % m


def _gen(a): return a["id"] >= "PL-2001"  # random failures only for generated applicants


def _forced(a, svc): return SCENARIOS.get(a["id"], {}).get(svc)


def _r(a, service, status, note, data=None):
    return dict(service=service, status=status, note=note, data=data or {}, latency_ms=60 + _h(a["id"] + service, 400),
                label="MOCK RESPONSE: synthetic data, simulated latency")


def bureau(a):
    if _forced(a, "bureau") == "unavailable" or (_gen(a) and _h(a["id"] + "b", 25) == 0):
        return _r(a, "Credit bureau", "unavailable", "Service timeout (simulated)")
    return _r(a, "Credit bureau", "ok", "Report returned",
              dict(score=a["score"], enquiries_6m=_h(a["id"] + "e", 6), active_loans=int(a["emi"] > 0)))


def pan_verify(a):
    if a["pan_name"].lower() != a["name"].lower():
        return _r(a, "PAN verification", "inconsistent", f"Name on PAN record is '{a['pan_name']}'")
    return _r(a, "PAN verification", "verified", "Name matches PAN record")


def bank_verify(a):
    if _gen(a) and _h(a["id"] + "k", 20) == 0:
        return _r(a, "Bank account verification", "inconsistent", "Account holder name differs (simulated)")
    return _r(a, "Bank account verification", "verified", "Account holder matches")


def fraud_screen(a):
    if _forced(a, "fraud") == "flagged" or (_gen(a) and _h(a["id"] + "f", 30) == 0):
        return _r(a, "Fraud screening", "flagged", "Multiple applications in 7 days across lenders (simulated)")
    return _r(a, "Fraud screening", "clear", "No adverse patterns")
