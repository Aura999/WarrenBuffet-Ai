# WarrenBuffet.Ai Architecture

## High-Level System Design

WarrenBuffet.Ai uses a separated frontend/backend architecture. The Streamlit frontend provides the demo interface for chat, document upload, voice input, and source inspection. The FastAPI backend owns the API contracts, intent routing, financial research graph, PDF processing, vector retrieval, voice transcription, and text-to-speech generation.

This separation keeps the UI lightweight while preserving a reusable backend API that can later support other clients such as mobile apps, browser extensions, or production dashboards.

## Request Lifecycle

For a normal financial query:

1. User enters a query in Streamlit.
2. Frontend sends `POST /api/chat` to the FastAPI backend.
3. Backend intent router classifies the query.
4. If the intent is `financial_analysis`, the LangGraph pipeline runs.
5. Agents collect market, news, sentiment, and document context where relevant.
6. Synthesis agent creates the final structured research answer.
7. Frontend displays the answer and sources.

For casual, identity, capability, planning, or voice-meta questions, the router sends the request to the conversation agent instead of running the financial research graph.

## Intent Router

The intent router prevents every query from becoming a financial report. It separates:

- `casual_chat`
- `identity_question`
- `capability_question`
- `clarification_or_planning`
- `financial_analysis`
- `document_query`
- `voice_meta`

This improves user experience because messages like "Hi bro, how are you?" receive a short branded response instead of a market report. It also prevents identity leakage by routing identity questions through the WarrenBuffet.Ai branded conversation agent.

## Financial Research Graph

The financial research graph is implemented with LangGraph and organizes the research flow into explicit nodes.

- Supervisor: Classifies the financial task type and sets the route for the research response.
- Market Data Agent: Fetches ticker-based market data from yfinance when a ticker is provided.
- News Agent: Retrieves company-specific recent news context through Tavily when the query asks for news, sentiment, or recent movement.
- Sentiment Agent: Summarizes the retrieved news and classifies sentiment using the supplied article titles and snippets.
- Document RAG Agent: Retrieves relevant uploaded PDF chunks from the FAISS vector index.
- Synthesis Agent: Combines market data, news, sentiment, and document context into a structured investor-style answer.

## RAG Pipeline

The document RAG pipeline supports annual report and PDF analysis.

1. User uploads a PDF through Streamlit or `POST /api/documents/upload`.
2. Backend extracts text with PyMuPDF.
3. Extracted text is split into chunks with page metadata.
4. OpenAI embeddings are generated for chunks.
5. Chunks are indexed in a FAISS vector store.
6. For document questions, top-k relevant chunks are retrieved.
7. The synthesis agent answers using retrieved context and returns source metadata.

Sources include document ID, filename, page number, and chunk index so the frontend can fetch and inspect the original source text.

## Voice Pipeline

The voice assistant uses the same backend reasoning path as text chat.

1. User records audio in the browser or uploads an audio file.
2. Backend transcribes the audio using the configured OpenAI transcription model.
3. The transcript is passed through the same intent router used by `/api/chat`.
4. Conversational transcripts receive short branded responses.
5. Financial transcripts run through the research graph.
6. Optional gTTS output generates a spoken MP3 answer.

Because voice uses the shared chat handling path, casual voice messages do not accidentally trigger financial reports.

## Docker Architecture

Docker Compose runs two services:

- `backend`: FastAPI service built from `./backend`, exposed on host port `8000`.
- `frontend`: Streamlit service built from `./frontend`, exposed on host port `8501`.

Both services load shared environment variables from root `.env`. Inside Docker Compose, the frontend calls the backend with:

```env
BACKEND_URL=http://backend:8000
```

From the user's browser, the exposed local URLs are:

- Streamlit: `http://localhost:8501`
- FastAPI Docs: `http://localhost:8000/docs`

## Design Decisions

- FastAPI was chosen for the backend because it provides clean API contracts, automatic Swagger docs, and good async file upload support.
- Streamlit was chosen for rapid demo development and recruiter-friendly presentation.
- LangGraph was chosen for structured, controllable multi-step agent workflows.
- FAISS was chosen for simple local vector retrieval over uploaded PDFs.
- Docker Compose was chosen for reproducible local deployment of frontend and backend together.

## Known Tradeoffs

- Uploaded documents are stored in memory and reset after backend/container restart.
- There is no authentication yet.
- Chat history is session-level in the frontend, not persisted in a database.
- yfinance market data can be delayed or temporarily unavailable.
- News retrieval quality depends on Tavily search relevance and available public web results.
