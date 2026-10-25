import os, sys, tempfile, subprocess, csv

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pytest, data, synth, agents, tables

ROOT = os.path.dirname(os.path.dirname(__file__))
EXPECT = {"PL-1001": "Recommend APPROVE", "PL-1002": "REFER - request documents", "PL-1003": "Recommend DECLINE",
          "PL-1004": "REFER - manual review",
          "PL-1005": "REFER - manual review", "PL-1006": "Recommend APPROVE", "PL-1007": "REFER - manual review",
          "PL-1008": "REFER - manual review"}


def test_demo_recommendations_unchanged_and_validated():
    for a in data.DEMO_APPS:
        out = agents.run_agents(a)
        assert out["rec"] == EXPECT[a["id"]], a["id"]
        assert out["validated"] is True


def test_loans_sum_to_declared_emi_and_are_repeatable():
    apps = data.default_applicants(60)
    for a in apps:
        assert sum(l["monthly_emi"] for l in synth.loans_for(a)) == a["emi"]
    assert synth.local_profile(apps[10]) == synth.local_profile(apps[10])


def test_adverse_repayment_flags():
    a3 = next(a for a in data.DEMO_APPS if a["id"] == "PL-1003");
    a4 = next(a for a in data.DEMO_APPS if a["id"] == "PL-1004");
    a1 = data.DEMO_APPS[0]
    assert agents.run_agents(a3)["credit"]["max_dpd"] == 90
    assert agents.run_agents(a4)["credit"]["max_dpd"] == 30
    assert agents.run_agents(a1)["credit"]["late_count"] == 0


def test_validation_rejects_bad_output():
    good = agents.run_agents(data.DEMO_APPS[0])
    bad = dict(good, findings=[dict(good["findings"][0], result="Maybe")])
    with pytest.raises(agents.AgentOutputError): agents.validate_output(bad)
    with pytest.raises(agents.AgentOutputError): agents.validate_output(dict(good, rec="Approve it"))
    with pytest.raises(agents.AgentOutputError): agents.validate_output(dict(good, findings=[]))


def test_tables_complete_and_consistent():
    t = tables.build_tables(data.default_applicants(40))
    assert set(t) == set(tables.NAMES) and len(t["applicants"]) == 40 == len(t["loan_applications"]) == len(
        t["bureau_results"])
    assert t["policy_rules"] and t["agent_logs"] and t["transactions"] and t["repayment_history"]
    assert t["decisions"] == [] and t["audit_events"] == []


def test_generate_data_script_scales(tmp_path):
    r = subprocess.run([sys.executable, os.path.join(ROOT, "generate_data.py"), "--n", "1000", "--out", str(tmp_path)],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr
    assert len(list(csv.DictReader(open(tmp_path / "applicants.csv")))) == 1000
