# LLM API 명세서

## 문서 정보

- 기준일: 2026-06-29
- 기준 구현: `main.py`, `swmm_formatter.py`, `maintenance_store.py`, `analyzer.py`, `telegram_notifier.py`
- 서비스: SuperMario LLM Server
- Local Base URL: `http://127.0.0.1:8001`
- 기본 LLM Prefix: `/llm`
- Content-Type: `application/json`
- 인증: 현재 이 FastAPI 서버 자체에는 별도 인증 미들웨어가 없다.

이 문서는 Django API 명세서인 `prompt/api-spec.md`와 별개로, 이 저장소의
FastAPI/LangChain 서버가 실제로 제공하는 API만 정리한다.

## 전체 라우팅

| 구분               | Method | Path                   | 설명                                               |
| ------------------ | ------ | ---------------------- | -------------------------------------------------- |
| Health             | `GET`  | `/llm/health`          | LLM 서버 상태 확인                                 |
| 분석 Preview       | `POST` | `/llm/analyze/preview` | LLM/텔레그램 호출 없이 정형화 payload 확인         |
| 위험 분석          | `POST` | `/llm/analyze`         | SWMM 위험 context를 LLM으로 분석하고 텔레그램 발송 |
| 유지보수 이력 저장 | `POST` | `/llm/maintenance/log` | Django 위험 조치 payload를 임베딩해 ChromaDB 저장  |

`/llm` prefix는 `LLM_API_PREFIX` 환경변수로 변경할 수 있다. 따라서
`/llm/maintenance/log`도 prefix 변경 시 `{LLM_API_PREFIX}/maintenance/log`로
변경된다.

유지보수 이력 저장 API는 Django 연동 편의를 위해 `/llm/maintenance/log`와
`/llm/maintenance/log/`를 모두 허용한다.

## 환경변수

| 이름                 | 기본값          | 설명                                                                 |
| -------------------- | --------------- | -------------------------------------------------------------------- |
| `LLM_API_PREFIX`     | `/llm`          | health/analyze/maintenance 계열 API prefix                           |
| `OPENAI_API_KEY`     | 없음            | ChatOpenAI 분석과 OpenAIEmbeddings 생성에 필요                       |
| `CHROMA_PERSIST_DIR` | `./chroma_data` | ChromaDB persist 경로                                                |
| `LLM_DEBUG_LOG_ENABLED` | `true`       | LLM 호출 입력/답변 debug log 저장 여부                               |
| `LLM_DEBUG_LOG_DIR` | `llm-debug`      | LLM debug log 저장 경로                                              |
| `TELEGRAM_BOT_TOKEN` | 없음            | `/llm/analyze` body에 토큰이 없을 때 사용할 Telegram bot token |
| `TELEGRAM_CHAT_ID`   | 없음            | `/llm/analyze` body에서 chat ID 필드가 생략됐을 때 사용할 fallback chat id. 여러 개는 콤마로 구분 |

Docker Compose 실행 시 host `8001` 포트가 container `8000` 포트로 연결된다.

## 공통 오류 형식

FastAPI 기본 오류 형식을 사용한다.

```json
{
  "detail": "오류 메시지"
}
```

Pydantic validation 오류는 FastAPI 기본 `422 Unprocessable Entity` 응답을
반환한다.

## Health API

### LLM 서버 상태 확인

- Method: `GET`
- Path: `/llm/health`
- 성공: `200 OK`

응답:

```json
{
  "status": "ok"
}
```

## 분석 Preview API

### LLM 입력 payload 미리보기

- Method: `POST`
- Path: `/llm/analyze/preview`
- 성공: `200 OK`
- 실패: `400 Bad Request`, `404 Not Found`, `422 Unprocessable Entity`, `500 Internal Server Error`

이 API는 LLM 호출과 텔레그램 발송을 하지 않는다. SWMM raw payload를
LLM 입력 형식으로 정형화하고, ChromaDB에서 같은 sourceId의 과거 유지보수 이력을
조회해 붙인 결과를 반환한다.

요청:

```json
{
  "id": "폭우",
  "swmm_raw_data": {
    "loggedAt": "2026-06-24T12:27:51.219",
    "status": "scheduled",
    "runId": "20260624-122709-3bfc7bc5",
    "stepIndex": 333,
    "modelTime": "2026-06-16T00:05:33",
    "reason": "new_issue",
    "highestSeverity": "CRITICAL",
    "riskEventCount": 1,
    "triggeredIssues": [
      {
        "issueId": "REVERSE_FLOW:link:pipe_free_1781771885636",
        "eventType": "REVERSE_FLOW",
        "severity": "CRITICAL",
        "sourceId": "pipe_free_1781771885636",
        "displayName": "파이프",
        "fromNode": "teeConnector_copy_1781771853047_1",
        "fromNodeName": "T자 커넥터",
        "toNode": "CONN_COMB_01",
        "toNodeName": "합류식 커넥터 01",
        "flowCms": -0.034,
        "direction": "reverse"
      }
    ]
  }
}
```

