# Session Provider Host Wrapper Snippets

These snippets are host-facing starting points for `provider=session`. They keep the engine as the owner of request creation, response validation, rendering, ledger writes, archive, and reconcile behavior.

Each snippet:

1. runs phase 1 with `provider-request`
2. extracts `request_path` and `expected_response_path` from the flat JSON summary
3. fills `REQUEST_PATH`, `RESPONSE_PATH`, `HOST_NAME`, and `MODEL_ID`
4. renders the generic extraction prompt from `docs/session-provider-subagent-prompt.md`
5. leaves exactly one host-specific step: run a dedicated extraction sub-agent with that rendered prompt
6. runs phase 2 with `ingest --provider session --provider-response`

Run snippets from the project root after enabling:

```toml
[privacy]
allow_session_provider = true
```

## Shared Helper

The snippets below use this shell helper shape. Keep it inline in wrappers so the source path, request path, response path, host, and model are visible in logs.

```bash
SOURCE="${1:?usage: wrapper SOURCE}"
QUALITY="${QUALITY:-balanced}"

PROJECT_SUMMARY="$(python3 -m meeting_ingest.cli status --root "$SOURCE" --json)"
MEETINGS_ROOT="$(printf '%s' "$PROJECT_SUMMARY" | python3 -c 'import json,sys; print(json.load(sys.stdin)["project"]["meetings_root"])')"

REQUEST_SUMMARY="$(python3 -m meeting_ingest.cli provider-request "$SOURCE" --provider session --quality "$QUALITY" --json)"

REQUEST_RELATIVE_PATH="$(printf '%s' "$REQUEST_SUMMARY" | python3 -c 'import json,sys; print(json.load(sys.stdin)["request_path"])')"
RESPONSE_RELATIVE_PATH="$(printf '%s' "$REQUEST_SUMMARY" | python3 -c 'import json,sys; print(json.load(sys.stdin)["expected_response_path"])')"
REQUEST_PATH="$(python3 -c 'from pathlib import Path; import sys; print(Path(sys.argv[1], sys.argv[2]))' "$MEETINGS_ROOT" "$REQUEST_RELATIVE_PATH")"
RESPONSE_PATH="$(python3 -c 'from pathlib import Path; import sys; print(Path(sys.argv[1], sys.argv[2]))' "$MEETINGS_ROOT" "$RESPONSE_RELATIVE_PATH")"

PROMPT_PATH="$(mktemp -t meeting-ingest-session-provider.XXXXXX.txt)"
python3 - "$REQUEST_PATH" "$RESPONSE_PATH" "$HOST_NAME" "$MODEL_ID" > "$PROMPT_PATH" <<'PY'
from pathlib import Path
import sys

request_path, response_path, host_name, model_id = sys.argv[1:]
template = Path("docs/session-provider-subagent-prompt.md").read_text()
prompt = template.split("```text", 1)[1].split("```", 1)[0].strip()
prompt = prompt.replace("REQUEST_PATH", request_path)
prompt = prompt.replace("RESPONSE_PATH", response_path)
prompt = prompt.replace("HOST_NAME", host_name)
prompt = prompt.replace("MODEL_ID", model_id)
print(prompt)
PY
```

After the host-specific sub-agent step writes `"$RESPONSE_PATH"`, every wrapper should complete with:

```bash
python3 -m meeting_ingest.cli ingest "$SOURCE" --provider session --provider-response "$RESPONSE_PATH" --json
```

`provider-request` returns handoff paths relative to `meetings_root`. The snippets pass absolute paths to the sub-agent so its plain file reads and writes resolve correctly from any project working directory.

## Claude Code

Use `claude-code` for provider provenance. If Claude Code exposes the active model through your shell environment, pass it through as `MODEL_ID`; otherwise use the session fallback.

