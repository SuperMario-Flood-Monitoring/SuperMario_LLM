# 운영 문서

## 로컬 실행

```powershell
cp .env.example .env
.\.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8001
```

## Docker Compose 실행

```powershell
docker compose up -d --build
```

`.env`를 변경했다면 기존 컨테이너를 재생성한다.

```powershell
docker compose down
docker compose up -d --build
```

컨테이너 내부 환경변수 확인:

```powershell
docker exec flood-api python -c "import os; k=os.getenv('OPENAI_API_KEY'); print(k[:12], k[-4:], len(k))"
```

## 필수 환경변수

| 이름 | 설명 |
| --- | --- |
| `OPENAI_API_KEY` | OpenAI Chat/Embedding 호출에 필요 |
| `LLM_API_PREFIX` | 기본 `/llm` |
| `CHROMA_PERSIST_DIR` | ChromaDB 저장 경로 |
| `LLM_DEBUG_LOG_ENABLED` | debug log 저장 여부 |
| `LLM_DEBUG_LOG_DIR` | debug log 저장 경로 |

## Endpoint 확인

```powershell
Invoke-WebRequest http://127.0.0.1:8001/llm/health
```

## ChromaDB 비어 있는지 확인

```powershell
.\.venv\Scripts\python.exe -c "import chromadb; c=chromadb.PersistentClient(path='./chroma_data'); col=c.get_or_create_collection('maintenance_logs'); print(col.count())"
```

## OpenAI 401 오류

`invalid_api_key`가 발생하면 서버가 사용하는 `OPENAI_API_KEY`가 유효하지 않거나
컨테이너에 새 값이 반영되지 않은 상태다.

확인 순서:

1. `.env`의 `OPENAI_API_KEY`가 새 키인지 확인
2. Docker 컨테이너 내부 환경변수 확인
3. `docker compose down` 후 `docker compose up -d --build`
4. 그래도 실패하면 OpenAI Platform에서 키 상태 재확인

