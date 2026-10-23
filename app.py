"""Streamlit demo: marine sampling to reviewed report (synthetic data only)."""
import io
import os
import sqlite3
from datetime import date,datetime
from pathlib import Path
import pandas as pd
import streamlit as st
from marine_flow.db import initialize
from marine_flow.workflow import (ALLOWED_ANALYTES, register_sample,record_handoff,import_lab_csv,
                                  sample_rows,handoff_rows,result_rows,validate,verified_results)
from marine_flow.sample_data import seed
from marine_flow.reporting import draft_report,optional_llm_polish
from marine_flow.retrieval import retrieve

ROOT=Path(__file__).parent
st.set_page_config(page_title="MarineFlow | 시료에서 보고서까지",page_icon="🌊",layout="wide")
initialize()
st.title("🌊 MarineFlow")
st.caption("현장 시료 등록 → 인수인계 → 시험분석 → 데이터 검증 → 보고서 초안")
st.info("합성 데이터 기반 MVP. 실제 고객용·파수 AI 상용 솔루션 연동 제품이 아닙니다.")
with st.sidebar:
    st.header("데모 설정")
    if st.button("합성 데모 데이터 불러오기",type="primary",use_container_width=True):
        if seed():
            st.success("예제 데이터를 불러왔습니다.")
        else:
            st.warning("등록된 시료가 있어 중복 추가하지 않았습니다.")
        st.rerun()
    st.caption("인증·권한 관리 미구현. 실제 개인정보나 고객 자료를 업로드하지 마세요.")

samples=sample_rows()
results=result_rows()
checks=validate()
k1,k2,k3,k4=st.columns(4)
k1.metric("등록 시료",len(samples))
k2.metric("분석 결과",len(results))
k3.metric("확인 필요",sum(c["level"]=="확인 필요" for c in checks))
k4.metric("보고서 반영 결과",len(verified_results()))

t1,t2,t3,t4,t5,t6=st.tabs(["🗂 서비스 안내","🧪 시료 등록","📦 인수인계","📥 분석 결과","✅ 검증 및 검색","📝 보고서"])
with t1:
    st.subheader("업무 및 데이터 흐름")
    st.markdown("**현장 채취 → 시료 등록 → 인수인계 기록 → 분석 CSV 등록 → 누락·중복·단위 검증 → 근거 검색 → 보고서 초안 → 연구원 승인**")
    st.markdown("**현재 구현:** SQLite, CSV, 규칙 검증, 로컬 TF-IDF 검색, 보고서 템플릿 및 선택형 LLM 문장 다듬기.")
    st.markdown("**향후 설계:** PDF OCR, 기업 RAG/SQL Router/Agent, 권한·승인 워크플로, 파수 제품 연동.")
with t2:
    st.subheader("현장 시료 등록")
    with st.form("sample",clear_on_submit=True):
        c1,c2=st.columns(2)
        with c1:
            sid=st.text_input("시료 ID",placeholder="A-05-2026Q2")
            project=st.text_input("프로젝트",value="가상 해양수질 조사")
            station=st.text_input("정점",value="A-05")
        with c2:
            collected_date=st.date_input("채취일",value=date.today())
            collected_time=st.time_input("채취시각",value=datetime.now().time().replace(second=0,microsecond=0))
            material=st.selectbox("시료 유형",["해수","저질","기타"])
        analytes=st.multiselect("필수 분석 항목",sorted(ALLOWED_ANALYTES),default=["T-N","T-P"])
        note=st.text_area("비고")
        if st.form_submit_button("시료 등록"):
            try:
                register_sample(sid,project,station,f"{collected_date} {collected_time:%H:%M}",material,analytes,note)
                st.success("시료가 등록되었습니다.")
                st.rerun()
            except (sqlite3.Error,ValueError) as exc:
                st.error(str(exc))
    st.dataframe(pd.DataFrame(sample_rows()),use_container_width=True,hide_index=True)
with t3:
    st.subheader("외부 분석업체 인수인계")
    ids=[s["sample_id"] for s in sample_rows()]
    if not ids:
        st.warning("시료를 먼저 등록하세요.")
    else:
        with st.form("handoff"):
            sid=st.selectbox("시료 ID",ids)
            sender=st.text_input("인계자")
            receiver=st.text_input("인수자")
            day=st.date_input("인계일",value=date.today())
            note=st.text_input("비고")
            if st.form_submit_button("기록"):
                try:
                    record_handoff(sid,sender,receiver,f"{day} 09:00",note)
                    st.success("인계 기록을 저장했습니다. 전자서명은 미구현입니다.")
                    st.rerun()
                except (sqlite3.Error,ValueError) as exc:
                    st.error(str(exc))
    st.dataframe(pd.DataFrame(handoff_rows()),use_container_width=True,hide_index=True)
with t4:
    st.subheader("시험분석 결과 CSV 등록")
    st.caption("CSV 열: sample_id, analyte, result, unit, analyzed_at")
    sample_csv=(ROOT/"examples"/"lab_results.csv").read_bytes()
    st.download_button("예제 CSV 다운로드",sample_csv,"lab_results.csv","text/csv")
    uploaded=st.file_uploader("CSV 선택",type=["csv"])
    if uploaded is not None:
        try:
            csv_text=uploaded.getvalue().decode("utf-8-sig")
            st.dataframe(pd.read_csv(io.StringIO(csv_text)),use_container_width=True,hide_index=True)
            if st.button("검증 후 저장"):
                out=import_lab_csv(csv_text,uploaded.name)
                if out["errors"]:
                    st.error("; ".join(out["errors"][:10]))
                else:
                    st.success(f"저장 {out['imported']}건, 중복 제외 {out['skipped']}건")
                    st.rerun()
        except (UnicodeError,ValueError) as exc:
            st.error(f"UTF-8 CSV를 확인하세요: {exc}")
    st.dataframe(pd.DataFrame(result_rows()),use_container_width=True,hide_index=True)
with t5:
    st.subheader("규칙 기반 자동 검증")
    st.caption("LLM이 아닌 정확한 ID·항목·단위 기준으로 검증합니다.")
    checks=validate()
    if checks:
        st.warning(f"{len(checks)}건 확인 필요/참고")
        st.dataframe(pd.DataFrame(checks),use_container_width=True,hide_index=True)
    else:
        st.success("자동 검증상 불일치 없음. 연구원 최종 검토는 별도로 필요합니다.")
    st.subheader("참고자료 검색 (TF-IDF, RAG 아님)")
    query=st.text_input("검색어",value="시료 인수인계 검증")
    if st.button("검색"):
        hits=retrieve(query,ROOT/"examples")
        if hits:
            for hit in hits:
                st.markdown(f"**{hit.source}** (유사도 {hit.score:.2f})")
                st.text(hit.text[:600])
        else:
            st.info("관련 근거자료가 없습니다.")
with t6:
    st.subheader("검증 데이터 기반 보고서 초안")
    hits=retrieve("해양수질 시료 분석 검증 보고서",ROOT/"examples")
    report=draft_report(reference_hits=hits)
    st.markdown(report)
    st.download_button("보고서 Markdown 다운로드",report.encode("utf-8"),"marine_report_draft.md","text/markdown")
    if os.getenv("OPENAI_API_KEY"):
        if st.button("선택: AI 문장 다듬기"):
            try:
                edited=optional_llm_polish(report)
                st.warning("AI 생성문은 원본 결과와 반드시 대조해야 합니다.")
                st.markdown(edited)
            except Exception as exc:
                st.error(str(exc))
    else:
        st.caption("OPENAI_API_KEY가 없는 경우 AI 문장 다듬기는 비활성화됩니다.")
