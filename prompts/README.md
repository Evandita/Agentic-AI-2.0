# Prompts Directory

This directory contains highly structured and engineered prompts for the Red Teaming AI agents.

## Files

### `system_prompts.py`
Contains all system prompts used by the agents:

- **`REACT_FORMAT_INSTRUCTIONS`**: Critical instructions that enforce single-action responses and prevent hallucination
- **`BASE_SYSTEM_PROMPT`**: Base template for general agent behavior
- **`WEB_CTF_SYSTEM_PROMPT`**: Specialized prompt for Web CTF challenges with security expertise

## Key Features

### 1. Anti-Hallucination Design
The prompts are specifically engineered to prevent the agent from:
- Planning multiple steps ahead
- Making up tool outputs
- Generating "thought chains" without executing tools
- Skipping the observation phase

### 2. Strict Format Enforcement
- Forces ONE action per response
- Mandates exact JSON format for parameters
- Includes stop sequences to prevent multi-step planning
- Provides clear examples of correct vs incorrect format

### 3. Context-Rich Instructions
The Web CTF prompt includes:
- Common vulnerability patterns
- CTF-specific strategies
- Analysis techniques
- Flag format patterns
- Step-by-step methodology

## Usage

```python
from prompts import get_web_ctf_system_prompt

# Get prompt with tools description
tools_desc = "- tool1: description\n- tool2: description"
prompt = get_web_ctf_system_prompt(tools_desc)
```

## Prompt Engineering Principles

1. **Be Explicit**: Don't assume the LLM knows what to do
2. **Use Examples**: Show correct and incorrect formats
3. **Set Boundaries**: Use stop sequences and token limits
4. **Provide Context**: Give domain-specific knowledge
5. **Enforce Structure**: Make format requirements unambiguous

## Customization

To add a new mode:
1. Create a new system prompt constant
2. Include `{tools_description}` placeholder
3. Add ReAct format instructions
4. Provide domain-specific expertise
5. Create getter function

Example:
```python
FORENSICS_MODE_PROMPT = """
You are a digital forensics expert...

{format_instructions}

Available Tools:
{tools_description}

## Forensics Methodology:
...
"""

def get_forensics_system_prompt(tools_description: str) -> str:
    return FORENSICS_MODE_PROMPT.format(
        format_instructions=REACT_FORMAT_INSTRUCTIONS,
        tools_description=tools_description
    )
```
