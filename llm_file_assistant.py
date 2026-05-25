"""LLM-Powered File System Assistant - Main Orchestration and CLI Layer."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Callable

from dotenv import load_dotenv
from groq import Groq, GroqError

import fs_tools

# Load environment variables from .env if present
load_dotenv()

# --- 1. Configuration ---

def load_config() -> dict[str, Any]:
    """Load configuration from environment variables and enforce required settings."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("ERROR: GROQ_API_KEY environment variable is not set.", file=sys.stderr)
        print("Please configure it in a local .env file or export it in your environment.", file=sys.stderr)
        sys.exit(1)

    model = os.environ.get("GROQ_MODEL", "qwen/qwen-2.5-32b").strip()
    
    # Parse turns guard
    try:
        max_turns = int(os.environ.get("MAX_AGENT_TURNS", "12"))
    except ValueError:
        max_turns = 12

    # Parse debug flag
    debug_val = os.environ.get("DEBUG", "false").lower()
    debug = debug_val in ("true", "1", "yes", "on")

    return {
        "api_key": api_key,
        "model": model,
        "max_turns": max_turns,
        "debug": debug
    }


# --- 2. Tool Schemas & Registry ---

# Definitions for the Groq tool calling API
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read document contents (PDF, DOCX, TXT) and return structured text content and metadata under the data/ sandbox directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Relative path to the file inside the data/ sandbox (e.g., 'resumes/john.pdf')."
                    }
                },
                "required": ["filepath"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "Retrieve all files from a directory inside the data/ sandbox, optionally filtered by extension.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "Relative path to the directory inside the data/ sandbox (e.g., 'resumes')."
                    },
                    "extension": {
                        "type": "string",
                        "description": "Optional file extension to filter by (e.g., '.pdf', 'pdf', '.docx'). Case-insensitive."
                    }
                },
                "required": ["directory"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create a new file or overwrite an existing file inside the data/ sandbox with the provided text content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Relative path to the file inside the data/ sandbox (e.g., 'output/summary.txt'). Parent folders are created if missing."
                    },
                    "content": {
                        "type": "string",
                        "description": "The textual content to write to the file."
                    }
                },
                "required": ["filepath", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_in_file",
            "description": "Search file contents (PDF, DOCX, TXT) inside the data/ sandbox for a given keyword and return context snippets.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Relative path to the file inside the data/ sandbox (e.g., 'resumes/david.txt')."
                    },
                    "keyword": {
                        "type": "string",
                        "description": "The keyword/phrase to search for (case-insensitive literal search)."
                    }
                },
                "required": ["filepath", "keyword"]
            }
        }
    }
]

# Map tool names to their corresponding python functions
TOOL_REGISTRY: dict[str, Callable[..., dict[str, Any]]] = {
    "read_file": fs_tools.read_file,
    "list_files": fs_tools.list_files,
    "write_file": fs_tools.write_file,
    "search_in_file": fs_tools.search_in_file
}


# --- 3. System Prompt ---

SYSTEM_PROMPT = """You are a helpful and efficient Resume and File Assistant.
You have access to a secure filesystem sandbox called data/.
All file operations must be performed using the provided tools.
You must adhere strictly to these rules:
1. ONLY access files inside the data/ sandbox using the provided tools. Do not make up, assume, or fabricate any file contents. If a file is not read using the read_file or search_in_file tools, you do not know its content.
2. If you are asked to look for files or lists of files, prefer using `list_files` first to see what exists in a directory, rather than guessing file paths.
3. If a tool execution fails (returns `success: false`), explain the error clearly to the user. Do not pretend it succeeded or ignore the failure.
4. Empty results (e.g. search_in_file returns no matches, list_files returns no files) are a successful completion indicating "none found". Do not treat them as failures.
5. All new folders or files you create should be placed appropriately under the data/ sandbox (e.g. `output/summary.txt`, `output/summaries/john_summary.txt`).
6. Do not mention the inner workings of tools, path resolution, or technical details unless asked. Focus on providing clear, natural answers to the user's queries.
"""


# --- 4. Dispatcher & Agent Loop ---

def dispatch_tool(name: str, arguments_json: str) -> dict[str, Any]:
    """Safe dispatcher that handles name matching, argument decoding, and maps errors cleanly."""
    if name not in TOOL_REGISTRY:
        return {"success": False, "error": f"Unknown tool: '{name}'"}

    try:
        args = json.loads(arguments_json) if arguments_json else {}
    except json.JSONDecodeError as exc:
        return {"success": False, "error": f"Invalid JSON arguments: {str(exc)}"}

    try:
        handler = TOOL_REGISTRY[name]
        return handler(**args)
    except Exception as exc:
        return {"success": False, "error": f"Unexpected execution error in tool '{name}': {str(exc)}"}


