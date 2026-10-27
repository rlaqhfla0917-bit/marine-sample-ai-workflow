import pytest
from marine_flow.db import initialize
from marine_flow.workflow import register_sample,record_handoff,import_lab_csv,validate,verified_results
from marine_flow.sample_data import seed
from marine_flow.reporting import draft_report
from marine_flow.retrieval import retrieve

def test_demo_missing_and_unknown(tmp_path):
    db=tmp_path/"demo.db"
    initialize(db)
    assert seed(db)
    assert not seed(db)
    issues=validate(db)
    assert any(x["sample_id"]=="A-03-2026Q2" and "T-N" in x["issue"] for x in issues)
    assert any(x["sample_id"]=="UNKNOWN-2026Q2" for x in issues)
    verified=verified_results(db)
    assert len(verified)==2
    assert {r["sample_id"] for r in verified}=={"A-01-2026Q2"}
    report=draft_report(db)
    assert "A-03-2026Q2" in report
    assert "최종 책임자 승인" in report

def test_atomic_csv_and_duplicates(tmp_path):
    db=tmp_path/"test.db"
    initialize(db)
    register_sample("S1","P","A-01","2026-06-10","해수",["T-N"],db=db)
    record_handoff("S1","a","b","2026-06-10",db=db)
    csv="sample_id,analyte,result,unit,analyzed_at\nS1,T-N,0.3,mg/L,2026-06-11\n"
    assert import_lab_csv(csv,"file.csv",db)["imported"]==1
    assert import_lab_csv(csv,"file.csv",db)["skipped"]==1
    assert not validate(db)
    result=import_lab_csv(csv+"S1,T-P,N/A,mg/L,2026-06-11\n","bad.csv",db)
    assert result["errors"] and result["imported"]==0

def test_korean_retrieval(tmp_path):
    (tmp_path/"guide.txt").write_text("해양 시료 인수인계 확인 기록을 보관합니다.",encoding="utf-8")
    hits=retrieve("인수인계 확인",tmp_path)
    assert hits and hits[0].source=="guide.txt"

def test_missing_handoff(tmp_path):
    db=tmp_path/"s.db"
    initialize(db)
    register_sample("S2","P","B-01","2026-06-10","해수",["T-N"],db=db)
    assert any("인수인계" in row["issue"] for row in validate(db))

def test_unrequested_analyte_is_not_reported_as_verified(tmp_path):
    db=tmp_path/"extra.db"
    initialize(db)
    register_sample("S3","P","C-01","2026-06-10","해수",["T-N"],db=db)
    record_handoff("S3","a","b","2026-06-10",db=db)
    csv="sample_id,analyte,result,unit,analyzed_at\nS3,T-N,0.3,mg/L,2026-06-11\nS3,T-P,0.02,mg/L,2026-06-11\n"
    assert import_lab_csv(csv,"extra.csv",db)["imported"]==2
    assert any("등록되지 않은 분석 항목: T-P" in row["issue"] for row in validate(db))
    assert [row["analyte"] for row in verified_results(db)]==["T-N"]
    report=draft_report(db)
    assert "| S3 | T-N |" in report
    assert "| S3 | T-P |" not in report
    assert "등록되지 않은 분석 항목: T-P" in report
