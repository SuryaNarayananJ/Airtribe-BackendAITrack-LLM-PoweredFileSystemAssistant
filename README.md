# LLM-Powered File System Assistant

An AI-powered File System Assistant capable of performing file system operations and enabling a Large Language Model (LLM) to intelligently select and execute those operations based on natural language user queries. 

The system utilizes **Groq**-hosted LLM tool calling (using `llama-3.3-70b-versatile` by default) as the reasoning layer, backed by deterministic Python-based local tools. It is specifically designed to work with resumes (PDF, DOCX, TXT formats) and is strictly confined to a sandbox directory (`data/`) for security.

---

## 🚀 Features

- **Natural Language File Management**: Query your files using regular English (e.g. *"Who has React experience?"* or *"List all resumes in the resumes folder"*).
- **Secure Sandbox Confinement**: Path resolution blocks any directory traversal or read/write operations outside the local `data/` folder.
- **Robust Parsing Support**: Out-of-the-box text extraction from PDF (`pypdf`), DOCX (`python-docx`), and raw text (UTF-8 `txt`).
- **Interactive Multi-Turn REPL**: Maintain context across subsequent prompts inside the CLI session.
- **Special Command Support**: `/clear` resets the conversation history, and `exit`/`quit` terminates the REPL gracefully.

---

## 📁 Project Structure

```text
LLM-Powered File System Assistant/
├── fs_tools.py               # Deterministic file operations & sandbox confinement
├── llm_file_assistant.py     # Main agent loop, Groq client, tool definitions & CLI REPL
├── requirements.txt          # Python library dependencies
├── .env.example              # Template for environment configuration
├── .gitignore                # Git ignore patterns (venv, .env, __pycache__, etc.)
├── README.md                 # Project guide & instructions (this file)
├── data/                     # Secure Sandbox root (confines all tool paths)
│   └── resumes/              # Seven sample resumes representing Indian profiles
│       ├── priya sharma.docx
│       ├── rohan patel.txt
│       ├── kavya nair.docx
│       ├── arjun mehta.pdf
│       ├── sneha iyer.pdf
│       ├── rahul verma.txt
│       └── ananya reddy.pdf
└── docs/                     # Architectural design and evaluation guides
    ├── architecture.md
    ├── context.md
    ├── edgecase.md
    ├── eval.md
    └── implementation-plan.md
```

---

## 📄 Sample Resumes Data

The sandbox contains 7 pre-configured sample resumes in the `data/resumes/` folder using **Indian** names, cities, phone numbers (`+91`), and education:

| File | Format | Candidate Name & Location | Key Skills / Search Keywords |
| ---- | ------ | ------------------------- | ---------------------------- |
| `arjun mehta.pdf` | PDF | Arjun Mehta (Mumbai) | Python |
| `priya sharma.docx` | DOCX | Priya Sharma (Bengaluru) | Python, automation |
| `rahul verma.txt` | TXT | Rahul Verma (Delhi) | Agile, Scrum (no Python) |
| `ananya reddy.pdf` | PDF | Ananya Reddy (Hyderabad) | Java, Spring Boot |
| `kavya nair.docx` | DOCX | Kavya Nair (Kochi) | React, frontend |
| `rohan patel.txt` | TXT | Rohan Patel (Pune) | Python, machine learning |
| `sneha iyer.pdf` | PDF | Sneha Iyer (Chennai) | DevOps, Docker, Kubernetes |

**Format split**: 3 PDF, 2 DOCX, 2 TXT.

---

## 🛠️ Setup & Installation

### Prerequisites
- Python 3.10+ (must be installed globally)
- A Groq API Key (get one from [Groq Console](https://console.groq.com/))

### Steps

1. **Verify Python Installation**:
   Check if Python is installed by running:
   ```bash
   python --version
   ```
   If Python is not installed, download and install it from [python.org](https://www.python.org/downloads/).
   **Important:** During installation, check the box **"Add Python to PATH"** to enable running Python from the terminal.

2. **Navigate to the project root directory** in your terminal.

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   This will install: groq, pypdf, python-docx, python-dotenv, and pytest.

4. **Configure Environment Variables**:
   Copy `.env.example` to a new `.env` file:
   ```bash
   copy .env.example .env
   ```
   Open the `.env` file in a text editor and input your Groq API Key:
   ```text
   GROQ_API_KEY=gsk_your_actual_key_here
   GROQ_MODEL=llama-3.3-70b-versatile
   MAX_AGENT_TURNS=12
   DEBUG=false
   ```
   *(Note: `.env` is automatically ignored by Git).*

---

## 🖥️ Usage

You can interact with the assistant in two ways:

### 1. Interactive REPL Mode (Recommended)
Launch the CLI loop:
```bash
python llm_file_assistant.py
```
This launches the REPL where you can enter multiple commands sequentially:
```text
AI Resume Assistant Started
Enter your query (type 'exit' or 'quit' to quit, '/clear' to reset conversation history):
> List all files in the resumes folder
...
> Find resumes mentioning Python
...
> /clear
Conversation history cleared.
> exit
Goodbye!
```

### 2. Single Query Mode
Execute a single query directly from the terminal and exit:
```bash
python llm_file_assistant.py --query "Find resumes mentioning Java"
```

### 3. Debug Mode
Enable verbose debug logs to inspect tool calls, model decisions, and conversation steps in real time:
```bash
python llm_file_assistant.py --debug
# Or with a single query
python llm_file_assistant.py --query "List PDF resumes" --debug
```

---

## 📝 Sample Queries for Testing

Here are some example queries you can use to test the assistant's capabilities:

### File Listing
- "List all files in the resumes folder"
- "List all PDF resumes"
- "List all DOCX files in resumes"
- "Show me all TXT files"

### Content Search
- "Find resumes mentioning Python"
- "Who has React experience?"
- "Search for Java skills in resumes"
- "Find candidates with DevOps experience"
- "Who has machine learning experience?"

### File Reading
- "Read resumes/arjun mehta.pdf"
- "Show me the content of resumes/priya sharma.docx"
- "Read the resume of the candidate with Python experience"

### File Creation
- "Write a summary of Python developers to output/python_summary.txt"
- "Save a list of Java developers to output/java_candidates.txt"
- "Create a summary of all resumes to output/all_resumes_summary.txt"

### Complex Queries
- "Find all candidates with Python experience and save their names to output/python_devs.txt"
- "Who has both frontend and backend skills?"
- "Compare the skills of resumes/arjun mehta.pdf and resumes/priya sharma.docx"
- "List all candidates and their primary skills"

### Security Testing
- "Read file outside the data folder" (should fail with access denied)
- "List files in C:\Windows" (should fail with access denied)
- "Read ../secret.txt" (should fail with access denied)

---

## 🛡️ Sandbox & Security Policy

All tool executions are restricted under `data/`:
- **Paths outside the sandbox** (e.g. `../../secret.txt` or absolute paths like `C:\Users\secret.txt`) will fail with an `Access denied` error.
- **Handling formats**: Only `.pdf`, `.docx`, and `.txt` extensions are supported. Any request for unsupported extensions will be safely rejected with a structured failure response, ensuring no raw stack traces leak to the LLM or end-user.
