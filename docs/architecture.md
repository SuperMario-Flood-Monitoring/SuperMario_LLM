# 아키텍처 문서

## 역할

이 저장소는 SuperMario 시스템 중 LLM 분석 서버 역할을 맡는다. Django 서버가
위험 데이터를 만들고, 이 FastAPI 서버는 해당 데이터를 현장 보고 문구로 변환해
Telegram으로 발송한다.

## 통신 흐름

```text
Django
  -> POST /llm/analyze
     -> FastAPI LLM Server
        -> swmm_formatter.py: 위험 데이터 정형화
        -> maintenance_store.py: 과거 조치 이력 조회
        -> analyzer.py: OpenAI Chat 호출
        -> telegram_notifier.py: Telegram 발송
  <- 분석 결과 및 발송 결과
```

유지보수 이력 저장:

```text
Django
  -> POST /llm/maintenance/log
     -> FastAPI LLM Server
        -> maintenance_store.py: 대응 사례 텍스트 포맷
        -> OpenAI Embeddings
        -> ChromaDB maintenance_logs 저장
  <- vector_id, sourceId, embedding_text
```

## 주요 모듈

| 파일 | 역할 |
| --- | --- |
| `main.py` | FastAPI app, endpoint, request validation |
| `swmm_formatter.py` | 위험 데이터 파싱, LLM 입력 payload 생성 |
| `analyzer.py` | 시스템 프롬프트, OpenAI Chat 호출 |
| `telegram_notifier.py` | Telegram 메시지 발송 |
| `maintenance_store.py` | ChromaDB 저장/조회, 유지보수 이력 포맷 |
| `llm_debug_logger.py` | 테스트용 LLM 입출력 저장 |
| `scenarios.py` | 강수 시나리오별 기상 관측 예시 |

## 외부 의존성

- Django 서버: 위험 이벤트와 조치 payload를 전달
- OpenAI API: 분석 문구 생성 및 embedding 생성
- Telegram Bot API: 메시지 발송
- ChromaDB: 과거 조치 이력 저장

