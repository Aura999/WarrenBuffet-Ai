import os
import site
import sys
from typing import Any
from urllib.parse import urlparse

user_site = site.getusersitepackages()
if user_site and user_site not in sys.path:
    sys.path.append(user_site)

import requests
import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

try:
    from streamlit_mic_recorder import mic_recorder
except ModuleNotFoundError:
    mic_recorder = None


load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")


st.set_page_config(
    page_title="WarrenBuffet.Ai",
    page_icon="WB",
    layout="wide",
)


def _api_url(path: str) -> str:
    return f"{BACKEND_URL}{path}"


def _response_json(response: requests.Response) -> dict:
    try:
        return response.json()
    except ValueError:
        return {
            "success": False,
            "error": response.text or "Invalid API response.",
        }


def check_backend_health() -> tuple[bool, str]:
    try:
        response = requests.get(_api_url("/api/health"), timeout=20)
        data = _response_json(response)

        if response.ok and data.get("status") == "ok":
            return True, "Backend is healthy."

        return False, data.get("detail") or data.get("error") or "Backend health check failed."
    except requests.RequestException:
        return (
            False,
            "Backend is not running. Start it with: uvicorn app.main:app --reload from backend/",
        )


def upload_documents(files) -> dict:
    multipart_files = []

    for file in files:
        multipart_files.append(
            (
                "files",
                (
                    file.name,
                    file.getvalue(),
                    "application/pdf",
                ),
            )
        )

    try:
        response = requests.post(
            _api_url("/api/documents/upload"),
            files=multipart_files,
            timeout=240,
        )
        return _response_json(response)
    except requests.RequestException as exc:
        return {
            "success": False,
            "error": str(exc) or "Document upload failed.",
            "documents": [],
        }


def get_documents() -> dict:
    try:
        response = requests.get(_api_url("/api/documents"), timeout=20)
        return _response_json(response)
    except requests.RequestException as exc:
        return {
            "success": False,
            "error": str(exc) or "Could not fetch documents.",
            "documents": [],
        }


def send_chat(
    query: str,
    ticker: str | None = None,
    document_ids: list[str] | None = None,
) -> dict:
    payload: dict[str, Any] = {"query": query}

    if ticker:
        payload["ticker"] = ticker

    if document_ids:
        payload["document_ids"] = document_ids

    try:
        response = requests.post(
            _api_url("/api/chat"),
            json=payload,
            timeout=240,
        )
        data = _response_json(response)

        if not response.ok:
            return {
                "success": False,
                "error": data.get("detail") or data.get("error") or "Chat request failed.",
            }

        return data
    except requests.Timeout:
        return {
            "success": False,
            "error": "The backend took too long to respond. Try again, or ask a narrower question.",
        }
    except requests.RequestException as exc:
        return {
            "success": False,
            "error": str(exc) or "Chat request failed.",
        }


def get_document_chunk(document_id: str, chunk_index: int) -> dict:
    try:
        response = requests.get(
            _api_url(f"/api/documents/{document_id}/chunks/{chunk_index}"),
            timeout=20,
        )
        return _response_json(response)
    except requests.RequestException as exc:
        return {
            "success": False,
            "error": str(exc) or "Could not fetch document source text.",
        }


def delete_document(document_id: str) -> dict:
    try:
        response = requests.delete(
            _api_url(f"/api/documents/{document_id}"),
            timeout=20,
        )
        return _response_json(response)
    except requests.RequestException as exc:
        return {
            "success": False,
            "error": str(exc) or "Could not delete document.",
        }


def transcribe_audio_bytes(audio_bytes: bytes, filename: str, mime_type: str) -> dict:
    try:
        files = {
            "file": (
                filename,
                audio_bytes,
                mime_type,
            )
        }
        response = requests.post(
            _api_url("/api/voice/transcribe"),
            files=files,
            timeout=120,
        )
        data = _response_json(response)

        if not response.ok:
            return {
                "success": False,
                "error": data.get("detail") or data.get("error") or "Transcription failed.",
            }

        return data
    except requests.RequestException as exc:
        return {
            "success": False,
            "error": str(exc) or "Transcription failed.",
        }


def transcribe_audio(audio_file) -> dict:
    return transcribe_audio_bytes(
        audio_bytes=audio_file.getvalue(),
        filename=audio_file.name,
        mime_type="application/octet-stream",
    )


