# SuperMario LLM Server

SuperMario LLM Server는 Django 서버가 전달한 도시침수 위험 데이터를 현장 담당자가 읽기 쉬운 한국어 보고 문구로 변환하고, Telegram으로 발송하는 FastAPI 기반 서버다.

분석 과정에서는 위험 데이터를 정형화하고, 필요한 경우 ChromaDB에 저장된 과거 조치 이력을 조회한다. 유지보수 이력 저장 API는 조치 기록을 embedding에 적합한 텍스트로 포맷한 뒤 vector DB에 저장한다.

## 주요 기능

- 위험 분석: `POST /llm/analyze`
- 분석 입력 미리보기: `POST /llm/analyze/preview`
- 유지보수 이력 저장: `POST /llm/maintenance/log`
- 상태 확인: `GET /llm/health`
- LLM 입출력 debug log 저장: `llm-debug/`

## 실행 환경

- Python 3.11
- FastAPI, Uvicorn, Pydantic v2
- LangChain OpenAI
- ChromaDB
- python-telegram-bot
- Docker Compose

## 환경변수

`.env.example`을 기준으로 `.env`를 만든다.

```powershell
cp .env.example .env
```

주요 환경변수:

| 이름 | 설명 |
| --- | --- |
| `LLM_API_PREFIX` | 기본 API prefix. 기본값은 `/llm` |
| `OPENAI_API_KEY` | OpenAI Chat/Embedding 호출에 필요 |
| `CHROMA_PERSIST_DIR` | ChromaDB 저장 경로 |
| `LLM_DEBUG_LOG_ENABLED` | LLM debug log 저장 여부 |
| `LLM_DEBUG_LOG_DIR` | LLM debug log 저장 경로 |
| `TELEGRAM_BOT_TOKEN` | `/llm/analyze` body에 토큰이 없을 때 사용할 Telegram bot token |
| `TELEGRAM_CHAT_ID` | `/llm/analyze` body에 chat id가 없을 때 사용할 Telegram chat id. 여러 개는 콤마로 구분 |

Telegram 메시지 발송은 `/llm/analyze` 요청 body의 `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`를 우선 사용한다. body에서 토큰이 비어 있거나 chat ID 필드가 생략되면 `.env`의 Telegram 값을 fallback으로 사용한다. 단, `TELEGRAM_CHAT_ID: []`처럼 빈 리스트가 명시되면 DB 수신자가 없는 상태로 보고 env chat ID로 대체하지 않는다. 운영 Docker Compose에서는 Infra가 생성한 `.env`가 LLM 컨테이너에도 주입된다.

현재 운영 배포에서는 LLM 이미지에 secret을 굽지 않는다. `SuperMario_Infra`의 `PRODUCTION_ENV_YAML_B64`가 서버 `.env`로 렌더링되고, `llm-blue`/`llm-green` 컨테이너가 해당 `.env`를 `env_file`로 읽는다.

## 로컬 실행

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8001
```

확인:

```powershell
Invoke-WebRequest http://127.0.0.1:8001/llm/health
```

## Docker Compose 실행

```powershell
docker compose up -d --build
```

Docker Compose에서는 host `8001` 포트가 container `8000` 포트로 연결된다.

`.env`를 변경했다면 컨테이너 단순 재시작이 아니라 재생성이 필요하다.

```powershell
docker compose down
docker compose up -d --build
```

## 문서

세부 문서는 `docs/`에 정리되어 있다.

| 문서 | 내용 |
| --- | --- |
| `docs/llm-api-spec.md` | API 명세 |
| `docs/priority-policy.md` | 현장 조치 우선순위 정책 |
| `docs/features.md` | 기능 설명 |
| `docs/technical-stack.md` | 기술 구성 |
| `docs/data-model.md` | 데이터 모델과 vector DB 구조 |
| `docs/architecture.md` | 통신 흐름과 모듈 역할 |
| `docs/operations.md` | 실행, 점검, 장애 확인 |

## 테스트 참고

현재 저장소에는 포맷터와 유지보수 저장 로직 중심의 테스트 파일이 있다.

```powershell
.\.venv\Scripts\python.exe -m compileall swmm_formatter.py analyzer.py main.py maintenance_store.py test_swmm_formatter.py test_maintenance_store.py llm_debug_logger.py
```

`pytest`가 설치되어 있지 않은 환경에서는 직접 함수 호출 방식으로 테스트할 수 있다.
