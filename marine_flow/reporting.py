"""Report drafts from verified records, always subject to human approval."""
import os
from .workflow import sample_rows,verified_results,validate

def draft_report(db=None,reference_hits=None):
    samples=sample_rows(db)
    verified=verified_results(db)
    issues=validate(db)
    lines=["# 해양환경 조사 결과 요약 (검토용 초안)","",
           "> 가상 데이터 기반 자동 생성물입니다. 실제 제출 전 담당 연구원의 검토 및 승인 필수.","",
           "## 1. 시료 및 검증 현황",
           f"- 등록 시료: {len(samples)}개",
           f"- 검증 통과 분석결과: {len(verified)}건",
           f"- 확인 필요/참고 항목: {len(issues)}건","",
           "## 2. 검증 완료 결과",
           "| 시료 ID | 분석 항목 | 값 | 단위 | 출처 |",
           "|---|---|---:|---|---|"]
    if verified:
        for r in verified:
            lines.append(f"| {r['sample_id']} | {r['analyte']} | {r['result']:g} | {r['unit']} | {r['source_file']} |")
    else:
        lines.append("| - | - | - | - | 검증 완료 결과 없음 |")
    lines+=["","## 3. 확인이 필요한 사항"]
    lines.extend([f"- **{r['sample_id']}**: {r['issue']}" for r in issues] or ["- 자동 규칙상 불일치 없음 (추가 전문 검토 필요)"])
    lines+=["","## 4. 참고 자료"]
    lines.extend([f"- {h.source} (유사도 {h.score:.2f}): {h.text[:100]}" for h in (reference_hits or [])] or ["- 검색된 자료 없음"])
    lines+=["","## 5. 검토 및 승인",
            "- [ ] 시료 ID·분석값 대조",
            "- [ ] 단위·시험방법·누락 항목 검토",
            "- [ ] 근거 문서·환경 해석 검토",
            "- [ ] 최종 책임자 승인 후 외부 제출"]
    return "\n".join(lines)

def optional_llm_polish(draft):
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다.")
    from openai import OpenAI
    client=OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response=client.responses.create(
        model=os.getenv("OPENAI_MODEL","gpt-4o-mini"),
        instructions="당신은 해양 조사 보고서 문장 교정자입니다. 수치, 식별자, 출처, 확인 필요 항목을 수정하거나 새로운 데이터를 만들지 마세요. 연구원 최종 검토 문구를 유지하세요.",
        input=draft)
    return response.output_text
