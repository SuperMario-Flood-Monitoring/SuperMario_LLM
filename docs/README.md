# SuperMario LLM 문서

이 디렉터리는 SuperMario LLM 서버의 정책, 기능, 기술 구성, 데이터 모델, 통신
흐름을 정리한다. 내용은 이 저장소의 코드와 설정에서 확인 가능한 정보만 기준으로
작성한다.

## 문서 목록

| 문서 | 설명 |
| --- | --- |
| `llm-api-spec.md` | FastAPI endpoint, 요청/응답, Django 연동 payload |
| `priority-policy.md` | 현장 조치 우선순위 처리 정책 |
| `features.md` | 분석, 텔레그램 발송, 과거 조치 이력 저장 기능 |
| `technical-stack.md` | FastAPI, LangChain, ChromaDB, Docker 구성 |
| `data-model.md` | LLM 입력 payload, ChromaDB metadata, debug log 구조 |
| `architecture.md` | Django, LLM 서버, OpenAI, Telegram 사이의 통신 흐름 |
| `operations.md` | 실행, 환경변수, Docker 재생성, debug log 확인 |

