# SuperMario LLM Server

FastAPI + LangChain 기반 침수 위험 분석 서버입니다.

## URL Prefix

이 서비스는 기본적으로 `/llm` prefix 아래에서 동작합니다.

| 환경 | Base URL |
| --- | --- |
| local | `http://127.0.0.1:8001/llm` |
| prod | `https://supermario.o-r.kr/llm` |

주요 endpoint:

```text
GET  /llm/health
POST /llm/analyze
POST /llm/maintenance/log
```

## Local 실행

```bash
cp .env.example .env
uvicorn main:app --host 0.0.0.0 --port 8001
```

Docker Compose로 실행할 때는 host `8001` 포트가 컨테이너 `8000` 포트로 연결됩니다.
