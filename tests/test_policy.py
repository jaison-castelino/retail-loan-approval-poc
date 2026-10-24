import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import policy
EXPECT = {"age": "PL-1.1", "employment": "PL-1.2", "score": "PL-2.1", "foir": "PL-2.2", "loan": "PL-2.3", "docs": "PL-3.1", "name": "PL-3.2"}

def test_retrieval_finds_right_clause():
    for k, cid in EXPECT.items():
        assert policy.retrieve(policy.QUERIES[k])["id"] == cid, k

def base(**kw):
    a = dict(age=35, years=5, score=760, amount=300000, income=80000, docs=["PAN", "Salary slip", "Bank statement"], name="A B", pan_name="A B")
    a.update(kw); return a

def results(a, foir=20, missing=(), match=True):
    return {f["check"]: f["result"] for f in policy.evaluate(a, foir, list(missing), match)}

def test_clean_passes():
    assert set(results(base()).values()) == {"Pass"}

def test_edges():
    assert results(base(score=679))["Bureau score"] == "Fail"
    assert results(base(score=700))["Bureau score"] == "Refer"
    assert results(base(), foir=45)["FOIR"] == "Refer" and results(base(), foir=55)["FOIR"] == "Fail"
    assert results(base(), missing=["PAN"])["Documents"] == "Refer"
