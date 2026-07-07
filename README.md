# WarrenBuffet.Ai

AI-powered financial research copilot designed and built by Satyam Mishra.

## Overview

WarrenBuffet.Ai combines market data, news sentiment, annual report RAG, and voice interaction to generate investor-style research assistance. It helps users analyze companies, summarize uploaded PDFs, inspect market snapshots, retrieve recent news context, and generate structured financial research outputs.

This is research assistance, not financial advice.

## Key Features

- Branded conversational assistant
- Casual chat and intent routing
- Company and stock analysis
- Market snapshot using yfinance
- News retrieval using Tavily
- News sentiment summarization
- Annual report / PDF analysis
- FAISS-based document retrieval
- OpenAI embeddings
- Voice transcription
- TTS spoken answer
- Streamlit UI
- FastAPI backend
- Docker Compose support

## Architecture

```text
User
|
v
Streamlit Frontend
|
v
FastAPI Backend
|
v
Intent Router
|
+-- Conversation Agent
|
+-- Financial Research Graph
```

Financial Research Graph:

```text
Supervisor
|
v
Market Data Agent
|
v
News Agent
|
v
Sentiment Agent
|
v
Document RAG Agent
|
v
Synthesis Agent
|
v
Structured Research Answer
```

Document pipeline:

```text
PDF Upload
|
v
PyMuPDF text extraction
|
v
Chunking
|
v
OpenAI embeddings
|
v
FAISS vector store
|
v
Top-k retrieval
|
v
RAG-grounded response
```

Voice pipeline:

```text
Audio input
|
v
OpenAI transcription
|
v
Intent router
|
v
Research/conversation response
|
v
Optional gTTS audio output
```

## Tech Stack

Backend:

- Python
- FastAPI
- LangGraph
- LangChain
- OpenAI API
- yfinance
- Tavily
- PyMuPDF
- FAISS
- gTTS

Frontend:

- Streamlit
- streamlit-mic-recorder
- requests

Infra:

- Docker
- Docker Compose
- dotenv

## Project Structure

```text
WarrenBuffet.Ai/
├── backend/
│   ├── app/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .dockerignore
├── frontend/
│   ├── streamlit_app.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .dockerignore
├── screenshots/
│   └── README.md
├── docker-compose.yml
├── .env.example
├── .gitignore
├── ARCHITECTURE.md
├── DEMO_SCRIPT.md
├── DEV_NOTES.md
├── SCREENSHOTS.md
└── README.md
```

## Setup Without Docker

Backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend:

```powershell
cd frontend
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Setup With Docker

```powershell
cd project-root
copy .env.example .env
```

Then fill:

- `OPENAI_API_KEY`
- `TAVILY_API_KEY`

Run:

```powershell
docker compose up --build
```

Open:

- Streamlit: http://localhost:8501
- FastAPI Docs: http://localhost:8000/docs

## Environment Variables

- `OPENAI_API_KEY`: API key used for synthesis, embeddings, and transcription.
- `OPENAI_MODEL`: Chat model for reasoning and synthesis.
- `OPENAI_EMBEDDING_MODEL`: Embedding model used for document chunks.
- `OPENAI_TRANSCRIPTION_MODEL`: Audio transcription model.
- `TAVILY_API_KEY`: Tavily key used for company-specific news retrieval.
- `TTS_PROVIDER`: Text-to-speech provider. Current default is `gtts`.
- `BACKEND_URL`: Frontend target backend URL. Use `http://127.0.0.1:8000` locally and `http://backend:8000` inside Docker Compose.

Never commit `.env`.

## Example Queries

Casual:

- Hi bro, how are you?
- Who are you?
- What can you do?

Market:

- Analyze Reliance Industries using current market data.
- Give me the market scenario of Infosys.
- Compare TCS and Infosys.

News:

- What is the latest sentiment around Reliance?
- Summarize recent company-specific news for HDFC Bank.

Document:

- Summarize this annual report.
- What are the key risks mentioned in the uploaded PDF?
- Extract investor insights from this document.
- What does management say about margins?

Voice:

- Analyze Reliance Industries using current market data.
- Summarize the uploaded annual report.

## API Endpoints

- `GET /`
- `GET /api/health`
- `POST /api/chat`
- `POST /api/documents/upload`
- `GET /api/documents`
- `GET /api/documents/{document_id}`
- `GET /api/documents/{document_id}/chunks/{chunk_index}`
- `POST /api/voice/transcribe`
- `POST /api/voice/tts`
- `POST /api/voice/chat`

Sample `/api/chat` request:

```json
{
  "query": "Analyze Reliance Industries using current market data",
  "ticker": "RELIANCE.NS",
  "document_ids": []
}
```

## Current Limitations

- Uploaded documents are currently stored in memory and reset after backend/container restart.
- Market data may be delayed depending on yfinance availability.
- News quality depends on Tavily search results.
- TTS summarizes long responses instead of reading entire reports.
- No authentication yet.
- No persistent user history yet.
- Not financial advice.

## Future Improvements

- Persistent document storage
- PostgreSQL / SQLite metadata store
- ChromaDB / pgvector / persistent FAISS
- User accounts and authentication
- Chat history
- Portfolio watchlist
- Better ticker/company resolution
- Advanced financial ratios
- Earnings call transcript analysis
- Deployment to cloud
- Evaluation and observability with LangSmith

## Disclaimer

This project is for educational and research-assistance purposes only. It does not provide financial advice, investment recommendations, or guaranteed buy/sell signals.
