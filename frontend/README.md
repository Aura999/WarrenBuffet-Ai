# WarrenBuffet.Ai - Streamlit UI

A lightweight Streamlit frontend for the WarrenBuffet.Ai backend.

## Run

1. Start the backend:

   ```powershell
   cd backend
   .\.venv\Scripts\Activate.ps1
   uvicorn app.main:app --reload
   ```

2. Start the frontend:

   ```powershell
   cd frontend
   pip install -r requirements.txt
   streamlit run streamlit_app.py
   ```

3. Open:

   ```text
   http://localhost:8501
   ```

By default, the frontend calls `http://127.0.0.1:8000`. To override it, create a local `.env` in `frontend/`:

```env
BACKEND_URL=http://127.0.0.1:8000
```

PDF documents are stored in backend memory and disappear after backend restart.

## Voice Assistant

The Streamlit app includes a Voice Assistant tab.

1. Record audio directly in the browser or upload an audio question in `.mp3`, `.wav`, `.m4a`, `.webm`, or `.ogg` format.
2. Optionally enter a ticker in the sidebar and select uploaded documents.
3. Click `Analyze Voice Question`.
4. The app transcribes the audio, sends the transcript to `/api/chat`, renders the text answer, and can generate a spoken MP3 answer through `/api/voice/tts`.

Browser microphone recording is supported through `streamlit-mic-recorder`. If recording does not work because browser microphone permission is blocked, use the audio upload fallback.

Voice transcription uses the backend OpenAI transcription endpoint. Spoken answers use backend gTTS.

This tool provides research assistance only and is not financial advice.