`swmm_raw_data`는 JSON object 또는 JSON 문자열을 받을 수 있다. object로 받으면
서버가 내부에서 JSON 문자열로 변환한다.

`id`는 현재 다음 값 중 하나여야 한다.

| id       | 설명               |
| -------- | ------------------ |
| `폭우`   | 강한 강수 시나리오 |
| `약한비` | 약한 강수 시나리오 |
| `맑음`   | 무강수 시나리오    |

성공 응답 주요 구조:

```json
{
  "id": "폭우",
  "contextSummary": {
    "hasLinkData": true,
    "hasNodeData": false,
    "hasEditorObjectData": true,
    "linkCount": 1,
    "nodeCount": 0,
    "editorObjectCount": 2,
    "issueCount": 1,
    "priorityTargetCount": 0,
    "priorityTargets": [],
    "pastHistoryCount": 0,
    "past_history": []
  },
  "llmInput": {
    "scenarioId": "폭우",
    "weatherObservation": {},
    "link": [],
    "node": [],
    "editorObject": [],
    "swmmSimulation": {},
    "swmmIssues": [],
    "priorityTargets": [],
    "past_history": []
  }
}
```

실제 `weatherObservation`에는 `scenarios.py`의 기상 관측 값이 들어간다.

## 위험 분석 API

### SWMM 위험 분석 및 텔레그램 발송

- Method: `POST`
- Path: `/llm/analyze`
- 성공: `200 OK`
- 실패: `400 Bad Request`, `404 Not Found`, `422 Unprocessable Entity`, `500 Internal Server Error`, `502 Bad Gateway`

SWMM 위험 context를 정형화하고, 같은 sourceId의 과거 유지보수 이력을 붙인 뒤
LLM 분석 결과를 생성한다. 생성된 분석 결과는 요청 body에 포함된 텔레그램
bot token/chat id를 우선 사용해 발송한다. body에서 bot token이 비어 있거나
chat ID 필드가 생략되면 서버 `.env`의 `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`를
fallback으로 사용한다.

요청:

```json
{
  "id": "폭우",
  "swmm_raw_data": {
    "loggedAt": "2026-06-24T12:27:51.219",
    "status": "scheduled",
    "runId": "20260624-122709-3bfc7bc5",
    "stepIndex": 333,
    "modelTime": "2026-06-16T00:05:33",
    "reason": "new_issue",
    "highestSeverity": "CRITICAL",
    "riskEventCount": 1,
    "triggeredIssues": [
      {
        "issueId": "REVERSE_FLOW:link:pipe_free_1781771885636",
        "eventType": "REVERSE_FLOW",
        "severity": "CRITICAL",
        "sourceId": "pipe_free_1781771885636",
        "displayName": "파이프",
        "fromNode": "teeConnector_copy_1781771853047_1",
        "fromNodeName": "T자 커넥터",
        "toNode": "CONN_COMB_01",
        "toNodeName": "합류식 커넥터 01"
      }
    ]
  },
  "TELEGRAM_BOT_TOKEN": "123456:telegram-token",
  "TELEGRAM_CHAT_ID": ["123456789"]
}
```

`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`는 선택 필드다. `TELEGRAM_CHAT_ID`는
문자열, 숫자, 또는 문자열/숫자 배열을 받을 수 있고 서버 내부에서는 문자열
배열로 정규화한다. `TELEGRAM_CHAT_ID` 필드가 생략된 경우에만 env chat ID로
fallback하며, 빈 리스트가 명시된 경우에는 env chat ID로 대체하지 않는다.
body와 env 양쪽에 Telegram 값이 없으면 분석은 생성되더라도 Telegram 발송
단계에서 서버 설정 오류로 실패한다.

성공 응답:

```json
{
  "id": "폭우",
  "analysis": "1. 현재 위험 상황 요약\n...",
  "contextSummary": {
    "hasLinkData": true,
    "hasNodeData": false,
    "hasEditorObjectData": true,
    "linkCount": 1,
    "nodeCount": 0,
    "editorObjectCount": 2,
    "issueCount": 1,
    "priorityTargetCount": 1,
    "priorityTargets": [
      {
        "rank": 1,
        "targetId": "pipe_free_1781771885636",
        "riskLabel": "만관 예측",
        "priorityScore": 92,
        "priorityBand": "P1",
        "priorityReasons": ["CRITICAL 위험", "만관 위험"]
      }
    ],
    "pastHistoryCount": 1,
    "past_history": [
      {
        "id": "vector-id",
        "sourceId": "pipe_free_1781771885636",
        "action_details": "[도시침수 위험 대응 사례]\n...",
        "loggedAt": "2026-06-26T06:52:00+00:00"
      }
    ]
  },
  "telegram": {
    "sentTo": ["123456789"],
    "sentCount": 1
  }
}
```

