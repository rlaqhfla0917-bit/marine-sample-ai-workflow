"""Fictional data for the demo."""
from .workflow import register_sample,record_handoff,import_lab_csv,sample_rows
EXAMPLE_CSV="""sample_id,analyte,result,unit,analyzed_at
A-01-2026Q2,T-N,0.31,mg/L,2026-06-18
A-01-2026Q2,T-P,0.018,mg/L,2026-06-18
A-03-2026Q2,T-P,0.021,mg/L,2026-06-18
UNKNOWN-2026Q2,T-N,0.28,mg/L,2026-06-18
"""
def seed(db=None):
    if sample_rows(db):
        return False
    for sid,station,t in (("A-01-2026Q2","A-01","09:00"),("A-03-2026Q2","A-03","10:30")):
        register_sample(sid,"가상 해양수질 2분기 조사",station,f"2026-06-12 {t}","해수",["T-N","T-P"],db=db)
        record_handoff(sid,"현장조사원","가상 시험분석기관","2026-06-12 14:00",db=db)
    import_lab_csv(EXAMPLE_CSV,"demo_lab_results.csv",db=db)
    return True
