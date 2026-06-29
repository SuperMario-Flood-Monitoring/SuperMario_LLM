# 데이터 모델 문서

## Analyze 요청

```json
{
  "id": "폭우",
  "swmm_raw_data": {},
  "TELEGRAM_BOT_TOKEN": "telegram-token",
  "TELEGRAM_CHAT_ID": ["123456789"]
}
```

`swmm_raw_data`는 JSON object 또는 JSON 문자열을 받을 수 있다.

## LLM 입력 payload

`swmm_formatter.build_analysis_payload()`는 다음 구조를 만든다.

```json
{
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
```

`editorObject`는 내부 입력에는 남아 있지만 현장 답변에는 출력하지 않는다.

## priorityTargets

```json
{
  "rank": 1,
  "targetId": "PIPE_1",
  "targetType": "link",
  "riskLabel": "만관 예측",
  "priorityScore": 92,
  "priorityBand": "P1",
  "priorityReasons": ["CRITICAL 위험", "만관 위험"],
  "prioritySource": "django"
}
```

`prioritySource` 값:

- `django`: Django가 보낸 우선순위를 사용
- `fallback`: LLM 서버가 입력 metric으로 보수 계산

## ChromaDB 문서

Collection: `maintenance_logs`

Document에는 포맷된 대응 사례 텍스트가 저장된다.

Metadata:

| 이름 | 설명 |
| --- | --- |
| `sourceId` | 대상 시설 ID |
| `loggedAt` | FastAPI 서버 저장 시각 |
| `eventId` | Django 위험 이벤트 ID |
| `hazardType` | 위험 유형 |
| `hazardLevel` | 위험 등급 |
| `priorityBand` | 현장 조치 우선순위 등급 |
| `priorityScore` | 현장 조치 우선순위 점수 |
| `actionStatus` | 조치 상태 |
| `resultStatus` | 결과 상태 |

## Debug log

입력 로그:

```json
{
  "debugId": "20260629T000000000000Z____run_12345678",
  "loggedAt": "2026-06-29T00:00:00+00:00",
  "analysisInput": {},
  "invokeMessages": []
}
```

답변 로그는 LLM 답변 text를 그대로 저장한다.

