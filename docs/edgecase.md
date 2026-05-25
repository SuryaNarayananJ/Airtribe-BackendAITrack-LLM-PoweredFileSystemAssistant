# Edge Cases and Failure Modes

This document describes boundary conditions, edge cases, and failure modes for the LLM-Powered File System Assistant, along with expected behavior and mitigation strategies.

---

## 1. File System Edge Cases

### 1.1 Path Traversal Attempts

**Scenario:** User attempts to access files outside the sandbox using relative paths like `../../secret.txt` or absolute paths like `C:\Users\secret.txt`.

**Expected Behavior:**
- `read_file`, `write_file`, `list_files`, `search_in_file` all return `{success: false, error: "Access denied: path must be inside data/ (...)"}`
- No files outside `data/` are accessed
- Error message is clear and does not leak system paths

**Mitigation:** `_resolve_path()` in `fs_tools.py` validates all paths against `DATA_ROOT` before any operation.

---

### 1.2 Non-Existent Paths

**Scenario:** User references files or directories that don't exist.

**Expected Behavior:**
- `read_file("missing.txt")` → `{success: false, error: "File not found: missing.txt"}`
- `list_files("missing_dir")` → `{success: false, error: "Directory not found: missing_dir"}`
- `search_in_file("missing.txt", "keyword")` → `{success: false, error: "File not found: missing.txt"}`

**Mitigation:** Path existence checks before operations; structured error responses.

---

### 1.3 Unsupported File Extensions

**Scenario:** User attempts to read or search files with extensions other than `.pdf`, `.docx`, `.txt` (e.g., `.png`, `.exe`, `.json`).

**Expected Behavior:**
- `read_file("image.png")` → `{success: false, error: "Unsupported file type: .png"}`
- `search_in_file("data.json", "key")` → `{success: false, error: "Unsupported file type: .json"}`
- `write_file` allows any extension (creates plain text files)

**Mitigation:** Extension whitelist in `fs_tools.py`; clear error messages for unsupported types.

---

### 1.4 Empty Files and Directories

**Scenario:**
- Empty file: `read_file("empty.txt")` on a 0-byte file
- Empty directory: `list_files("empty_dir")` on a folder with no files

**Expected Behavior:**
- Empty file: `{success: true, content: "", metadata: {...}}` (success, not failure)
- Empty directory: `{success: true, files: []}` (success, not failure)
- LLM should interpret empty results as "none found" rather than errors

**Mitigation:** Distinguish between "no results" (success) and "operation failed" (error).

---

### 1.5 Large Files

**Scenario:** Very large resume files (e.g., 10MB+ PDFs).

**Expected Behavior:**
- Current implementation reads full content; may be slow
- No explicit size limit in current implementation
- Future enhancement: truncate with notice in metadata

**Mitigation:** (Optional) Add max bytes limit with truncation warning.

---

## 2. Document Parsing Edge Cases

### 2.1 Corrupted PDF Files

**Scenario:** PDF file is corrupted or encrypted.

**Expected Behavior:**
- `read_file` catches exception from `pypdf`
- Returns `{success: false, error: "..."}` with clear message
- No raw stack trace leaked to LLM

**Mitigation:** Try/except around all parsing functions; structured error responses.

---

### 2.2 Malformed DOCX Files

**Scenario:** DOCX file structure is invalid or unreadable.

**Expected Behavior:**
- `read_file` catches exception from `python-docx`
- Returns `{success: false, error: "..."}` with clear message
- No raw stack trace leaked to LLM

**Mitigation:** Try/except around `Document()` and paragraph extraction.

---

### 2.3 Non-UTF-8 Text Files

**Scenario:** TXT file uses encoding other than UTF-8 (e.g., UTF-16, Latin-1).

**Expected Behavior:**
- `read_file` catches `UnicodeDecodeError`
- Returns `{success: false, error: "File is not valid UTF-8 text: filename"}`
- No raw stack trace leaked to LLM

**Mitigation:** Explicit UTF-8 encoding with error handling in `_read_txt`.

---

### 2.4 Search Keyword Not Found

**Scenario:** `search_in_file("resume.txt", "nonexistent_keyword")` where keyword doesn't exist.

**Expected Behavior:**
- `{success: true, matches: []}` (success, not failure)
- LLM should report "no matches found" rather than treating as error

**Mitigation:** Clear distinction in tool contract between empty results and failures.

---

## 3. LLM and Agent Edge Cases

### 3.1 Infinite Tool Loop

**Scenario:** LLM keeps calling tools without reaching a final answer (e.g., repeatedly listing files).

**Expected Behavior:**
- Agent loop terminates after `MAX_AGENT_TURNS` (default: 12)
- Returns user-visible message: "I have reached the maximum allowed analysis steps without finding a final answer. Please try refining your query."
- No infinite loop or hang

**Mitigation:** `MAX_AGENT_TURNS` guard in `run_agent()` loop.

---

### 3.2 Groq API Errors

**Scenario:** Network failure, authentication error, rate limit, or invalid API key.

**Expected Behavior:**
- Agent catches `GroqError` and other exceptions
- Returns user-friendly message: "I encountered an error communicating with the AI service: ..."
- CLI does not crash; user can retry

**Mitigation:** Try/except around Groq API calls; structured error messages.

---

### 3.3 Invalid Tool Call JSON

**Scenario:** LLM returns malformed JSON in `tool_calls` arguments.

**Expected Behavior:**
- Dispatcher catches `json.JSONDecodeError`
- Returns `{success: false, error: "Invalid JSON arguments: ..."}`
- LLM receives structured failure and can retry or explain error

