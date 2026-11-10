import json
import logging
import os
import time
from pathlib import Path

import streamlit as st
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

WORKSPACE = Path("agent_workspace")
WORKSPACE.mkdir(exist_ok=True)

logging.basicConfig(
    filename="agent_audit.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)


SYSTEM_PROMPT = """
You are an action-planning assistant. Convert the user's request into exactly one JSON object.
Allowed actions are:
1. list_files: {"action":"list_files"}
2. read_file: {"action":"read_file","filename":"name.txt"}
3. write_file: {"action":"write_file","filename":"name.txt","content":"text"}
4. calculate: {"action":"calculate","expression":"2+2"}
If the request is unsafe, destructive, or outside these actions, return:
{"action":"reject","reason":"brief explanation"}
Return JSON only. Never include markdown or additional text.
"""

ACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["list_files", "read_file", "write_file", "calculate", "reject"],
        },
        "filename": {"type": "string"},
        "content": {"type": "string"},
        "expression": {"type": "string"},
        "reason": {"type": "string"},
    },
    "required": ["action"],
}


def get_setting(name: str, default: str | None = None) -> str | None:
    """Read local .env values or Streamlit Community Cloud secrets."""
    value = os.getenv(name)
    if value:
        return value
    try:
        value = st.secrets.get(name)
        if value:
            return str(value)
    except Exception:
        pass
    return default

def safe_path(filename: str) -> Path:
    """Keep all file operations inside agent_workspace."""
    path = (WORKSPACE / filename).resolve()
    if WORKSPACE.resolve() not in path.parents:
        raise ValueError("File path must remain inside agent_workspace.")
    return path


def get_plan(user_request: str) -> dict:
    api_key = get_setting("GEMINI_API_KEY") or get_setting("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing. Add it to your .env file.")

    client = genai.Client(api_key=api_key)
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=get_setting("GEMINI_MODEL", "gemini-3.5-flash-lite"),
                contents=user_request,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0,
                    response_mime_type="application/json",
                    response_schema=ACTION_SCHEMA,
                ),
            )
            plan = json.loads(response.text)
            logging.info("PLAN | request=%r | plan=%s", user_request, plan)
            return plan
        except json.JSONDecodeError as exc:
            if attempt == 2:
