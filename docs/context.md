# context.md

# AI File Assistant – Project Context

## Project Overview

This project aims to build an AI-powered File Assistant capable of performing file system operations and allowing a Large Language Model (LLM) to intelligently use those operations based on natural language user requests.

The system combines:

1. File system tools for reading, writing, searching, and listing files
2. **Groq**-hosted LLM tool-calling (reasoning and response generation)
3. A Command Line Interface (CLI) for user interaction

The application will focus on processing resume files and demonstrating how an LLM can act as a reasoning layer that decides which tool should be executed.

---

# Problem Statement

Modern users often need to manually search through multiple files to locate specific information.

Example problems:

- Reading multiple resumes one by one
- Searching for candidates with specific skills
- Creating summaries of documents
- Managing files manually

The process becomes inefficient when the number of files increases.

The goal of this project is to create an intelligent assistant that allows users to interact with files using natural language.

Example:

Instead of:

"Open arjun mehta.pdf and search for Python"

The user can simply type:

"Find resumes mentioning Python experience"

The system should automatically determine:

- which files to access
- which tools to execute
- how to combine results
- how to provide meaningful output

---

# Objectives

The project should:

- Read PDF, DOCX, and TXT files
- Extract textual content
- Search for keywords
- Create files dynamically
- List files with metadata
- Integrate file tools with **Groq** via native function / tool calling
- Allow the Groq model to choose tools automatically
- Provide responses through CLI

---

# Functional Requirements

## File System Tools

The following tools must be implemented.

**Sandbox:** All paths are relative to the `data/` folder. Users can read, write, and create files or folders only inside `data/` (e.g. `resumes/arjun mehta.pdf`, `output/summary.txt`).

### Tool response contract

Every tool returns a **JSON-serializable dict** with the same top-level shape:

| Field     | Type   | When present |
| --------- | ------ | ------------ |
| `success` | bool   | Always       |
| `error`   | string | Only when `success` is `False` |
| …         | varies | Tool-specific payload when `success` is `True` |

Rules:

- **`success: True`** — the tool ran correctly. Payload fields (`content`, `files`, `matches`, `message`, etc.) may be empty; that is still success (e.g. no search hits, empty folder).
- **`success: False`** — the tool could not complete (invalid path, missing file, permission error, unsupported format). Include a clear `error` message; omit tool-specific payload fields or set them to `null` / empty as appropriate.
- Do not rely on exceptions reaching the LLM — catch errors in `fs_tools.py` and return this structure so Groq always gets parseable tool results.

Failure example (any tool):

```python
{
    "success": False,
    "error": "Directory not found: resumes/missing"
}
```

---

### read_file(filepath)

Purpose:

Read document contents and return structured information.

Input:

```python
read_file("resumes/arjun mehta.pdf")
```

Output:

```python
{
    "success": True,
    "content": "John has 3 years of Python experience",
    "metadata": {
        "filename": "arjun mehta.pdf",
        "size": "230KB",
        "extension": ".pdf"
    }
}
```

Failure:

```python
{
    "success": False,
    "error": "File not found: resumes/missing.pdf"
}
```

---

### list_files(directory, extension=None)

Purpose:

Retrieve all files from a folder and optionally filter by extension.

Input:

```python
list_files("resumes",".pdf")
```

Output:

```python
{
    "success": True,
    "files": [
        {
            "name": "arjun mehta.pdf",
            "size": "230KB",
            "modified": "2026-05-20"
        },
        {
            "name": "alice.pdf",
            "size": "180KB",
            "modified": "2026-05-18"
        }
    ]
}
```

Empty directory (still success):

```python
{
    "success": True,
    "files": []
}
```

---

### write_file(filepath, content)

Purpose:

Create and write content to files.

Input:

```python
write_file(
"output/summary.txt",
"John has Python experience"
)
```

Output:

```python
{
    "success": True,
    "message": "File created successfully"
}
```

Failure:

```python
{
    "success": False,
    "error": "Permission denied: output/summary.txt"
}
```

---

### search_in_file(filepath, keyword)

Purpose:

Search file contents for keywords.

Input:

```python
search_in_file(
"arjun mehta.pdf",
"Python"
)
```

Output:

```python
{
    "success": True,
    "matches": [
        {
            "keyword": "Python",
            "context": "John has 3 years of Python experience"
        }
    ]
}
```

No matches (still success):

```python
{
    "success": True,
    "matches": []
}
```

Failure:

```python
{
    "success": False,
    "error": "File not found: arjun mehta.pdf"
}
```

---

# LLM Integration

## LLM Provider: Groq

This project uses **[Groq](https://console.groq.com/)** as the LLM provider.

Groq provides fast inference for open models and exposes an API that is compatible with OpenAI-style **chat completions** and **tool (function) calling**. The assistant sends tool definitions to Groq; the model returns structured `tool_calls`; Python executes the matching functions locally and sends results back to the model for the final answer.

### Why Groq

- Low-latency inference (good fit for an interactive CLI)
- Official Python SDK (`groq` on PyPI)
- Strong support for **local tool calling** (model requests tools; app runs them)
- API key already available for this project

### Configuration

Store the API key in the environment (do not commit secrets):

| Variable        | Description                          |
| --------------- | ------------------------------------ |
| `GROQ_API_KEY`  | Groq API key (read from [Groq Console](https://console.groq.com/keys)) |

Optional: use a `.env` file locally (e.g. with `python-dotenv`) and add `.env` to `.gitignore`. Provide `.env.example` with placeholder keys only.

```text
GROQ_API_KEY=your_groq_api_key_here
```

### Python SDK

Install via `requirements.txt`:

```text
groq
python-dotenv   # optional, for loading .env in development
```

Minimal client setup:

```python
import os
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
```

Use `client.chat.completions.create(...)` with `tools` and `tool_choice="auto"` for tool-calling loops.

Docs: [Groq Tool Use](https://console.groq.com/docs/tool-use/overview) · [groq-python](https://github.com/groq/groq-python)

### Recommended models

Pick one default model in `llm_file_assistant.py` (config constant or env var `GROQ_MODEL`):

| Model ID | Use case |
| -------- | -------- |
| `llama-3.3-70b-versatile` | **Default** — strong tool use and multi-step reasoning |
| `llama-3.1-8b-instant` | Faster, lighter CLI demos |
| `qwen/qwen3-32b` | Alternative with parallel tool use support |

All of the above support **local tool calling** for this assignment pattern. Avoid `groq/compound` and `groq/compound-mini` for custom local tools—they use Groq’s built-in tool flow instead.

### Tool-calling loop (Groq)

1. Send system prompt + user message + `tools` (JSON schemas for `read_file`, `list_files`, `write_file`, `search_in_file`).
2. If the assistant message includes `tool_calls`, run the matching Python functions with parsed arguments.
3. Append `role: "tool"` messages with results.
4. Call Groq again until the model returns a normal text reply (no further `tool_calls`).

Map each filesystem function to a Groq tool definition (`type: "function"`, `name`, `description`, `parameters`).

---

## Purpose

The Groq model acts as the reasoning component of the application.

The model does **not** directly execute Python code.

It only decides:

- what action should be performed
- which tool should be used
- what parameters are needed

Python functions in `fs_tools.py` execute the actual operations.

---

# LLM Workflow

System flow:

User Query
↓
CLI Input
↓
Groq API (chat.completions + tools)
↓
Tool Selection (model tool_calls)
↓
Python Tool Execution (fs_tools.py)
↓
Tool Result (sent back to Groq)
↓
Final Groq Response
↓
CLI Output

---

# Example Flow

User:

```text
Find resumes mentioning Python experience
```

Groq assistant message (tool_calls excerpt):

```json
{
    "tool_calls": [
        {
            "type": "function",
            "function": {
                "name": "search_in_file",
                "arguments": "{\"filepath\":\"arjun mehta.pdf\",\"keyword\":\"Python\"}"
            }
        }
    ]
}
```

Python executes:

```python
search_in_file(
    "arjun mehta.pdf",
    "Python"
)
```

Tool result:

```python
{
    "success": True,
    "matches": [
        {
            "keyword": "Python",
            "context": "John has 3 years of Python experience"
        }
    ]
}
```

Final LLM response:

```text
Found Python experience in arjun mehta.pdf

Context:

John has 3 years of Python experience
```

---

# LLM Input and Output Structure

## Input to Groq

The model receives:

1. User query
2. Available tool descriptions
3. Tool definitions
4. Previous conversation context if needed

Example:

```python
{
    "query":
    "Find resumes mentioning Python",

    "tools":[
        "read_file",
        "search_in_file",
        "write_file",
        "list_files"
    ]
}
```

---

## Output from Groq

Primary output is the chat completion **assistant message**:

- **Text** — final answer for the user when no more tools are needed.
- **`tool_calls`** — one or more function calls to run locally before the next API request.

Conceptual mapping (after parsing `function.arguments` JSON):

```python
{
    "tool": "search_in_file",
    "arguments": {
        "filepath": "arjun mehta.pdf",
        "keyword": "Python"
    }
}
```

Multiple tools in one turn are supported on models such as `llama-3.3-70b-versatile` (parallel tool calls per Groq docs).

---

# User Interface Decision

## CLI Approach

This project will use a Command Line Interface (CLI).

Reasoning:

- Assignment requirements do not mention frontend development
- CLI keeps implementation simple
- Faster development
- Easier debugging
- Focus remains on LLM tool-calling functionality
- Suitable for demonstration purposes

---

# Expected CLI Interaction

Program startup:

```text
AI Resume Assistant Started
Enter your query:
```

Example:

```text
> Read all resumes in resumes folder
```

Output:

```text
Found files:

1. arjun mehta.pdf
2. priya sharma.docx
3. rahul verma.txt
```

Example:

```text
> Find resumes mentioning Python
```

Output:

```text
Found matches:

arjun mehta.pdf
Context:
Arjun has 3 years of Python experience

priya sharma.docx
Context:
Worked on Python automation systems
```

---

# Proposed Project Structure

project-root/

├── fs_tools.py
├── llm_file_assistant.py      # Groq client, tool schemas, agent loop
├── requirements.txt           # includes groq
├── .env                       # local only — GROQ_API_KEY (gitignored)
├── .env.example               # GROQ_API_KEY=, optional GROQ_MODEL=
├── README.md
├── docs/
│   ├── context.md
│   ├── architecture.md
│   ├── implementation-plan.md
│   ├── edgecase.md
│   └── eval.md
│
├── data/                      # sandbox — all file tool paths live here
│   ├── resumes/               # seven sample resumes
│   │   ├── arjun mehta.pdf
│   │   ├── priya sharma.docx
│   │   └── ...
│   └── (user-created folders) # e.g. output/summary.txt

---

# Development Approach

Phase 1:

- Build fs_tools.py
- Test all tools independently

Phase 2:

- Integrate Groq tool-calling (`groq` SDK, `GROQ_API_KEY`, default model `llama-3.3-70b-versatile`)
- Define tool schemas and implement the request → tool_calls → execute → respond loop

Phase 3:

- Build CLI interaction

Phase 4:

- Create sample resume files

Phase 5:

- Documentation and demo video

---

# Final Goal

Create an AI-powered assistant that can understand natural language requests and intelligently perform file operations through **Groq**-guided tool execution.

---

## Related documentation

- [architecture.md](./architecture.md) — system design
- [implementation-plan.md](./implementation-plan.md) — phased build guide
- [edgecase.md](./edgecase.md) — edge cases and failure modes
- [eval.md](./eval.md) — evaluation rubric and demo script