def _recorded_audio_payload(audio: Any) -> tuple[bytes, str, str] | None:
    if not audio:
        return None

    audio_bytes = audio.get("bytes") if isinstance(audio, dict) else None

    if not audio_bytes:
        return None

    mime_type = (
        audio.get("mime_type")
        or audio.get("mimeType")
        or audio.get("type")
        or "audio/wav"
    )
    audio_format = (audio.get("format") or "").lower()

    if "webm" in mime_type or audio_format == "webm":
        filename = "recorded_question.webm"
        mime_type = "audio/webm"
    elif "ogg" in mime_type or audio_format == "ogg":
        filename = "recorded_question.ogg"
        mime_type = "audio/ogg"
    elif "mpeg" in mime_type or "mp3" in mime_type or audio_format == "mp3":
        filename = "recorded_question.mp3"
        mime_type = "audio/mpeg"
    else:
        filename = "recorded_question.wav"
        mime_type = "audio/wav"

    return audio_bytes, filename, mime_type


def generate_tts_audio(text: str) -> dict:
    try:
        response = requests.post(
            _api_url("/api/voice/tts"),
            json={"text": text},
            timeout=120,
        )

        if not response.ok:
            data = _response_json(response)
            return {
                "success": False,
                "error": data.get("detail") or data.get("error") or "Audio generation failed.",
            }

        return {
            "success": True,
            "audio": response.content,
        }
    except requests.RequestException as exc:
        return {
            "success": False,
            "error": str(exc) or "Audio generation failed.",
        }


def init_session_state() -> None:
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("uploaded_documents", [])
    st.session_state.setdefault("selected_document_ids", [])
    st.session_state.setdefault("ticker_input", "")


def sync_documents_from_backend(show_errors: bool = False) -> None:
    data = get_documents()

    if data.get("success"):
        st.session_state.uploaded_documents = data.get("documents", [])
        available_ids = {
            document.get("document_id")
            for document in st.session_state.uploaded_documents
        }
        st.session_state.selected_document_ids = [
            document_id
            for document_id in st.session_state.selected_document_ids
            if document_id in available_ids
        ]
    elif show_errors:
        st.error(data.get("error") or "Could not refresh documents.")


def is_document_related(query: str) -> bool:
    terms = (
        "pdf",
        "document",
        "report",
        "annual report",
        "uploaded",
        "from this",
        "based on this",
        "summarize this",
        "management commentary",
        "risks mentioned",
        "extract from",
    )
    normalized = query.lower()
    return any(term in normalized for term in terms)


def _currency_symbol(currency: str | None) -> str:
    symbols = {
        "INR": "₹",
        "USD": "$",
        "EUR": "€",
        "GBP": "£",
        "JPY": "¥",
    }
    return symbols.get((currency or "").upper(), currency or "")


def _format_price(value: Any, currency: str | None = None) -> str:
    if value is None:
        return "N/A"

    try:
        symbol = _currency_symbol(currency)
        return f"{symbol}{float(value):,.2f}" if symbol else f"{float(value):,.2f}"
    except (TypeError, ValueError):
        return str(value)


def _format_compact_number(value: Any) -> str:
    if value is None:
        return "N/A"

    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)

    abs_number = abs(number)

    if abs_number >= 10_000_000_000_000:
        return f"{number / 10_000_000_000_000:.2f} Lakh Cr"

    if abs_number >= 10_000_000:
        return f"{number / 10_000_000:.2f} Cr"

    if abs_number >= 100_000:
        return f"{number / 100_000:.2f} L"

    if abs_number >= 1_000:
        return f"{number / 1_000:.2f}K"

    return f"{number:,.0f}"


def _format_percent(value: Any) -> str:
    if value is None:
        return "N/A"

    try:
        return f"{float(value):+.2f}%"
    except (TypeError, ValueError):
        return str(value)


def render_market_snapshot_cards(snapshot: dict[str, Any]) -> None:
    if not snapshot:
        return

    currency = snapshot.get("currency")
    current_price = snapshot.get("current_price")
    day_change_pct = snapshot.get("day_change_pct")
    day_change = snapshot.get("day_change")

    st.subheader("Market Snapshot")

    company_name = snapshot.get("company_name")
    ticker = snapshot.get("ticker")
    exchange = snapshot.get("exchange")

    if company_name or ticker:
        st.caption(
            " | ".join(
                value
                for value in (company_name, ticker, exchange, "Data source: yfinance")
                if value
            )
        )

    col1, col2, col3 = st.columns(3)
    col4, col5, col6 = st.columns(3)

    with col1:
        st.metric(
            "Current Price",
            _format_price(current_price, currency),
            delta=_format_percent(day_change_pct) if day_change_pct is not None else None,
        )

    with col2:
        st.metric(
            "Day Change %",
            _format_percent(day_change_pct),
            delta=_format_price(day_change, currency) if day_change is not None else None,
        )

    with col3:
        st.metric("Market Cap", _format_compact_number(snapshot.get("market_cap")))

    with col4:
        st.metric("Volume", _format_compact_number(snapshot.get("volume")))

    with col5:
        st.metric("52W High", _format_price(snapshot.get("fifty_two_week_high"), currency))

    with col6:
        st.metric("52W Low", _format_price(snapshot.get("fifty_two_week_low"), currency))