`contextSummary.priorityTargets`와 `llmInput.priorityTargets`에는 같은 현장
우선순위 배열이 포함된다. LLM 답변의 "현장 확인 순서"는 이 배열의 `rank` 순서를
따라 작성된다.

### SWMM raw data 파싱 규칙

`swmm_raw_data`에서 위험 이슈는 다음 키에서 수집한다.

| 키                 | 위치                |
| ------------------ | ------------------- |
| `triggeredIssues`  | root 또는 `context` |
| `triggered_issues` | root 또는 `context` |
| `issues`           | root 또는 `context` |
| `riskEvents`       | root 또는 `context` |
| `risk_events`      | root 또는 `context` |
| `events`           | root 또는 `context` |
| `dispatchKey`      | root                |

`dispatchKey`만 있는 경우에도
`{runId}:{stepIndex}:{eventType}:{category}:{elementId}:{severity}:...` 형식이면
이슈를 생성한다.

Django forecast payload의 `riskEvents`는 다음 우선순위 필드를 포함할 수 있다.

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `priorityScore` | number/string | Django가 계산한 현장 조치 우선순위 점수 |
| `priorityBand` | string | `P1`, `P2`, `P3`, `P4` 중 하나 |
| `priorityReasons` | array | 우선순위 산정 근거 |

이 필드가 있으면 LLM 서버는 값을 그대로 보존해 `priorityTargets`를 만든다. 이
필드가 없으면 LLM 서버가 severity, 위험 유형, 주요 metric을 기준으로 보수적인
fallback 우선순위를 만든다.

분석 입력으로 전달되는 `priorityTargets` 예시:

```json
[
  {
    "rank": 1,
    "targetId": "PIPE_1",
    "targetType": "link",
    "riskLabel": "만관 예측",
    "riskCode": "PREDICTED_FULL_PIPE",
    "severity": "치명",
    "severityCode": "CRITICAL",
    "priorityScore": 92,
    "priorityBand": "P1",
    "priorityReasons": ["CRITICAL 위험", "만관 위험", "예측 증가량 0.09"],
    "prioritySource": "django",
    "metrics": {
      "metric": "fullness",
      "currentValue": 0.9,
      "predictedValue": 0.99,
      "forecastMinutes": 10
    }
  }
]
```

LLM은 현장 우선순위를 직접 추정하지 않고 `priorityTargets.rank` 순서를 따라야
한다. `priorityTargets`가 비어 있으면 확정 순위를 만들지 않는다.

이슈를 찾지 못하면 `400 Bad Request`를 반환한다.

```json
{
  "detail": "swmm_raw_data에서 이슈를 찾지 못했습니다. ..."
}
```

## 유지보수 이력 저장 API

### Django 위험 조치 이력 임베딩 저장

- Method: `POST`
- Path: `/llm/maintenance/log`
- 성공: `200 OK`
- 실패: `400 Bad Request`, `422 Unprocessable Entity`, `500 Internal Server Error`

Trailing slash가 붙은 `/llm/maintenance/log/`도 같은 handler로 처리한다.

Django의 위험 로그 조치 저장 이후 호출되는 endpoint다. 전달받은 `event`,
`metrics`, `action` payload를 임베딩에 적합한 텍스트로 포맷한 뒤
`text-embedding-3-small`로 임베딩하고 ChromaDB `maintenance_logs` collection에
저장한다.

요청:

```json
{
  "event": {
    "id": 1,
    "run_id": "20260624-164620-7faf56be",
    "step_index": 3087,
    "model_time": "2026-06-16T00:51:27",
    "target_id": "PIPE_1",
    "source": "link",
    "hazard_type": "REVERSE_FLOW",
    "hazard_level": "CRITICAL",
    "hazard_detail": "파이프 PIPE_1에서 역류가 감지되었습니다.",
    "priority": {
      "priorityScore": 92,
      "priorityBand": "P1",
      "priorityReasons": ["CRITICAL 위험", "만관 위험"]
    },
    "created_at": "2026-06-26T15:51:00"
  },
  "metrics": {
    "flowCms": -0.034,
    "direction": "reverse",
    "fullness": 0.92,
    "capacityRatio": 1.2,
    "blockageRatio": 0.4
  },
  "action": {
    "status": "RESOLVED",
    "initial_action_detail": "하류 관로 현장 점검 완료",
    "action_type": "FIELD_CHECK",
    "result_detail": "토사 제거 후 수위 안정화",
    "result_status": "RESOLVED",
    "recurrence_note": "폭우 시 상류 맨홀 우선 점검",
    "created_at": "2026-06-26T15:52:00"
  }
}
```

