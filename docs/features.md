# 기능 문서

## 위험 분석

`POST /llm/analyze`는 Django가 전달한 강수 상황과 위험 데이터를 정형화한 뒤
OpenAI Chat 모델로 현장 보고 문구를 생성한다. 생성된 문구는 요청 body에 포함된
Telegram bot token/chat id로 발송된다. 직접 호출에서 chat ID 필드가 생략된
경우에만 서버 `.env`의 Telegram 값을 fallback으로 사용할 수 있다.

주요 흐름:

1. `id` 값으로 기상 시나리오를 선택한다.
2. `swmm_raw_data`를 `swmm_formatter.py`에서 정형화한다.
3. 같은 시설 ID의 과거 조치 이력을 ChromaDB에서 조회한다.
4. `priorityTargets`를 포함한 LLM 입력을 만든다.
5. OpenAI Chat 모델로 답변을 생성한다.
6. Telegram으로 메시지를 발송한다.

## 분석 Preview

`POST /llm/analyze/preview`는 LLM 호출과 Telegram 발송 없이 정형화된 입력 payload만
확인한다. 통합 테스트 중 입력 변환 결과를 확인할 때 사용한다.

## 유지보수 이력 저장

`POST /llm/maintenance/log`는 Django 위험 조치 payload를 받아 ChromaDB에 저장한다.
저장 전 `maintenance_store.py`가 payload를 사람이 읽기 쉬운 대응 사례 텍스트로
포맷하고, OpenAI embedding 모델로 임베딩한다.

저장되는 주요 내용:

- 위험 사건 정보
- 대상 시설 ID
- 주요 metric
- 현장 조치 우선순위
- 조치 내용
- 결과 내용
- 재발 시 참고사항

## 과거 조치 이력 반영

분석 시 `link[].id`와 `swmmIssues[].primaryElement.id`를 기준으로 ChromaDB에서
같은 `sourceId`의 기록을 조회한다. 이력이 없으면 `past_history`는 빈 배열이다.
프롬프트는 빈 이력 상태에서 "재발"이나 "과거 여러 차례 조치"를 말하지 않도록
제한한다.

## LLM debug log

`llm_debug_logger.py`는 LLM 호출 직전 입력과 호출 결과를 파일로 저장한다.

- 기본 경로: `llm-debug/`
- 입력: `llm-debug/inputs/*.json`
- 답변: `llm-debug/answers/*.txt`
- 비활성화: `LLM_DEBUG_LOG_ENABLED=false`

이 기능은 테스트용이며, `analyzer.py`의 import와 호출부를 제거하면 쉽게 분리할 수
있다.
