# Developer Notes

## Run Backend Locally

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend docs:

```text
http://127.0.0.1:8000/docs
```

Health check:

```text
http://127.0.0.1:8000/api/health
```

## Run Frontend Locally

```powershell
cd frontend
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Frontend:

```text
http://localhost:8501
```

The frontend uses `BACKEND_URL` from the environment when available. Without it, the local fallback is `http://127.0.0.1:8000`.

## Run With Docker

From the project root:

```powershell
copy .env.example .env
```

Fill:

- `OPENAI_API_KEY`
- `TAVILY_API_KEY`

Then run:

```powershell
docker compose up --build
```

Open:

- Streamlit: `http://localhost:8501`
- FastAPI Docs: `http://localhost:8000/docs`

## Test `/api/chat` From Swagger

1. Start the backend.
2. Open `http://127.0.0.1:8000/docs`.
3. Expand `POST /api/chat`.
4. Try:

```json
{
  "query": "Hi bro, how are you?",
  "ticker": null,
  "document_ids": null
}
```

Expected: short conversational WarrenBuffet.Ai response with empty sources.

Financial query:

```json
{
  "query": "Analyze Reliance Industries using current market data",
  "ticker": "RELIANCE.NS",
  "document_ids": []
}
```

Expected: structured research answer with market snapshot when yfinance is available.

## Test PDF Upload

1. Start backend and frontend.
2. In Streamlit sidebar, upload one or more PDF annual reports.
3. Click `Upload & Index PDFs`.
4. Select the uploaded document.
5. Ask:

```text
Summarize the key risks from this annual report.
```

Expected: document-grounded answer with source metadata. Uploaded documents are in memory and reset after backend restart.

## Test Voice

1. Open the Voice Assistant tab in Streamlit.
2. Record in the browser or upload an audio file.
3. Ask a casual or financial question.
4. Click `Analyze Voice Question`.
5. Optionally enable spoken answer generation.

Expected: transcript appears, then the same intent routing and research pipeline used by text chat runs.

## Common Issues

Docker Desktop not running:

- Start Docker Desktop before running `docker compose up --build`.

`BACKEND_URL` mismatch:

- Local frontend should use `http://127.0.0.1:8000`.
- Docker frontend should use `http://backend:8000`.

Missing `.env`:

- Copy `.env.example` to `.env` at the project root for Docker.
- Keep real secrets out of Git.

Invalid OpenAI key:

- Chat, embeddings, PDF indexing, and transcription can fail if `OPENAI_API_KEY` is missing or invalid.

Tavily missing:

- News retrieval and sentiment context can fail or be skipped if `TAVILY_API_KEY` is missing.

Uploaded docs reset after restart:

- The current document store is in memory. Restarting the backend or Docker container clears uploaded PDF indexes.
