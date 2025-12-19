# Red Teaming Agentic AI System

A powerful Python-based red teaming AI system that uses LLM agents (Gemini or Ollama) to solve Capture The Flag (CTF) challenges. The system features an intuitive terminal UI with real-time display of agent reasoning, tool execution, and results.

## Features

- 🤖 **Multiple Agent Support**: Choose between Gemini API or local Ollama models
- 🎯 **Web CTF Mode**: Specialized mode for web security challenges
- 🛠️ **Built-in Tools**: Base64 encoding/decoding and web content fetching
- 🎨 **Beautiful Terminal UI**: Auto-adjusting bordered frames for clear visualization
- 📝 **Comprehensive Logging**: Automatic session logging in both text and JSON formats
- 🔄 **ReAct Pattern**: Agents use Thought → Action → Observation loop for problem-solving
- 🛡️ **Anti-Hallucination**: Engineered prompts and stop sequences prevent agents from making up tool outputs
- 📚 **Structured Prompts**: Highly engineered prompts in `prompts/` folder ensure reliable agent behavior

## Installation

### Prerequisites

- Python 3.10 or higher
- (Optional) [Ollama](https://ollama.ai/) for local LLM support

### Setup

1. **Clone or navigate to the project directory**

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   ```

4. **Edit `.env` file**:
   - Add your Gemini API key (get one from [Google AI Studio](https://aistudio.google.com/app/apikey))
   - Or configure Ollama settings if using local models

   ```env
   GEMINI_API_KEY=your_api_key_here
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_MODEL=llama3.1
   ```

5. **(Optional) Setup Ollama**:
   ```bash
   # Install and start Ollama
   ollama serve
   
   # Pull the model
   ollama pull llama3.1
   ```

## Usage

### Starting the System

```bash
python main.py
```

### Basic Workflow

1. **Select an agent**:
   ```
   /agent gemini
   ```
   or
   ```
   /agent ollama
   ```

2. **Select a mode**:
   ```
   /mode web-ctf
   ```

3. **Give the agent a challenge**:
   ```
   Find the flag at http://ctf-challenge.example.com
   ```

### Available Commands

- `/agent gemini` - Switch to Gemini agent
- `/agent ollama` - Switch to Ollama agent
- `/mode web-ctf` - Switch to Web CTF mode
- `/help` - Show help message
- `/clear` - Clear the screen
- `/exit` or `/quit` - Exit the program

## Project Structure

```
Agentic AI 2.0/
├── agents/              # Agent implementations
│   ├── base.py         # Base ReAct agent
│   ├── gemini_agent.py # Gemini implementation
│   └── ollama_agent.py # Ollama implementation
├── tools/              # Tool registry and implementations
│   ├── registry.py     # Tool registration system
│   ├── base64_tool.py  # Base64 encoding/decoding
│   └── web_request.py  # Web content fetching
├── modes/              # Mode configurations
│   ├── base.py         # Base mode class
│   └── web_ctf.py      # Web CTF mode
├── ui/                 # User interface
│   ├── display.py      # Rich-based display manager
│   └── commands.py     # Command parser
├── logs/               # Session logs (auto-generated)
├── config.py           # Configuration management
├── logger.py           # Session logging
├── errors.py           # Custom exceptions
├── main.py             # Main entry point
├── requirements.txt    # Python dependencies
└── .env               # Environment configuration
```

## Available Tools

### Base64 Tools
- `base64_decode` - Decode base64 encoded strings
- `base64_encode` - Encode strings to base64

### Web Tools
- `web_request` - Fetch content from URLs with custom headers and methods

## Example Session

```
> /agent gemini
✓ Gemini agent selected

> /mode web-ctf
✓ Web CTF mode selected

> Analyze http://example-ctf.com/challenge and find the flag

╭─ 🧠 Agent Thinking (Step 1) ─────────────────────────╮
│ I need to first fetch the webpage to see what        │
│ information is available and look for any clues.     │
╰──────────────────────────────────────────────────────╯

╭─ 🔧 Tool Execution (Step 1) ────────────────────────╮
│ Tool: web_request                              │
│                                                       │
│ Input:                                                │
│ {                                                     │
│   "url": "http://example-ctf.com/challenge"         │
│ }                                                     │
╰──────────────────────────────────────────────────────╯

╭─ 📊 Tool Response (Step 1) ─────────────────────────╮
│ ✓ web_request                                  │
│                                                       │
│ Status Code: 200                                      │
│ Content: ...                                          │
╰──────────────────────────────────────────────────────╯
```

## Logging

All sessions are automatically logged to the `logs/` directory:
- `session_YYYYMMDD_HHMMSS.log` - Human-readable text log
- `session_YYYYMMDD_HHMMSS.json` - Machine-readable JSON log with full interaction history

## Configuration

Environment variables in `.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google Gemini API key | - |
| `OLLAMA_BASE_URL` | Ollama server URL | `http://localhost:11434` |
| `OLLAMA_MODEL` | Ollama model to use | `llama3.1` |
| `CONSOLE_WIDTH` | Terminal width | `auto` |
| `LOG_LEVEL` | Logging level | `INFO` |

## Troubleshooting

### Gemini API Issues
- Verify your API key is correct
- Check you have API quota remaining
- Ensure stable internet connection

### Ollama Issues
- Verify Ollama is running: `ollama list`
- Ensure model is pulled: `ollama pull llama3.1`
- Check Ollama is accessible: `curl http://localhost:11434/api/tags`

### Terminal Display Issues
- Ensure terminal width is at least 80 characters
- Try setting `CONSOLE_WIDTH` in `.env` to a fixed value

## Security Note

This tool is designed for **authorized security testing and CTF challenges only**. Always ensure you have permission before testing any system.

## Anti-Hallucination Features

This system includes several measures to prevent the agent from "hallucinating" (making up tool outputs):

1. **Structured Prompts**: Engineered prompts in `prompts/` explicitly enforce single-action responses
2. **Stop Sequences**: LLM generation stops at keywords like "Thought:" to prevent multi-step planning
3. **Token Limits**: Responses limited to 512 tokens to keep agent focused
4. **Low Temperature**: Set to 0.3 for consistent, focused behavior
5. **Strict Parsing**: Only the FIRST action is extracted from responses
6. **Error Feedback**: Agent receives corrections when format is wrong

See `prompts/ANTI_HALLUCINATION.md` for detailed explanation.

## Troubleshooting Common Issues

### Agent Generates Multiple Steps at Once
- ✅ **Fixed** with stop sequences and token limits
- Check that `temperature=0.3` and `max_output_tokens=512`
- Review `prompts/system_prompts.py` for format instructions

### Tool Execution Not Showing
- ✅ **Fixed** with improved display formatting
- Tool name, parameters, and output are now clearly labeled
- Each execution shows in bordered yellow/green panels

### Agent Makes Up Tool Results
- ✅ **Fixed** with strict ReAct loop enforcement  
- Parser only extracts FIRST action
- Agent must wait for real tool output before continuing

## License

This project is for educational and authorized security testing purposes only.