```bash
#!/usr/bin/env bash
set -euo pipefail

HOST_NAME="claude-code"
MODEL_ID="${CLAUDE_CODE_MODEL:-claude-code-session}"

SOURCE="${1:?usage: claude-code-session-ingest SOURCE}"
QUALITY="${QUALITY:-balanced}"

PROJECT_SUMMARY="$(python3 -m meeting_ingest.cli status --root "$SOURCE" --json)"
MEETINGS_ROOT="$(printf '%s' "$PROJECT_SUMMARY" | python3 -c 'import json,sys; print(json.load(sys.stdin)["project"]["meetings_root"])')"

REQUEST_SUMMARY="$(python3 -m meeting_ingest.cli provider-request "$SOURCE" --provider session --quality "$QUALITY" --json)"
REQUEST_RELATIVE_PATH="$(printf '%s' "$REQUEST_SUMMARY" | python3 -c 'import json,sys; print(json.load(sys.stdin)["request_path"])')"
RESPONSE_RELATIVE_PATH="$(printf '%s' "$REQUEST_SUMMARY" | python3 -c 'import json,sys; print(json.load(sys.stdin)["expected_response_path"])')"
REQUEST_PATH="$(python3 -c 'from pathlib import Path; import sys; print(Path(sys.argv[1], sys.argv[2]))' "$MEETINGS_ROOT" "$REQUEST_RELATIVE_PATH")"
RESPONSE_PATH="$(python3 -c 'from pathlib import Path; import sys; print(Path(sys.argv[1], sys.argv[2]))' "$MEETINGS_ROOT" "$RESPONSE_RELATIVE_PATH")"

PROMPT_PATH="$(mktemp -t meeting-ingest-claude-code.XXXXXX.txt)"
python3 - "$REQUEST_PATH" "$RESPONSE_PATH" "$HOST_NAME" "$MODEL_ID" > "$PROMPT_PATH" <<'PY'
from pathlib import Path
import sys

request_path, response_path, host_name, model_id = sys.argv[1:]
template = Path("docs/session-provider-subagent-prompt.md").read_text()
prompt = template.split("```text", 1)[1].split("```", 1)[0].strip()
prompt = prompt.replace("REQUEST_PATH", request_path)
prompt = prompt.replace("RESPONSE_PATH", response_path)
prompt = prompt.replace("HOST_NAME", host_name)
prompt = prompt.replace("MODEL_ID", model_id)
print(prompt)
PY

printf 'Run a dedicated Claude Code extraction sub-agent with this prompt:\n%s\n' "$PROMPT_PATH"
printf 'After it writes %s, run:\n' "$RESPONSE_PATH"
printf 'python3 -m meeting_ingest.cli ingest %q --provider session --provider-response %q --json\n' "$SOURCE" "$RESPONSE_PATH"
```

## Supa Code

Use `supa-code` for provider provenance. Supa Code wrappers should run the extraction in a focused sub-agent or task surface, not in the same wrapper process that completes phase 2.

```bash
#!/usr/bin/env bash
set -euo pipefail

HOST_NAME="supa-code"
MODEL_ID="${SUPA_CODE_MODEL:-supa-code-session}"

SOURCE="${1:?usage: supa-code-session-ingest SOURCE}"
QUALITY="${QUALITY:-balanced}"

PROJECT_SUMMARY="$(python3 -m meeting_ingest.cli status --root "$SOURCE" --json)"
MEETINGS_ROOT="$(printf '%s' "$PROJECT_SUMMARY" | python3 -c 'import json,sys; print(json.load(sys.stdin)["project"]["meetings_root"])')"

REQUEST_SUMMARY="$(python3 -m meeting_ingest.cli provider-request "$SOURCE" --provider session --quality "$QUALITY" --json)"
REQUEST_RELATIVE_PATH="$(printf '%s' "$REQUEST_SUMMARY" | python3 -c 'import json,sys; print(json.load(sys.stdin)["request_path"])')"
RESPONSE_RELATIVE_PATH="$(printf '%s' "$REQUEST_SUMMARY" | python3 -c 'import json,sys; print(json.load(sys.stdin)["expected_response_path"])')"
REQUEST_PATH="$(python3 -c 'from pathlib import Path; import sys; print(Path(sys.argv[1], sys.argv[2]))' "$MEETINGS_ROOT" "$REQUEST_RELATIVE_PATH")"
RESPONSE_PATH="$(python3 -c 'from pathlib import Path; import sys; print(Path(sys.argv[1], sys.argv[2]))' "$MEETINGS_ROOT" "$RESPONSE_RELATIVE_PATH")"

PROMPT_PATH="$(mktemp -t meeting-ingest-supa-code.XXXXXX.txt)"
python3 - "$REQUEST_PATH" "$RESPONSE_PATH" "$HOST_NAME" "$MODEL_ID" > "$PROMPT_PATH" <<'PY'
from pathlib import Path
import sys

request_path, response_path, host_name, model_id = sys.argv[1:]
template = Path("docs/session-provider-subagent-prompt.md").read_text()
prompt = template.split("```text", 1)[1].split("```", 1)[0].strip()
prompt = prompt.replace("REQUEST_PATH", request_path)
prompt = prompt.replace("RESPONSE_PATH", response_path)
prompt = prompt.replace("HOST_NAME", host_name)
prompt = prompt.replace("MODEL_ID", model_id)
print(prompt)
PY

printf 'Run a dedicated Supa Code extraction sub-agent with this prompt:\n%s\n' "$PROMPT_PATH"
printf 'After it writes %s, run:\n' "$RESPONSE_PATH"
printf 'python3 -m meeting_ingest.cli ingest %q --provider session --provider-response %q --json\n' "$SOURCE" "$RESPONSE_PATH"
```

