# Evaluation Rubric and Demo Script

This document provides the evaluation criteria for the LLM-Powered File System Assistant project, along with a demo script for manual testing and a sign-off checklist.

---

## 1. Evaluation Rubric

### 1.1 Code Quality (30 points)

| Criterion | Points | Description |
| --------- | ------ | ----------- |
| **Tool contract consistency** | 10 | All tools return `{success: bool, error?: str, ...payload}` on every code path |
| **Sandbox security** | 10 | Path traversal blocked; all I/O confined to `data/` |
| **Error handling** | 5 | No raw stack traces leaked to LLM or user; structured errors |
| **Code organization** | 5 | Clear separation between `fs_tools.py` and `llm_file_assistant.py`; no circular dependencies |

---

### 1.2 Functionality (40 points)

| Criterion | Points | Description |
| --------- | ------ | ----------- |
| **File operations** | 10 | `read_file`, `list_files`, `write_file`, `search_in_file` work correctly |
| **Document parsing** | 10 | PDF, DOCX, TXT extraction works; unsupported types rejected |
| **Groq integration** | 10 | Tool calling loop works; LLM selects appropriate tools |
| **CLI interface** | 10 | REPL and single-query modes work; special commands (`/clear`, `exit`) function |

---

### 1.3 Testing (15 points)

| Criterion | Points | Description |
| --------- | ------ | ----------- |
| **Unit tests** | 10 | `pytest` passes; all 8+ test cases cover success/failure paths |
| **Test coverage** | 5 | Tests cover edge cases (path traversal, unsupported extensions, empty results) |

---

### 1.4 Documentation (15 points)

| Criterion | Points | Description |
| --------- | ------ | ----------- |
| **README.md** | 5 | Setup, usage, and project structure clearly documented |
| **Architecture docs** | 5 | `architecture.md`, `context.md`, `implementation-plan.md` present and complete |
| **Edge cases** | 5 | `edgecase.md` documents boundary conditions and failure modes |

---

**Total: 100 points**

---

## 2. Demo Script

### 2.1 Pre-Demo Checklist

Before running the demo, ensure:

- [ ] Python 3.10+ installed
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] `.env` file configured with valid `GROQ_API_KEY`
- [ ] Sample resumes exist in `data/resumes/` (7 files)
- [ ] Unit tests pass: `pytest tests/test_fs_tools.py -v`

---

### 2.2 Demo Flow (Interactive REPL)

**Step 1: Start the CLI**
```bash
python llm_file_assistant.py
```

**Expected output:**
```
AI Resume Assistant Started
Enter your query (type 'exit' or 'quit' to quit, '/clear' to reset conversation history):
>
```

---

**Step 2: List all resumes**
```
> List all files in the resumes folder
```

**Expected behavior:**
- LLM calls `list_files("resumes")`
- Returns list of 7 files: priya sharma.docx, rohan patel.txt, kavya nair.docx, arjun mehta.pdf, sneha iyer.pdf, rahul verma.txt, ananya reddy.pdf
- Response formatted naturally

---

**Step 3: Search for specific skill**
```
> Find resumes mentioning Python
```

**Expected behavior:**
- LLM calls `list_files` (optional) then `search_in_file` for each resume
- Returns candidates with Python experience (priya sharma.docx, rohan patel.txt, arjun mehta.pdf)
- Shows context snippets from matches

---

**Step 4: Read specific file**
```
> Read priya sharma.docx
```

**Expected behavior:**
- LLM calls `read_file("resumes/priya sharma.docx")`
- Returns file content and metadata
- Summarizes key information (name, skills, experience)

---

**Step 5: Write new file**
```
> Write a summary of Python developers to output/python_summary.txt
```

**Expected behavior:**
- LLM calls `search_in_file` to find Python developers
- Calls `write_file("output/python_summary.txt", "...")` with summary content
- Confirms file creation

---

**Step 6: Clear history**
```
> /clear
```

**Expected output:**
```
Conversation history cleared.
>
```

---

**Step 7: Exit**
```
> exit
```

**Expected output:**
```
Goodbye!
```

---

### 2.3 Demo Flow (Single Query Mode)

**Query 1: List files**
```bash
python llm_file_assistant.py --query "List all PDF resumes"
```

**Expected behavior:**
- LLM calls `list_files("resumes", ".pdf")`
- Returns PDF files: arjun mehta.pdf, sneha iyer.pdf, ananya reddy.pdf
- Exits after response

---

**Query 2: Search**
```bash
python llm_file_assistant.py --query "Who has React experience?"
```

**Expected behavior:**
- LLM searches resumes for "React"
- Returns kavya nair.docx (React, frontend skills)
- Exits after response

---

**Query 3: Complex query**
```bash
python llm_file_assistant.py --query "Find candidates with DevOps experience and save to output/devops_candidates.txt"
```

**Expected behavior:**
- LLM searches for "DevOps", "Docker", "Kubernetes"
- Finds sneha iyer.pdf
- Calls `write_file` to save results
- Confirms operation

---

### 2.4 Debug Mode Demo

```bash
python llm_file_assistant.py --query "List files in resumes" --debug
```

**Expected behavior:**
- Shows turn number, model name
- Shows tool calls being made
- Shows success/failure of each tool
- Shows final response

---

## 3. Manual Testing Checklist

