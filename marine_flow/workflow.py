"""Deterministic sample and laboratory data validation (no LLM inference)."""
import csv
import math
from io import StringIO
from .db import connect

REQUIRED_LAB_COLS = ("sample_id","analyte","result","unit","analyzed_at")
ALLOWED_ANALYTES = {"T-N","T-P","pH","COD","DO","SS"}

def register_sample(sample_id, project, station, collected_at, material, expected_analytes, note="", db=None):
    if any(not str(x).strip() for x in (sample_id,project,station,collected_at,material)):
        raise ValueError("시료 ID, 프로젝트, 정점, 채취일시, 시료 유형은 필수입니다.")
    analytes = sorted(set(expected_analytes))
    if not analytes or not set(analytes).issubset(ALLOWED_ANALYTES):
        raise ValueError("유효한 분석 항목을 선택하세요.")
    with connect(db) as con:
        con.execute("""INSERT INTO samples
          (sample_id,project,station,collected_at,material,expected_analytes,note)
          VALUES (?,?,?,?,?,?,?)""",
          (sample_id.strip(),project.strip(),station.strip(),collected_at,material.strip(),",".join(analytes),note.strip()))

def record_handoff(sample_id,sender,receiver,handed_at,note="",db=None):
    if any(not str(x).strip() for x in (sample_id,sender,receiver,handed_at)):
        raise ValueError("시료, 인계자, 인수자, 인계시각은 필수입니다.")
    with connect(db) as con:
        con.execute("INSERT INTO handoffs(sample_id,handed_at,sender,receiver,note) VALUES(?,?,?,?,?)",
                    (sample_id,handed_at,sender,receiver,note))

def import_lab_csv(csv_text,filename,db=None):
    reader = csv.DictReader(StringIO(csv_text.lstrip("\ufeff")))
    if not reader.fieldnames or not set(REQUIRED_LAB_COLS).issubset(reader.fieldnames):
        raise ValueError("필수 컬럼: "+", ".join(REQUIRED_LAB_COLS))
    rows,errors=[],[]
    for line,row in enumerate(reader,start=2):
        try:
            sid,analyte,unit,at=[row[key].strip() for key in ("sample_id","analyte","unit","analyzed_at")]
            value=float(row["result"])
            if not all((sid,analyte,unit,at)) or analyte not in ALLOWED_ANALYTES or not math.isfinite(value):
                raise ValueError("식별자, 분석항목 또는 결과값 오류")
            rows.append((sid,analyte,value,unit,at,filename))
        except (ValueError,AttributeError,TypeError,KeyError) as exc:
            errors.append(f"{line}행: {exc}")
    if errors:
        return {"imported":0,"skipped":0,"errors":errors}
    imported=0
    with connect(db) as con:
        for row in rows:
            cur=con.execute("""INSERT OR IGNORE INTO results
                (sample_id,analyte,result,unit,analyzed_at,source_file) VALUES(?,?,?,?,?,?)""",row)
            imported+=cur.rowcount
    return {"imported":imported,"skipped":len(rows)-imported,"errors":[]}

def sample_rows(db=None):
    with connect(db) as con:
        return [dict(x) for x in con.execute("SELECT * FROM samples ORDER BY sample_id")]

def handoff_rows(db=None):
    with connect(db) as con:
        return [dict(x) for x in con.execute("SELECT * FROM handoffs ORDER BY id DESC")]

def result_rows(db=None):
    with connect(db) as con:
        return [dict(x) for x in con.execute("SELECT * FROM results ORDER BY sample_id,analyte")]

def validate(db=None):
    samples=sample_rows(db)
    handoffs=handoff_rows(db)
    results=result_rows(db)
    handed={h["sample_id"] for h in handoffs}
    by_sample={}
    for row in results:
        by_sample.setdefault(row["sample_id"],[]).append(row)
    issues=[]
    for s in samples:
        sid=s["sample_id"]
        rows=by_sample.get(sid,[])
        found={r["analyte"] for r in rows}
        required=set(s["expected_analytes"].split(","))
        if sid not in handed:
            issues.append({"sample_id":sid,"level":"확인 필요","issue":"인수인계 기록 없음"})
        for analyte in sorted(required-found):
            issues.append({"sample_id":sid,"level":"확인 필요","issue":f"{analyte} 분석결과 누락"})
        for analyte in sorted(found-required):
            issues.append({"sample_id":sid,"level":"참고","issue":f"등록되지 않은 분석 항목: {analyte}"})
        for analyte in found:
            values=[r for r in rows if r["analyte"]==analyte]
            if len(values)>1:
                issues.append({"sample_id":sid,"level":"확인 필요","issue":f"{analyte} 중복 분석값 {len(values)}건"})
            if len({v["unit"] for v in values})>1:
                issues.append({"sample_id":sid,"level":"확인 필요","issue":f"{analyte} 단위 불일치"})
    known={s["sample_id"] for s in samples}
    for sid in sorted(set(by_sample)-known):
        issues.append({"sample_id":sid,"level":"확인 필요","issue":"등록되지 않은 시료 ID의 분석결과"})
    return issues

def verified_results(db=None):
    invalid={v["sample_id"] for v in validate(db) if v["level"]=="확인 필요"}
    expected={s["sample_id"]:set(s["expected_analytes"].split(",")) for s in sample_rows(db)}
    return [v for v in result_rows(db)
            if v["sample_id"] not in invalid
            and v["analyte"] in expected.get(v["sample_id"], set())]