## T3 Code

Use `t3-code` for provider provenance. T3 Code is treated as its own host even when it routes through another model harness, because `provider.host` should identify the workflow that generated the response.

```bash
#!/usr/bin/env bash
set -euo pipefail

HOST_NAME="t3-code"
MODEL_ID="${T3_CODE_MODEL:-t3-code-session}"

SOURCE="${1:?usage: t3-code-session-ingest SOURCE}"
QUALITY="${QUALITY:-balanced}"

PROJECT_SUMMARY="$(python3 -m meeting_ingest.cli status --root "$SOURCE" --json)"
MEETINGS_ROOT="$(printf '%s' "$PROJECT_SUMMARY" | python3 -c 'import json,sys; print(json.load(sys.stdin)["project"]["meetings_root"])')"

REQUEST_SUMMARY="$(python3 -m meeting_ingest.cli provider-request "$SOURCE" --provider session --quality "$QUALITY" --json)"
REQUEST_RELATIVE_PATH="$(printf '%s' "$REQUEST_SUMMARY" | python3 -c 'import json,sys; print(json.load(sys.stdin)["request_path"])')"
RESPONSE_RELATIVE_PATH="$(printf '%s' "$REQUEST_SUMMARY" | python3 -c 'import json,sys; print(json.load(sys.stdin)["expected_response_path"])')"
REQUEST_PATH="$(python3 -c 'from pathlib import Path; import sys; print(Path(sys.argv[1], sys.argv[2]))' "$MEETINGS_ROOT" "$REQUEST_RELATIVE_PATH")"
RESPONSE_PATH="$(python3 -c 'from pathlib import Path; import sys; print(Path(sys.argv[1], sys.argv[2]))' "$MEETINGS_ROOT" "$RESPONSE_RELATIVE_PATH")"

PROMPT_PATH="$(mktemp -t meeting-ingest-t3-code.XXXXXX.txt)"
python3 - "$REQUEST_PATH" "$RESPONSE_PATH" "$HOST_NAME" "$MODEL_ID" > "$PROMPT_PATH" <<'PY'
from pathlib import Path
import sys

request_path, response_path, host_name, model_id = sys.argv[1:]
template = Path("docs/session-provider-subagent-prompt.md").read_text()
prompt = template.split("```text", 1)[1].split("```", 1)[0].strip()
prompt = prompt.replace("REQUEST_PATH", request_path)
prompt = prompt.replace("RESPONSE_PATH", response_path)
prompt = prompt.replace("HOST_NAME", host_name)
prompt = prompt.replace("MODEL_ID", model_id)
print(prompt)
PY

printf 'Run a dedicated T3 Code extraction sub-agent with this prompt:\n%s\n' "$PROMPT_PATH"
printf 'After it writes %s, run:\n' "$RESPONSE_PATH"
printf 'python3 -m meeting_ingest.cli ingest %q --provider session --provider-response %q --json\n' "$SOURCE" "$RESPONSE_PATH"
```
