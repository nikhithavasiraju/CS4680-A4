# Safe AI Agent - CS4680 Assignment 4

## What this project does

The user enters a natural-language request. The LLM converts it into one JSON action. The program validates the JSON, executes only an allow-listed operation, displays the result, and records the request and result in `agent_audit.log`.

## Run locally

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env       # Windows
# cp .env.example .env       # macOS/Linux
streamlit run app.py
```

Put your Gemini API key in `.env` as `GEMINI_API_KEY`. Never commit `.env`.

## Rubric answers

### 1. Problem identification and relevance
Many chatbots only return text. This project solves the practical problem of turning a natural-language request into a controlled operation while reducing unsafe execution. It is useful for lightweight file and calculation tasks.

### 2. Application design and implementation
The system has four stages: user request, LLM action plan, validation, and execution. It supports listing files, reading files, creating new files, and basic arithmetic.

### 3. Prompt engineering
The system prompt uses role instructions, a closed list of allowed actions, JSON output requirements, argument schemas, and an explicit rejection action. Temperature is set to zero to improve consistency.

### 4. UI/UX design
The Streamlit interface has a text input, execution confirmation checkbox, interpreted JSON preview, success/error messages, and a visible audit-log location.

### 5. Error handling and safety
The application retries temporary LLM failures, handles rate limits, validates the JSON schema, blocks path traversal, prevents overwriting files, rejects unsupported requests, restricts arithmetic characters, requires confirmation, and logs errors/actions.

## Demo requests

1. `calculate 18*4`
2. `create notes.txt containing Study for the AI Agent exam`
3. `list my files`
4. `read notes.txt`
5. `delete all files` (demonstrates safe rejection)

## Deployment

Deploy `app.py`, `requirements.txt`, and `.streamlit/config.toml` to Streamlit Community Cloud. Add `GEMINI_API_KEY` under App Settings > Secrets, then copy the generated public URL into the Google Form.

## One-minute demo script

“This is my Safe AI Agent. The user types a natural-language request. I’ll ask it to calculate 18 times 4. The LLM returns a structured JSON action, the application validates the action against an allow-list, executes it, and displays the result. I’ll now create a file and list the workspace to show an action that changes state. Finally, I’ll request deletion of all files. The agent rejects it because destructive operations are not allowed. Every plan, execution, and error is written to the audit log.”