**Mitigation:** JSON parsing with error handling in `dispatch_tool()`.

---

### 3.4 Unknown Tool Name

**Scenario:** LLM requests a tool that doesn't exist in the registry.

**Expected Behavior:**
- Dispatcher returns `{success: false, error: "Unknown tool: 'tool_name'"}`
- LLM receives structured failure and can adjust

**Mitigation:** Tool name validation in `dispatch_tool()`.

---

### 3.5 Empty or Null Query

**Scenario:** User sends empty string or only whitespace as query.

**Expected Behavior:**
- CLI skips empty input (reprompts)
- If passed to agent, LLM may respond with clarification request

**Mitigation:** CLI-level validation in REPL loop.

---

## 4. Configuration Edge Cases

### 4.1 Missing GROQ_API_KEY

**Scenario:** `.env` file missing or `GROQ_API_KEY` not set.

**Expected Behavior:**
- `load_config()` fails fast on startup
- Prints error to stderr: "ERROR: GROQ_API_KEY environment variable is not set."
- Exits with code 1
- Does not proceed to try API calls

**Mitigation:** Early validation in `load_config()`.

---

### 4.2 Invalid MAX_AGENT_TURNS

**Scenario:** `MAX_AGENT_TURNS` set to non-integer value (e.g., "abc").

**Expected Behavior:**
- `load_config()` catches `ValueError`
- Falls back to default value (12)
- Logs or warns (optional)

**Mitigation:** Try/except with default fallback in `load_config()`.

---

### 4.3 Invalid DEBUG Value

**Scenario:** `DEBUG` set to arbitrary string (e.g., "maybe").

**Expected Behavior:**
- `load_config()` treats any value other than "true", "1", "yes", "on" as false
- No error; simply disables debug mode

**Mitigation:** Case-insensitive boolean parsing in `load_config()`.

---

## 5. CLI Edge Cases

### 5.1 Keyboard Interrupt

**Scenario:** User presses `Ctrl+C` during REPL or query execution.

**Expected Behavior:**
- CLI catches `KeyboardInterrupt`
- Prints "Goodbye!" or similar message
- Exits gracefully
- No stack trace shown to user

**Mitigation:** Try/except around REPL loop in `main()`.

---

### 5.2 EOF (End of File)

**Scenario:** Input stream closed (e.g., piped input ends).

**Expected Behavior:**
- CLI catches `EOFError`
- Prints "Goodbye!" or similar message
- Exits gracefully

**Mitigation:** Try/except around REPL loop in `main()`.

---

### 5.3 Special Commands

**Scenario:** User types `/clear`, `exit`, or `quit` in REPL.

**Expected Behavior:**
- `/clear`: Clears conversation history; prints "Conversation history cleared."
- `exit` / `quit`: Terminates REPL; prints "Goodbye!"
- Commands are case-insensitive

**Mitigation:** Explicit command handling in REPL loop.

---

## 6. Security Edge Cases

### 6.1 Symbolic Links Outside Sandbox

**Scenario:** Symlink inside `data/` points to file outside sandbox.

**Expected Behavior:**
- Current implementation uses `resolve()` which follows symlinks
- If symlink target is outside `DATA_ROOT`, `relative_to()` check fails
- Returns `{success: false, error: "Access denied: path must be inside data/ (...)"}`

**Mitigation:** Path resolution with `relative_to()` validation.

---

### 6.2 Case Sensitivity in Paths

**Scenario:** User provides path with different case than actual file (e.g., `resumes/arjun mehta.pdf` vs `resumes/arjun mehta.pdf`).

**Expected Behavior:**
- On Windows: case-insensitive filesystem; path works
- On Linux/macOS: case-sensitive; may fail if case doesn't match
- Error message: "File not found: ..."

**Mitigation:** Document platform-specific behavior; encourage consistent casing.

---

### 6.3 Permission Denied

**Scenario:** File exists but user lacks read/write permissions.

**Expected Behavior:**
- `write_file` catches `PermissionError`
- Returns `{success: false, error: "Permission denied: filepath"}`
- No raw OS error leaked

**Mitigation:** Explicit `PermissionError` handling in `write_file`.

---

## 7. Testing Edge Cases

### 7.1 Concurrent File Access

**Scenario:** Test writes and reads same file simultaneously.

**Expected Behavior:**
- Tests use isolated `test_sandbox` directory
- Fixture cleans up after each test
- No interference between tests

**Mitigation:** `autouse=True` fixture with setup/teardown in `test_fs_tools.py`.

---

### 7.2 Test Data Pollution

**Scenario:** Tests create files that persist after test run.

**Expected Behavior:**
- Fixture removes `test_sandbox` directory after each test
- Production data in `data/resumes/` never modified by tests

**Mitigation:** Isolated test directory; cleanup in fixture.

---

## 8. Summary of Mitigation Strategies

| Category | Primary Mitigation |
| -------- | ------------------ |
| Path security | `_resolve_path()` with `relative_to()` check |
| Parsing errors | Try/except with structured error responses |
| API failures | Try/except with user-friendly messages |
| Infinite loops | `MAX_AGENT_TURNS` guard |
| Invalid input | Validation at CLI and dispatcher levels |
| Permission errors | Explicit exception handling |
| Test isolation | Dedicated test sandbox with cleanup |

---

## Related Documentation

- **[architecture.md](./architecture.md)** — Error handling strategy (§10), security (§6.4)
- **[context.md](./context.md)** — Tool response contract (§1.1)
- **[implementation-plan.md](./implementation-plan.md)** — Risk register (Risk register & mitigations)