필수 필드:

| 필드                           | 타입           | 필수   | 설명                                                           |
| ------------------------------ | -------------- | ------ | -------------------------------------------------------------- |
| `event.id`                     | integer/string | 예     | Django 위험 이벤트 ID                                          |
| `event.target_id`              | string         | 예     | SWMM link/node 등 대상 ID. ChromaDB metadata `sourceId`로 저장 |
| `event.priority`               | object         | 아니요 | Django가 계산한 현장 조치 우선순위 |
| `metrics`                      | object         | 아니요 | 당시 주요 수치 snapshot                                        |
| `action`                       | object         | 예     | 조치 및 결과 정보                                              |
| `action.initial_action_detail` | string         | 조건부 | `result_detail`이 없으면 필수                                  |
| `action.result_detail`         | string         | 조건부 | `initial_action_detail`이 없으면 필수                          |

`action.initial_action_detail`과 `action.result_detail` 중 적어도 하나는 비어 있지
않아야 한다.

성공 응답:

```json
{
  "id": "2c21d91c-f3fc-401a-b8aa-a4cc7b13adbd",
  "vector_id": "2c21d91c-f3fc-401a-b8aa-a4cc7b13adbd",
  "sourceId": "PIPE_1",
  "action_details": "[도시침수 위험 대응 사례]\n\n이벤트 ID: 1\n시설 ID: PIPE_1\n...",
  "embedding_text": "[도시침수 위험 대응 사례]\n\n이벤트 ID: 1\n시설 ID: PIPE_1\n...",
  "loggedAt": "2026-06-26T06:52:00.000000+00:00"
}
```

`action_details`와 `embedding_text`는 현재 같은 포맷 텍스트를 반환한다.

### 임베딩 텍스트 포맷

저장 전 payload는 다음 형태의 텍스트로 변환된다.

```text
[도시침수 위험 대응 사례]

이벤트 ID: 1
시설 ID: PIPE_1
시설 유형: link
위험 유형: REVERSE_FLOW
위험 등급: CRITICAL
위험 상세: 파이프 PIPE_1에서 역류가 감지되었습니다.
발생 시각: 2026-06-26T15:51:00
모델 시각: 2026-06-16T00:51:27
실행 ID: 20260624-164620-7faf56be
스텝: 3087

주요 지표:
- 유량: -0.034 m3/s
- 흐름 방향: reverse
- 만관율: 92.0%
- 용량 비율: 120.0%
- 막힘 비율: 40.0%

조치:
- 상태: RESOLVED
- 조치 유형: FIELD_CHECK
- 초기 조치: 하류 관로 현장 점검 완료
- 결과: 토사 제거 후 수위 안정화
- 결과 상태: RESOLVED
- 조치 시각: 2026-06-26T15:52:00

재발 시 참고사항:
폭우 시 상류 맨홀 우선 점검
```

ChromaDB metadata:

| 이름           | 값                                     |
| -------------- | -------------------------------------- |
| `sourceId`     | `event.target_id`                      |
| `loggedAt`     | FastAPI 서버 저장 시각, UTC ISO string |
| `eventId`      | `event.id`                             |
| `hazardType`   | `event.hazard_type`                    |
| `hazardLevel`  | `event.hazard_level`                   |
| `priorityBand` | `event.priority.priorityBand`          |
| `priorityScore` | `event.priority.priorityScore`        |
| `actionStatus` | `action.status`                        |
| `resultStatus` | `action.result_status`                 |

## 과거 이력 조회 방식

`/llm/analyze/preview`와 `/llm/analyze`는 LLM 입력 payload에서 source id를
추출한 뒤 ChromaDB에서 같은 `sourceId` metadata를 가진 유지보수 이력을 조회한다.

source id 추출 순서:

1. `llmInput.link[].id`
2. `llmInput.swmmIssues[].primaryElement.id`

따라서 `/llm/maintenance/log` 저장 시 `event.target_id`는 분석 payload의 link id 또는
issue primary element id와 같은 값을 사용해야 한다.

## Django 연동 메모

Django API 명세서 기준으로 위험 로그 조치 저장 후 FastAPI 연동 URL은
`SUPERMARIO_LLM_MAINTENANCE_LOG_URL`로 지정한다. 이 서버의 현재 구현에 맞추려면
`LLM_API_PREFIX=/llm` 기본 설정에서 다음 URL을 사용해야 한다.

```text
http://127.0.0.1:8001/llm/maintenance/log
```

또는 운영 환경:

```text
https://supermario.o-r.kr/llm/maintenance/log
```