def render_price_history_chart(price_history: list[dict[str, Any]], ticker: str | None = None) -> None:
    if not price_history:
        return

    try:
        price_df = pd.DataFrame(price_history)

        if price_df.empty or "date" not in price_df.columns or "close" not in price_df.columns:
            return

        price_df["date"] = pd.to_datetime(price_df["date"], errors="coerce")
        price_df = price_df.dropna(subset=["date", "close"])

        if price_df.empty:
            return

        st.subheader("Price History")
        chart_title = f"{ticker or 'Ticker'} Closing Price - 1Y"
        hover_columns = [
            column
            for column in ("open", "high", "low", "close", "volume")
            if column in price_df.columns
        ]
        fig = px.line(
            price_df,
            x="date",
            y="close",
            title=chart_title,
            hover_data=hover_columns,
        )
        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="Close",
            hovermode="x unified",
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception:
        return


def render_visuals(visuals: dict[str, Any] | None) -> None:
    if not visuals:
        return

    market_snapshot = visuals.get("market_snapshot") or {}
    price_history = visuals.get("price_history") or []
    ticker = market_snapshot.get("ticker")

    if market_snapshot:
        render_market_snapshot_cards(market_snapshot)

    if price_history:
        render_price_history_chart(price_history, ticker)


def render_sources(sources: list[Any], message_index: int) -> None:
    if not sources:
        return

    with st.expander("Sources"):
        for source_index, source in enumerate(sources):
            if isinstance(source, str):
                if source == "yfinance":
                    st.markdown("- Market data: yfinance")
                elif source.startswith("http"):
                    domain = urlparse(source).netloc.replace("www.", "")
                    st.markdown(f"- News: [{domain or 'News source'}]({source})")
                else:
                    st.markdown(f"- {source}")
                continue

            if isinstance(source, dict) and source.get("type") == "news":
                url = source.get("url") or ""
                title = source.get("title")
                domain = urlparse(url).netloc.replace("www.", "") if url else ""
                label = title or domain or "News source"

                if url:
                    st.markdown(f"- News: [{label}]({url})")
                else:
                    st.markdown(f"- News: {label}")

                if domain and title:
                    st.caption(domain)

                continue

            if isinstance(source, dict) and source.get("type") == "document":
                filename = source.get("filename") or "document"
                page_number = source.get("page_number")
                chunk_index = source.get("chunk_index")
                document_id = source.get("document_id")
                short_id = (document_id or "")[:12]

                st.markdown(
                    f"- Document: `{filename}` | page `{page_number}` | "
                    f"chunk `{chunk_index}` | id `{short_id}`"
                )

                button_key = f"source_{message_index}_{source_index}_{document_id}_{chunk_index}"
                show_key = f"show_{button_key}"

                if st.button("View source text", key=button_key):
                    st.session_state[show_key] = True

                if st.session_state.get(show_key):
                    chunk = get_document_chunk(document_id, int(chunk_index))

                    with st.expander(
                        f"Source text - {filename} page {page_number} chunk {chunk_index}",
                        expanded=True,
                    ):
                        if chunk.get("success"):
                            st.write(chunk.get("text") or "")
                        else:
                            st.error(chunk.get("error") or chunk.get("detail") or "Could not load source text.")


def render_chat_history() -> None:
    for index, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                render_visuals(message.get("visuals"))
                st.markdown(message["content"])
                render_sources(message.get("sources", []), index)
            else:
                st.markdown(message["content"])


