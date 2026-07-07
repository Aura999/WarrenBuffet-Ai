# WarrenBuffet.Ai Demo Script

## 30-Second Pitch

WarrenBuffet.Ai is an AI-powered financial research copilot I designed and built. It combines market data, news sentiment, annual report RAG, and voice interaction to generate structured investor-style analysis. The system can answer casual questions, identify itself with a custom branded assistant layer, analyze companies using market data and news, reason over uploaded PDFs, and support voice-based research through transcription and spoken responses.

## 2-Minute Demo Flow

Step 1: Show Streamlit UI.

Open `http://localhost:8501` and point out the Research Chat, Voice Assistant, and Documents tabs.

Step 2: Ask casual:

```text
Hi bro, how are you?
```

Show that the assistant responds conversationally and does not generate a financial report.

Step 3: Ask:

```text
Who are you?
```

Show the WarrenBuffet.Ai identity response and mention that identity questions are routed away from the financial graph.

Step 4: Enter ticker `RELIANCE.NS`.

Ask:

```text
Analyze Reliance Industries using current market data.
```

Show the Market Snapshot and structured analysis.

Step 5: Upload annual report PDF.

Ask:

```text
Summarize the key risks from this annual report.
```

Show the document-grounded response and source metadata.

Step 6: Use voice.

Say:

```text
Analyze Reliance Industries using current market data.
```

Show transcription, answer, and optional audio response.

Step 7: Show Docker.

```powershell
docker compose up --build
```

Explain that the frontend and backend run together through Docker Compose.

## Technical Explanation For Interviewer

The frontend sends requests to FastAPI. FastAPI first routes each message through an intent classifier. Casual, identity, capability, planning, and voice-meta messages go to a branded conversation agent. Financial analysis and document questions enter a LangGraph pipeline.

The LangGraph pipeline gathers context from yfinance, Tavily, sentiment analysis, and document retrieval. PDF queries use PyMuPDF extraction, OpenAI embeddings, and FAISS similarity search. The synthesis agent combines the available context into a structured investor-style answer with source traceability.

Voice uses the same backend pipeline after transcription, which keeps text and voice behavior consistent.

## Strong Interview Talking Points

- Built modular multi-agent architecture
- Added intent router to avoid wrong tool use
- Integrated structured RAG over annual reports
- Added source traceability
- Dockerized full stack
- Designed for extensibility: persistence, auth, watchlist, ratios

## Questions Interviewers May Ask

Q: Why LangGraph?

A: For explicit stateful graph orchestration and controllable multi-step workflows.

Q: Why not only one LLM call?

A: Financial research requires routing, context gathering, retrieval, and synthesis. Modular nodes improve maintainability.

Q: Why FAISS?

A: Lightweight local vector search suitable for a PDF RAG prototype.

Q: What is the current limitation?

A: Document storage is in-memory; next step is persistent vector storage and a metadata database.

Q: Is this financial advice?

A: No, it is research assistance only.
