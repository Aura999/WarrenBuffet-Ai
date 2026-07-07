# WarrenBuffet.Ai

A FastAPI and LangGraph-ready backend for a financial research copilot.

## Current Status

Phase 6 voice interface.

This phase adds audio transcription and text-to-speech endpoints. The graph still supports yfinance market data, Tavily news, OpenAI sentiment analysis, PDF upload, FAISS RAG, and document-aware synthesis. Docker is not connected yet.

## Run Locally

1. Create a virtual environment:

   ```powershell
   python -m venv .venv
   ```

2. Activate the virtual environment:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

3. Install requirements:

   ```powershell
   pip install -r requirements.txt
   ```

4. Create `.env` from `.env.example`:

   ```powershell
   Copy-Item .env.example .env
   ```

   Put real API keys and other secrets only in `.env`. Never store real secrets in `.env.example`; it must contain placeholders only.

   Required for LLM responses:

   ```env
   OPENAI_API_KEY=your_real_openai_key
   OPENAI_MODEL=gpt-4o-mini
   OPENAI_EMBEDDING_MODEL=text-embedding-3-small
   OPENAI_TRANSCRIPTION_MODEL=whisper-1
   TTS_PROVIDER=gtts
   ```

   Optional for news retrieval:

   ```env
   TAVILY_API_KEY=your_real_tavily_key
   ```

5. Run the backend:

   ```powershell
   uvicorn app.main:app --reload
   ```

Swagger docs will be available at `http://127.0.0.1:8000/docs`.

## API Endpoints

- `GET /`
- `GET /api/health`
- `POST /api/chat`
- `POST /api/documents/upload`
- `GET /api/documents`
- `GET /api/documents/{document_id}`
- `GET /api/documents/{document_id}/chunks/{chunk_index}`
- `DELETE /api/documents/{document_id}`
- `POST /api/voice/transcribe`
- `POST /api/voice/tts`
- `POST /api/voice/chat`

## Voice

Transcription uses the OpenAI audio transcription API with `OPENAI_TRANSCRIPTION_MODEL`, defaulting to `whisper-1`.

Text-to-speech uses `gTTS` for a simple local demo MVP. Long answers are shortened before speech generation.

Supported upload formats:

- `.mp3`
- `.wav`
- `.m4a`
- `.webm`
- `.ogg`

Transcribe audio:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/voice/transcribe" `
  -F "file=@question.wav"
```

Generate speech:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/voice/tts" `
  -H "Content-Type: application/json" `
  -d "{\"text\":\"Reliance Industries is a diversified Indian conglomerate.\"}" `
  --output answer.mp3
```

## PDF Upload

Upload one or more PDFs with multipart form data:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/documents/upload" `
  -F "files=@annual_report.pdf"
```

Example response:

```json
{
  "success": true,
  "documents": [
    {
      "document_id": "doc_xxx",
      "filename": "annual_report.pdf",
      "page_count": 120,
      "character_count": 250000,
      "chunk_count": 180,
      "status": "indexed"
    }
  ]
}
```

Documents are stored in memory for local development. Uploaded files are processed through a temp file and removed after indexing. Document registry and FAISS indexes are not persisted after server restart.

## Chat Example

Request:

```json
{
  "query": "Create an investor brief using this annual report, current market data, and latest news",
  "ticker": "RELIANCE.NS",
  "document_ids": ["doc_xxx"]
}
```

Response:

```json
{
  "success": true,
  "query": "Create an investor brief using this annual report, current market data, and latest news",
  "answer": "### Market Snapshot\n...\n\n### News & Sentiment Snapshot\n...\n\n### Document Insights\n- Key document-backed findings: ...\n- Relevant pages: annual_report.pdf page 12\n- Important caveats: Only relevant excerpts were retrieved.\n\n### 1. Executive Summary\n...",
  "sources": [
    "yfinance",
    "https://example.com/news-article",
    {
      "type": "document",
      "document_id": "doc_xxx",
      "filename": "annual_report.pdf",
      "page_number": 12,
      "chunk_index": 5
    }
  ]
}
```

When a ticker is provided and yfinance returns usable data, the answer starts with a deterministic `### Market Snapshot` section before the research analysis. The snapshot includes current price, previous close, day change, day change percent, day high/low, volume, market cap, 52-week high/low, currency, exchange, and a yfinance delay note. Market data from yfinance may be delayed and should not be treated as financial advice.

When Tavily returns recent news, the answer includes a deterministic `### News & Sentiment Snapshot` section with overall sentiment, key news drivers, a short news summary, and article sources. News data comes from Tavily search results and may be incomplete. The output is research assistance, not financial advice.

If `TAVILY_API_KEY` is missing, the backend still runs. Market data still works, and the answer should say recent news could not be fetched in that run.

When `document_ids` are provided, the backend retrieves relevant PDF chunks from FAISS and passes them to the synthesis agent. Document answers are grounded in retrieved excerpts, not necessarily the whole document. The model is instructed to cite document context inline with labels such as `[Document Source 1]`.

If no document is uploaded and the user asks a document question, the answer should ask the user to upload a PDF first.

Example tickers:

- `RELIANCE.NS`
- `HDFCBANK.NS`
- `INFY.NS`
- `TCS.NS`
- `AAPL`
- `MSFT`
- `TATAMOTORS.NS`
- `ZOMATO.NS`

If no ticker is provided, `/api/chat` still works without market data. If a ticker is invalid or yfinance is unavailable, the response should say market data could not be fetched without crashing the backend.

More example requests:

```json
{
  "query": "Why is Tata Motors moving recently?",
  "ticker": "TATAMOTORS.NS"
}
```

```json
{
  "query": "What are the key risks for Zomato based on recent news?",
  "ticker": "ZOMATO.NS"
}
```

## Upcoming Phases

1. LangGraph text agent
2. Market data agent
3. News + sentiment agent
4. PDF RAG
5. Voice interface
6. Dockerization
