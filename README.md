# 🌊 MarineFlow — 해양 시료에서 보고서까지

해양환경조사의 **현장 시료 등록 → 인수인계 → 분석결과 검증 → 참고자료 검색 → 보고서 초안 작성**을 잇는 Streamlit 데모입니다.

> **구현 상태:** 실제 해양 현장 경험에서 착안한 새 MVP입니다. 기존 업무 중 만들었던 인수인계 프로그램의 원본이 아니며, 고객사 시스템이나 Fasoo AI 제품과 연동하지 않았습니다. 모든 예제 자료는 가상 데이터입니다.

## 업무 흐름

~~~mermaid
flowchart TD
    A[현장 시료 등록] --> B[외부 분석업체 인수인계]
    B --> C[분석결과 CSV 수령]
    C --> D{시료 ID 및 분석항목 검증}
    D -->|누락/불일치| E[담당자 확인 요청]
    D -->|검증 통과| F[조회 가능한 분석 데이터]
    G[과거 조사 자료 및 지침] --> H[근거 문서 검색]
    F --> I[결과 보고서 초안]
    H --> I
    I --> J[연구원 검토 및 최종 승인]
~~~

## 구현된 기능
- SQLite 시료 등록과 인수인계 이력 관리
- CSV 분석결과 업로드, 중복 방지, 시료·항목 누락과 단위 충돌 검증
- 검증되지 않은 시료 결과는 확정 보고서 표에서 제외
- TF-IDF를 이용한 로컬 참고문서 검색과 출처 표시
- Markdown 보고서 초안 생성, 선택적 OpenAI API 문장 다듬기
- 자동 검증 테스트 (pytest)

## 기술
Python · Streamlit · SQLite · pandas · scikit-learn · pytest · 선택형 OpenAI API

## 로컬 실행

~~~bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
~~~

앱 왼쪽의 **합성 데모 데이터 불러오기**를 클릭하면 A-03-2026Q2의 T-N 결과 누락과 미등록 시료 ID를 확인할 수 있습니다.

테스트: `python -m pytest -q`

OpenAI API 키는 필수가 아닙니다. 사용할 때는 운영체제 환경변수 `OPENAI_API_KEY`로 관리하고 GitHub에 커밋하지 마세요.

## 아직 구현되지 않은 것
PDF/HWP OCR, 기업용 RAG, 자연어 SQL Intent Router, LangGraph AI Agent, 파수 상용 제품 연동, 사용자 인증·권한 제어·감사로그·전자서명·승인 워크플로.

자세한 기술 구분과 확장 계획: [서비스 설계 문서](docs/architecture.md).

**주의:** 인증/보안 기능이 없는 시연용 앱입니다. 실제 고객 데이터나 개인정보를 등록하지 마세요. AI 출력은 담당자의 검증 후 사용해야 합니다.