### 3.1 File System Tools

- [ ] `read_file("resumes/arjun mehta.pdf")` returns content and metadata
- [ ] `read_file("missing.txt")` returns `{success: false, error: "File not found"}`
- [ ] `list_files("resumes")` returns 7 files
- [ ] `list_files("resumes", ".pdf")` returns 3 PDF files
- [ ] `write_file("output/test.txt", "Hello")` creates file successfully
- [ ] `search_in_file("resumes/arjun mehta.pdf", "Python")` returns matches with context
- [ ] `search_in_file("resumes/rahul verma.txt", "Python")` returns empty matches (success)
- [ ] `read_file("data.png")` returns `{success: false, error: "Unsupported file type"}`
- [ ] `read_file("../outside.txt")` returns `{success: false, error: "Access denied"}`

---

### 3.2 CLI Functionality

- [ ] `python llm_file_assistant.py` starts REPL
- [ ] `exit` or `quit` terminates REPL gracefully
- [ ] `/clear` clears conversation history
- [ ] Empty input is skipped (reprompt)
- [ ] `Ctrl+C` exits gracefully
- [ ] `--query "..."` runs single query and exits
- [ ] `--debug` flag enables verbose logging

---

### 3.3 LLM Integration

- [ ] LLM uses tools for file access (doesn't invent file contents)
- [ ] LLM explains tool failures to user
- [ ] LLM treats empty results as "none found" (not errors)
- [ ] LLM respects sandbox (doesn't request paths outside `data/`)
- [ ] Agent loop terminates after `MAX_AGENT_TURNS`

---

### 3.4 Security

- [ ] Path traversal (`../`) blocked
- [ ] Absolute paths outside `data/` blocked
- [ ] Unsupported file types rejected
- [ ] No stack traces leaked to user
- [ ] API key not logged or exposed

---

## 4. Sign-Off Checklist

### 4.1 Code Completeness

- [ ] `fs_tools.py` implements all 4 tools with uniform response contract
- [ ] `llm_file_assistant.py` implements Groq client, tool schemas, agent loop, CLI
- [ ] `requirements.txt` includes all dependencies (groq, pypdf, python-docx, python-dotenv, pytest)
- [ ] `.env.example` provided as template
- [ ] `.gitignore` excludes `.env`, `__pycache__`, `*.pyc`

---

### 4.2 Data Completeness

- [ ] `data/resumes/` contains 7 sample files
- [ ] Format split: 3 PDF, 2 DOCX, 2 TXT
- [ ] All files are readable via `read_file`
- [ ] Search keywords work as documented (Python, Java, React, DevOps, etc.)

---

### 4.3 Testing Completeness

- [ ] `pytest tests/test_fs_tools.py -v` passes all tests
- [ ] Tests cover success paths (read, list, write, search)
- [ ] Tests cover failure paths (missing files, unsupported types, path traversal)
- [ ] Tests use isolated sandbox directory

---

### 4.4 Documentation Completeness

- [ ] `README.md` includes setup, usage, project structure
- [ ] `docs/context.md` includes requirements, tool specs, Groq config
- [ ] `docs/architecture.md` includes system design, components, flows
- [ ] `docs/implementation-plan.md` includes phased build guide
- [ ] `docs/edgecase.md` includes boundary conditions and failure modes
- [ ] `docs/eval.md` includes rubric and demo script (this file)

---

### 4.5 End-to-End Verification

- [ ] "Find resumes mentioning Python" returns sensible answer
- [ ] "Read all resumes in resumes folder" works
- [ ] "Write summary to output/summary.txt" succeeds
- [ ] REPL multi-turn conversation works
- [ ] Single-query mode works
- [ ] Debug mode shows tool calls

---

## 5. Grading Criteria Summary

| Category | Weight | Pass Criteria |
| -------- | ------ | ------------- |
| Code Quality | 30% | All tools return consistent contract; sandbox secure; errors handled |
| Functionality | 40% | All 4 tools work; Groq integration functional; CLI works |
| Testing | 15% | Unit tests pass; edge cases covered |
| Documentation | 15% | README complete; all docs present and accurate |

**Passing Score:** 70/100 points

**Excellent Score:** 90/100 points

---

## 6. Common Issues and Fixes

### Issue: "GROQ_API_KEY not set"
**Fix:** Ensure `.env` file exists with valid API key; check `load_dotenv()` is called.

### Issue: Tests fail with "ModuleNotFoundError"
**Fix:** Ensure dependencies installed: `pip install -r requirements.txt`

### Issue: "Access denied" on valid paths
**Fix:** Ensure paths are relative to `data/` (e.g., `resumes/arjun mehta.pdf`, not `data/resumes/arjun mehta.pdf`)

### Issue: PDF extraction returns empty string
**Fix:** Verify PDF is not encrypted or corrupted; try `pdfplumber` as alternative to `pypdf`

### Issue: LLM doesn't use tools
**Fix:** Check system prompt; verify tool schemas match function signatures; check Groq model supports tool calling

---

## Related Documentation

- **[architecture.md](./architecture.md)** — System design and component details
- **[context.md](./context.md)** — Functional requirements and tool specifications
- **[implementation-plan.md](./implementation-plan.md)** — Phased build guide and acceptance criteria
- **[edgecase.md](./edgecase.md)** — Edge cases and failure modes