def render_sidebar() -> str:
    with st.sidebar:
        st.header("Controls")
        st.caption(f"Backend: `{BACKEND_URL}`")

        if st.button("Check Backend", use_container_width=True):
            healthy, message = check_backend_health()

            if healthy:
                st.success(message)
            else:
                st.error(message)

        ticker = st.text_input(
            "Ticker Symbol",
            value=st.session_state.ticker_input,
            placeholder="RELIANCE.NS, INFY.NS, TCS.NS, HDFCBANK.NS, ETERNAL.NS, AAPL",
        )
        st.session_state.ticker_input = ticker.strip()

        st.divider()
        st.subheader("PDF Upload")
        uploaded_files = st.file_uploader(
            "Upload financial PDFs",
            type=["pdf"],
            accept_multiple_files=True,
        )

        if st.button("Upload & Index PDFs", use_container_width=True):
            if not uploaded_files:
                st.warning("Choose one or more PDF files first.")
            else:
                with st.spinner("Uploading, extracting, embedding, and indexing PDFs..."):
                    result = upload_documents(uploaded_files)

                for document in result.get("documents", []):
                    if document.get("status") == "indexed":
                        st.success(f"Uploaded and indexed: {document.get('filename')}")
                    else:
                        st.error(
                            f"{document.get('filename')}: "
                            f"{document.get('error') or 'Upload failed.'}"
                        )

                sync_documents_from_backend(show_errors=True)

        st.divider()
        st.subheader("Uploaded Documents")

        if st.button("Refresh Documents", use_container_width=True, key="sidebar_refresh_docs"):
            sync_documents_from_backend(show_errors=True)

        documents = st.session_state.uploaded_documents

        if not documents:
            st.info("No uploaded documents found.")
        else:
            options = {
                f"{doc.get('filename')} | p{doc.get('page_count')} | chunks {doc.get('chunk_count')} | {doc.get('document_id', '')[:10]}": doc.get("document_id")
                for doc in documents
            }
            selected_labels = [
                label
                for label, document_id in options.items()
                if document_id in st.session_state.selected_document_ids
            ]
            selected_labels = st.multiselect(
                "Use documents in chat",
                options=list(options.keys()),
                default=selected_labels,
            )
            st.session_state.selected_document_ids = [
                options[label]
                for label in selected_labels
            ]

            for doc in documents:
                st.caption(
                    f"{doc.get('filename')} | pages: {doc.get('page_count')} | "
                    f"chunks: {doc.get('chunk_count')} | id: {doc.get('document_id', '')[:12]}"
                )

        st.divider()

        if st.button("Clear Session", use_container_width=True):
            st.session_state.messages = []
            st.session_state.selected_document_ids = []
            st.rerun()

    return st.session_state.ticker_input


def render_research_chat(ticker: str) -> None:
    st.subheader("Research Chat")

    with st.expander("Example prompts"):
        st.markdown(
            """
- Analyze Reliance Industries using current market data and latest news
- What are the key risks for Zomato?
- Summarize this annual report
- Create an investor brief using this document, market data, and news
- Compare the bull and bear case from this report
"""
        )

    render_chat_history()

    user_input = st.chat_input("Ask about a company, market, news, or uploaded PDF...")

    if not user_input:
        return

    selected_document_ids = st.session_state.selected_document_ids

    if is_document_related(user_input) and not selected_document_ids:
        st.warning("No document selected. Upload/select a PDF for document-grounded answers.")

    st.session_state.messages.append(
        {
            "role": "user",
            "content": user_input,
            "sources": [],
        }
    )

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Analyzing document and generating response. Large PDFs may take 1-3 minutes."):
            result = send_chat(
                query=user_input,
                ticker=ticker or None,
                document_ids=selected_document_ids,
            )

        if result.get("success"):
            answer = result.get("answer") or ""
            sources = result.get("sources") or []
            visuals = result.get("visuals")
            render_visuals(visuals)
            st.markdown(answer)
            render_sources(sources, len(st.session_state.messages))
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": answer,
                    "sources": sources,
                    "visuals": visuals,
                }
            )
        else:
            error = result.get("error") or result.get("detail") or "Chat request failed."
            st.error(error)
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": f"Error: {error}",
                    "sources": [],
                }
            )


