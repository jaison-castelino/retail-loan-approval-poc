import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["LOAN_DB"] = os.path.join(tempfile.mkdtemp(), "t.db")
import data

def test_generator_deterministic_and_sized():
    a, b = data.generate_applicants(50), data.generate_applicants(50)
    assert a == b and len(a) == 50 and len({x["id"] for x in a}) == 50

def test_persistence_roundtrip():
    d = dict(decision="Approved", reason="r", officer="o", time="t")
    data.save_decision("X1", d); data.save_audit("t", "X1", "e"); data.save_stage("X1", "accepted")
    dec, aud, acc, dis = data.load_state()
    assert dec["X1"] == d and aud[-1]["Event"] == "e" and "X1" in acc and not dis