def run_agent(client: Groq, user_query: str, history: list[dict[str, Any]] | None = None, config: dict[str, Any] | None = None) -> str:
    """Run the main ReAct agent loop to address the user query using local tools."""
    if config is None:
        config = load_config()

    debug = config["debug"]
    model = config["model"]
    max_turns = config["max_turns"]

    # Initialize messages list with system prompt and history/query
    messages: list[Any] = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    if history:
        messages.extend(history)
    
    messages.append({"role": "user", "content": user_query})

    if debug:
        print(f"\n[DEBUG] Running agent with model: {model}")
        print(f"[DEBUG] User query: '{user_query}'")

    for turn in range(1, max_turns + 1):
        if debug:
            print(f"[DEBUG] --- Turn {turn} of {max_turns} ---")

        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto"
            )
        except GroqError as exc:
            err_msg = f"Groq API Error: {str(exc)}"
            if debug:
                print(f"[DEBUG] API call failed: {err_msg}")
            # Handle tool validation errors specifically
            if "tool call validation failed" in str(exc):
                return "I encountered an internal error with the AI service's tool calling. Please try a simpler query or try again in a moment."
            return f"I encountered an error communicating with the AI service: {str(exc)}"
        except Exception as exc:
            err_msg = f"Unexpected connection error: {str(exc)}"
            if debug:
                print(f"[DEBUG] Connection failed: {err_msg}")
            return f"I could not connect to the AI service. Please check your network connection: {str(exc)}"

        response_message = response.choices[0].message
        
        # Append assistant response (mandatory even if content is null because it contains tool_calls)
        messages.append(response_message)

        tool_calls = getattr(response_message, "tool_calls", None)

        if not tool_calls:
            if debug:
                print("[DEBUG] No more tool calls requested. Returning final answer.")
            if isinstance(history, list):
                history.extend(messages[1 + len(history):])
            return response_message.content or ""

        if debug:
            print(f"[DEBUG] Model requested {len(tool_calls)} tool call(s):")

        # Execute tool calls (supports parallel execution)
        for tool_call in tool_calls:
            call_id = tool_call.id
            func_name = tool_call.function.name
            func_args = tool_call.function.arguments

            if debug:
                print(f"[DEBUG]   -> Call {func_name}({func_args}) [ID: {call_id}]")

            # Dispatch the tool locally
            result = dispatch_tool(func_name, func_args)

            if debug:
                success_str = "SUCCESS" if result.get("success") else "FAILURE"
                print(f"[DEBUG]      Result [{success_str}]: {json.dumps(result)[:160]}...")

            # Feed back tool output
            messages.append({
                "role": "tool",
                "tool_call_id": call_id,
                "name": func_name,
                "content": json.dumps(result)
            })

    # If loop completes without natural language termination
    warn_msg = "I have reached the maximum allowed analysis steps without finding a final answer. Please try refining your query."
    if debug:
        print(f"[DEBUG] {warn_msg}")
    if isinstance(history, list):
        history.extend(messages[1 + len(history):])
    return warn_msg


# --- 5. Temporary smoke / CLI handler for testing Phase 2 ---

def main():
    """Main CLI execution entrypoint."""
    config = load_config()
    
    # Simple argument parser for Phase 2 debugging / early execution
    parser = argparse.ArgumentParser(description="AI File Assistant Orchestration CLI")
    parser.add_argument("--query", type=str, help="Run a single natural language query directly against the agent.")
    parser.add_argument("--debug", action="store_true", help="Enable verbose debug logging.")
    args = parser.parse_args()

    # Override debug config if explicitly provided in args
    if args.debug:
        config["debug"] = True

    client = Groq(api_key=config["api_key"])

    if args.query:
        # Run a single query directly and exit (excellent for pipelines or grading checks)
        response = run_agent(client, args.query, config=config)
        print("\n=== Agent Response ===")
        print(response)
        sys.exit(0)
    else:
        print("AI Resume Assistant Started")
        print("Enter your query (type 'exit' or 'quit' to quit, '/clear' to reset conversation history):")
        history = []
        while True:
            try:
                user_input = input("> ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ("exit", "quit"):
                    print("Goodbye!")
                    break
                if user_input.lower() == "/clear":
                    history.clear()
                    print("Conversation history cleared.")
                    continue
                
                # Run agent and print result
                response = run_agent(client, user_input, history=history, config=config)
                print(f"\n{response}\n")
            except (KeyboardInterrupt, EOFError):
                print("\nGoodbye!")
                break


if __name__ == "__main__":
    main()
