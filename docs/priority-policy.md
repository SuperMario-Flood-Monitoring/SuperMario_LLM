# 우선순위 정책

## 목적

현장 조치 우선순위는 LLM이 임의로 판단하지 않고, 입력 payload에 포함된
`priorityScore`, `priorityBand`, `priorityReasons`를 기준으로 정한다.

## 입력 위치

Django forecast payload의 `riskEvents[]` 항목은 다음 필드를 포함할 수 있다.

```json
{
  "priorityScore": 210.0,
  "priorityBand": "P1",
  "priorityReasons": ["CRITICAL 위험", "용량 초과 위험"]
}
```

## 처리 규칙

1. Django가 우선순위 필드를 보내면 LLM 서버는 이를 그대로 보존한다.
2. `priorityTargets`는 `priorityBand`, `priorityScore`, `targetId` 기준으로 정렬된다.
3. LLM 프롬프트는 `priorityTargets.rank` 순서를 따르도록 제한한다.
4. Django 우선순위 필드가 없으면 LLM 서버가 보수적인 fallback 우선순위를 만든다.
5. fallback 우선순위는 severity, 위험 유형, 주요 metric 값으로만 계산한다.
6. `priorityTargets`가 없으면 LLM은 확정 순위를 만들지 않는다.

## priorityTargets 구조

```json
{
  "rank": 1,
  "targetId": "REL_061_CONDUIT",
  "targetType": "link",
  "riskLabel": "관로 용량 초과 예측",
  "riskCode": "PREDICTED_CAPACITY_EXCEEDED",
  "severity": "치명",
  "severityCode": "CRITICAL",
  "priorityScore": 210.0,
  "priorityBand": "P1",
  "priorityReasons": ["CRITICAL 위험", "용량 초과 위험"],
  "prioritySource": "django"
}
```

## 현장 보고 표현

LLM 답변은 개발 용어를 그대로 출력하지 않는다.

| 내부 코드 | 현장 표현 |
| --- | --- |
| `link` | 관로 |
| `node` | 맨홀/집수구/주변 지점 |
| `PREDICTED_FULL_PIPE` | 만관 예측 |
| `PREDICTED_NODE_DEPTH` | 수위 상승 예측 |
| `PREDICTED_CAPACITY_EXCEEDED` | 관로 용량 초과 가능성 |
| `CRITICAL` | 매우 위험 |

`editorObject`는 현장 보고에 출력하지 않는다.

