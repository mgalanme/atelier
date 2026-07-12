"""
ATELIER conversational demo: Streamlit front end over the SAM WebUI gateway.

This app is a thin HTTP/SSE client. All orchestration and reasoning logic
lives in the SAM mesh (OrchestratorAgent and its four peer agents); this
file only submits the user's message via message:stream, then opens a
real SSE connection to the gateway's task event stream and renders events
as they arrive.

Environment variables required:
    SAM_GATEWAY_URL   Base URL of the SAM WebUI gateway (e.g.
                       "http://localhost:8000" locally, or the public URL
                       of the deployed container in production).
"""

import json
import os
import re
import uuid

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

SAM_GATEWAY_URL = os.environ.get("SAM_GATEWAY_URL", "http://localhost:8000")
AGENT_NAME = "OrchestratorAgent"
EMBED_PATTERN = re.compile(r"\u00ab[^\u00bb]*\u00bb")

st.set_page_config(page_title="ATELIER", layout="centered")
st.title("ATELIER")
st.caption("Conversational AI platform for the fashion industry")

if "context_id" not in st.session_state:
    st.session_state.context_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []


def submit_message(text: str, context_id: str | None) -> str:
    """
    Submits a message to the SAM WebUI gateway via message:stream. This
    marks the task as streaming-enabled server-side (is_streaming=True),
    which is required for the gateway to correctly track and forward
    sub-task events. Returns the task_id.
    """
    payload = {
        "id": f"req-{uuid.uuid4()}",
        "jsonrpc": "2.0",
        "method": "message/stream",
        "params": {
            "message": {
                "role": "user",
                "messageId": f"msg-{uuid.uuid4()}",
                "metadata": {"agent_name": AGENT_NAME},
                "parts": [{"kind": "text", "text": text}],
            }
        },
    }
    if context_id:
        payload["params"]["message"]["contextId"] = context_id

    response = requests.post(
        f"{SAM_GATEWAY_URL}/api/v1/message:stream", json=payload, timeout=30
    )
    response.raise_for_status()
    data = response.json()
    return data["result"]["id"]


def extract_progress_text(event_data: dict) -> str | None:
    """
    Extracts a human-readable progress message from a status_update event,
    where the gateway has already resolved a status_update embed into an
    agent_progress_update data part.
    """
    result = event_data.get("result", {})
    status = result.get("status", {})
    message = status.get("message", {})
    for part in message.get("parts", []):
        if part.get("kind") == "data":
            data = part.get("data", {})
            if data.get("type") == "agent_progress_update":
                return data.get("status_text")
    return None


def extract_llm_text(event_data: dict) -> str | None:
    """
    Extracts visible model-generated text from an llm_response data part
    inside a status_update event, stripping any embed directives.
    """
    result = event_data.get("result", {})
    status = result.get("status", {})
    message = status.get("message", {})
    for part in message.get("parts", []):
        if part.get("kind") == "data":
            data = part.get("data", {})
            if data.get("type") == "llm_response":
                content = data.get("data", {}).get("content", {})
                chunks = []
                for content_part in content.get("parts", []):
                    text = content_part.get("text", "")
                    cleaned = EMBED_PATTERN.sub("", text).strip()
                    if cleaned:
                        chunks.append(cleaned)
                if chunks:
                    return "\n\n".join(chunks)
    return None


def extract_context_id(event_data: dict) -> str | None:
    return event_data.get("result", {}).get("contextId")


def stream_task_events(task_id: str, timeout: float = 180.0):
    """
    Opens a real SSE connection to the gateway's task event stream and
    yields (event_name, event_data) tuples as they arrive. Uses
    reconnect=true so that any events emitted before this connection was
    opened are replayed first.
    """
    url = f"{SAM_GATEWAY_URL}/api/v1/sse/subscribe/{task_id}"
    with requests.get(
        url, params={"reconnect": "true"}, stream=True, timeout=timeout
    ) as response:
        response.raise_for_status()
        event_name = None
        for raw_line in response.iter_lines(decode_unicode=True):
            if raw_line is None or raw_line == "":
                event_name = None
                continue
            if raw_line.startswith(":"):
                continue
            if raw_line.startswith("event:"):
                event_name = raw_line.split(":", 1)[1].strip()
            elif raw_line.startswith("data:"):
                data_raw = raw_line.split(":", 1)[1].strip()
                try:
                    data = json.loads(data_raw)
                except json.JSONDecodeError:
                    continue
                yield event_name, data
                if event_name == "final_response":
                    return


for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_input = st.chat_input("Ask ATELIER about trends, sustainability, buying, or storytelling...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        status_placeholder = st.empty()
        answer_placeholder = st.empty()
        latest_text = ""

        try:
            status_placeholder.info("Sending request to the ATELIER mesh...")
            task_id = submit_message(user_input, st.session_state.context_id)

            for event_name, event_data in stream_task_events(task_id):
                context_id = extract_context_id(event_data)
                if context_id:
                    st.session_state.context_id = context_id

                progress = extract_progress_text(event_data)
                if progress:
                    status_placeholder.info(progress)

                # Each llm_response event represents one full model turn.
                # The orchestrator may reason across several turns before
                # delegating and again after receiving peer responses; only
                # the LAST turn contains the true final synthesis. Earlier
                # turns are intermediate reasoning and are intentionally
                # discarded here, not accumulated.
                llm_text = extract_llm_text(event_data)
                if llm_text:
                    latest_text = llm_text

            status_placeholder.empty()
            final_text = latest_text
            if not final_text:
                final_text = (
                    "The orchestrator completed the task but returned no "
                    "visible text. It may have produced an artifact instead, "
                    "which this simple client does not yet display."
                )
            answer_placeholder.markdown(final_text)

        except requests.exceptions.RequestException as exc:
            status_placeholder.empty()
            final_text = f"Connection error talking to the ATELIER mesh: {exc}"
            answer_placeholder.error(final_text)

    st.session_state.messages.append({"role": "assistant", "content": final_text})

with st.sidebar:
    st.subheader("About ATELIER")
    st.markdown(
        "ATELIER coordinates four specialist AI agents over Solace Agent "
        "Mesh: **TrendAgent**, **SustainabilityAgent**, **BuyerAgent**, and "
        "**StorytellingAgent**. The OrchestratorAgent routes your request "
        "to the right specialist, or coordinates several in sequence."
    )
    if st.session_state.context_id:
        st.caption(f"Session: {st.session_state.context_id[:20]}...")
    if st.button("New conversation"):
        st.session_state.context_id = None
        st.session_state.messages = []
        st.rerun()
