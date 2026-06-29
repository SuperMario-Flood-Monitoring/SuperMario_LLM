# 기술 문서

## Runtime

- Python 3.11
- FastAPI
- Uvicorn
- Pydantic v2

## LLM

- `langchain-openai`
- Chat 모델: `gpt-4o-mini`
- Embedding 모델: `text-embedding-3-small`

모델 API key는 `OPENAI_API_KEY` 환경변수로 전달한다.

## Vector DB

- ChromaDB PersistentClient
- 기본 로컬 경로: `./chroma_data`
- Docker Compose 경로: `/app/chroma_data`
- Collection: `maintenance_logs`

## Telegram

- `python-telegram-bot`
- `/llm/analyze` 요청 body의 `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`를 사용한다.
- `.env`의 Telegram 값은 로컬 `test_bot.py setup` 용도다.

## Docker

`docker-compose.yml`은 `api` 서비스를 정의한다.

- host port: `8001`
- container port: `8000`
- container name: `flood-api`
- env file: `.env`
- ChromaDB volume: `chroma_data:/app/chroma_data`

`.env` 변경 후 컨테이너는 단순 재시작이 아니라 재생성해야 한다.

```powershell
docker compose down
docker compose up -d --build
```

