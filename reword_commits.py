import sys
import re

def rewrite_message(msg):
    # Rule 1: No conventional-commit prefixes like "Fix:", "feat:", "chore:"
    # Rule 2: Must read like a human wrote them in plain English.
    
    # We will specifically target the ones we know about first:
    specifics = {
        "Fix: add support for F.audio files": "Added support for F.audio voice files",
        "Stage 13: LangGraph Query Agent": "Built the LangGraph query agent",
        "Stage 12: MCP Server (Expose Financial Tools)": "Exposed financial tools via an MCP server",
        "Stage 11: Agentic Environment Setup (LangGraph & MCP)": "Set up the agentic environment with LangGraph and MCP",
        "Update Telegram menu with /start command": "Updated the Telegram menu with the /start command",
        "Fix: correct Optional typing for query tool to resolve Groq schema validation crashes": "Corrected Optional typing for query tool to resolve Groq schema validation crashes"
    }
    
    for old, new in specifics.items():
        if old in msg:
            return msg.replace(old, new)
            
    # For others, just try to strip known bad prefixes and capitalize:
    lines = msg.split('\n')
    if lines:
        first_line = lines[0]
        # Remove prefixes like "Fix: ", "feat: ", "chore: "
        first_line = re.sub(r'^(?:Fix|Fixes|Feature|feat|chore|docs|style|refactor|test|Optimize|Revert|Enhance|Update)(?:\(.*\))?:\s*', '', first_line, flags=re.IGNORECASE)
        # Convert imperative to past tense for some common ones if it reads better, but simple capitalization is safe
        if first_line:
            first_line = first_line[0].upper() + first_line[1:]
        lines[0] = first_line
    return '\n'.join(lines)

def main():
    file_path = sys.argv[1]
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # If this is the sequence editor (git-rebase-todo)
    if 'git-rebase-todo' in file_path:
        # Change 'pick' to 'reword' for all commits to ensure we can fix all messages
        content = re.sub(r'^pick ', 'reword ', content, flags=re.MULTILINE)
    else:
        # This is the commit message editor
        content = rewrite_message(content)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == "__main__":
    main()