def render_voice_assistant(ticker: str) -> None:
    st.subheader("Voice Assistant")
    st.info(
        "Upload or record an audio question. The assistant will transcribe it "
        "and run the same financial research pipeline."
    )

    input_mode = st.radio(
        "Voice input mode",
        options=["Record in browser", "Upload audio file"],
        index=0,
        horizontal=True,
    )
    audio_payload = None

    if input_mode == "Record in browser":
        if mic_recorder is None:
            st.warning(
                "Microphone recorder package is not installed. Run "
                "`pip install -r requirements.txt` or use audio upload."
            )
        else:
            recorded_audio = mic_recorder(
                start_prompt="🎙️ Start recording",
                stop_prompt="⏹️ Stop recording",
                just_once=False,
                use_container_width=True,
                key="voice_recorder",
            )
            audio_payload = _recorded_audio_payload(recorded_audio)

            if recorded_audio is None:
                st.caption("If recording does not start, allow microphone permission or use audio upload.")
            elif audio_payload is None:
                st.warning("Microphone access was blocked. Allow microphone permission or use audio upload.")
    else:
        audio_file = st.file_uploader(
            "Upload an audio question",
            type=["mp3", "wav", "m4a", "webm", "ogg"],
            accept_multiple_files=False,
            key="voice_audio_upload",
        )

        if audio_file:
            audio_payload = (
                audio_file.getvalue(),
                audio_file.name,
                "application/octet-stream",
            )

    generate_audio = st.checkbox("Generate spoken answer", value=True)

    if st.button("Analyze Voice Question", type="primary"):
        if not audio_payload:
            st.warning("Please record or upload an audio question first.")
            return

        with st.spinner("Transcribing audio question..."):
            transcription = transcribe_audio_bytes(*audio_payload)

        if not transcription.get("success"):
            st.error(transcription.get("error") or "Transcription failed.")
            return

        transcript = (transcription.get("transcript") or "").strip()

        if not transcript:
            st.warning("Could not detect speech. Try a clearer audio file.")
            return

        st.info("Transcript detected:")
        st.markdown(f"> {transcript}")

        selected_document_ids = st.session_state.selected_document_ids

        if is_document_related(transcript) and not selected_document_ids:
            st.warning("No document selected. Upload/select a PDF for document-grounded answers.")

        with st.spinner("Analyzing document and generating response. Large PDFs may take 1-3 minutes."):
            result = send_chat(
                query=transcript,
                ticker=ticker or None,
                document_ids=selected_document_ids,
            )

        if not result.get("success"):
            st.error(result.get("error") or result.get("detail") or "Chat request failed.")
            return

        answer = result.get("answer") or ""
        sources = result.get("sources") or []
        visuals = result.get("visuals")

        render_visuals(visuals)
        st.markdown(answer)
        render_sources(sources, len(st.session_state.messages) + 1000)

        st.session_state.messages.append(
            {
                "role": "user",
                "content": f"Voice: {transcript}",
                "sources": [],
            }
        )
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": answer,
                "sources": sources,
                "visuals": visuals,
            }
        )

        if generate_audio:
            with st.spinner("Generating spoken answer..."):
                audio = generate_tts_audio(answer)

            if audio.get("success"):
                st.audio(audio["audio"], format="audio/mp3")
                st.caption("Audio summary generated from the first part of the answer if the response was long.")
            else:
                st.warning("Audio generation failed, but text answer is available.")
                st.caption(audio.get("error") or "")

    st.caption("Voice output is for convenience only. This is research assistance, not financial advice.")


def render_documents_tab() -> None:
    st.subheader("Documents")

    if st.button("Refresh Documents", key="main_refresh_docs"):
        sync_documents_from_backend(show_errors=True)

    documents = st.session_state.uploaded_documents

    if not documents:
        st.info("No documents indexed in the backend.")
        return

    for document in documents:
        with st.expander(document.get("filename") or "Document"):
            st.markdown(f"**Document ID:** `{document.get('document_id')}`")
            st.markdown(f"**Page count:** {document.get('page_count')}")
            st.markdown(f"**Character count:** {document.get('character_count')}")
            st.markdown(f"**Chunk count:** {document.get('chunk_count')}")
            st.markdown(f"**Status:** {document.get('status', 'indexed')}")

            document_id = document.get("document_id")

            if st.button("Delete Document", key=f"delete_{document_id}"):
                result = delete_document(document_id)

                if result.get("success"):
                    st.success("Document deleted.")
                    sync_documents_from_backend(show_errors=True)
                    st.rerun()
                else:
                    st.error(result.get("error") or result.get("detail") or "Delete failed.")


def main() -> None:
    init_session_state()
    sync_documents_from_backend(show_errors=False)

    st.title("WarrenBuffet.Ai")
    st.caption("AI-powered financial research copilot designed and built by Satyam Mishra")
    st.caption("Market data + news sentiment + annual report RAG + voice interface")

    ticker = render_sidebar()

    tab_chat, tab_voice, tab_documents = st.tabs(
        ["Research Chat", "Voice Assistant", "Documents"]
    )

    with tab_chat:
        render_research_chat(ticker)

    with tab_voice:
        render_voice_assistant(ticker)

    with tab_documents:
        render_documents_tab()

    st.divider()
    st.caption("This tool provides research assistance only and is not financial advice.")


if __name__ == "__main__":
    main()
