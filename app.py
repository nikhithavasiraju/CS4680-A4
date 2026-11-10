
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
                raise RuntimeError("Gemini returned invalid JSON.") from exc
            time.sleep(2 ** attempt)
        except Exception as exc:
            message = str(exc).lower()
            if "429" in message or "rate" in message or "quota" in message:
                if attempt == 2:
                    raise RuntimeError("Gemini rate limit or free-tier quota reached.") from exc
                time.sleep(2 ** attempt)
                continue
            if attempt == 2:
                raise RuntimeError(f"The Gemini request failed: {exc}") from exc
            time.sleep(2 ** attempt)


def validate_plan(plan: dict) -> None:
    allowed = {"list_files", "read_file", "write_file", "calculate", "reject"}
    if not isinstance(plan, dict) or plan.get("action") not in allowed:
        raise ValueError("The LLM returned an invalid action.")

    action = plan["action"]
    if action in {"read_file", "write_file"}:
        if not isinstance(plan.get("filename"), str) or not plan["filename"].strip():
            raise ValueError("A valid filename is required.")
        safe_path(plan["filename"])
    if action == "write_file" and not isinstance(plan.get("content"), str):
        raise ValueError("File content must be text.")
    if action == "calculate" and not isinstance(plan.get("expression"), str):
        raise ValueError("A calculation expression is required.")


def execute_plan(plan: dict) -> str:
    validate_plan(plan)
    action = plan["action"]

    if action == "reject":
        return f"Request rejected for safety: {plan.get('reason', 'unsupported request')}"
    if action == "list_files":
        files = [p.name for p in WORKSPACE.iterdir() if p.is_file()]
        return "Files: " + (", ".join(files) if files else "No files yet.")
    if action == "read_file":
        path = safe_path(plan["filename"])
        if not path.exists():
            return f"{plan['filename']} does not exist."
        return path.read_text(encoding="utf-8")
    if action == "write_file":
        path = safe_path(plan["filename"])
        if path.exists():
            raise PermissionError("Overwriting an existing file is disabled for safety.")
        path.write_text(plan["content"], encoding="utf-8")
        return f"Created {plan['filename']} in agent_workspace."
    if action == "calculate":
        # Deliberately allow only digits, spaces, decimal points, and arithmetic operators.
        expression = plan["expression"]
        if any(char not in "0123456789+-*/(). %" for char in expression):
            raise ValueError("Only basic arithmetic is allowed.")
        return f"{expression} = {eval(expression, {'__builtins__': {}}, {})}"
    raise ValueError("Unsupported action.")


st.set_page_config(page_title="Safe AI Agent", page_icon="🤖")
st.title("🤖 Safe AI Agent")
st.caption("Natural language request → validated action → execution result")

request = st.text_area(
    "What should the agent do?",
    placeholder="Examples: list my files, create notes.txt containing Meeting at 3 PM, or calculate 18*4",
)
confirm = st.checkbox("I understand that the agent will execute the interpreted action.")

if st.button("Run agent", type="primary"):
    if not request.strip():
        st.warning("Enter a request first.")
    elif not confirm:
        st.warning("Confirm execution before running the agent.")
    else:
        try:
            plan = get_plan(request)
            st.subheader("Interpreted action")
            st.json(plan)
            result = execute_plan(plan)
            logging.info("EXECUTION | result=%r", result)
            st.success("Execution completed")
            st.write(result)
        except Exception as exc:
            logging.exception("ERROR | request=%r", request)
            st.error(str(exc))

st.divider()
st.write("Audit log: `agent_audit.log` | Safe workspace: `agent_workspace/`")
