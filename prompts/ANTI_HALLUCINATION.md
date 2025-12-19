# Anti-Hallucination Guide

## The Problem

When using LLMs as agents with tools, they often "hallucinate" by:
1. Planning multiple steps ahead without executing tools
2. Making up tool outputs instead of waiting for real results
3. Generating thought chains like "First I'll do X, then Y, then Z"
4. Not stopping after one action

**Example of Hallucination:**
```
Thought: I need to fetch the page
Action: fetch_web_content
Action Input: {"url": "http://example.com"}

Thought: The response will contain...  [HALLUCINATING!]
Action: base64_decode
Action Input: {"encoded_string": "..."}  [HASN'T RECEIVED RESPONSE YET!]
```

## The Solution

### 1. Structured Prompts (`prompts/system_prompts.py`)

**REACT_FORMAT_INSTRUCTIONS** explicitly tells the agent:
- Generate ONLY ONE action at a time
- STOP after each action
- WAIT for observations
- Use exact format

```python
REACT_FORMAT_INSTRUCTIONS = """CRITICAL INSTRUCTIONS - YOU MUST FOLLOW THESE EXACTLY:

1. You MUST respond with ONLY ONE action at a time
2. After each action, STOP and wait for the observation
3. Use this EXACT format (nothing before or after):

Thought: [One clear sentence]
Action: [ONE tool name]
Action Input: {"param": "value"}
"""
```

### 2. Stop Sequences

Both Gemini and Ollama agents use stop sequences:

```python
stop_sequences=['\nThought:', '\n\nThought:', 'Observation:']
```

This forces the LLM to stop generating text when it tries to create a second "Thought:" or when it tries to imagine an "Observation:".

### 3. Token Limits

Reduced from 2048 to 512 tokens:

```python
max_output_tokens=512  # Shorter responses prevent multi-step planning
```

### 4. Lower Temperature

Reduced from 0.7 to 0.3:

```python
temperature=0.3  # More focused, less creative/hallucinating
```

### 5. Improved Response Parsing

The parser now:
- Extracts only the FIRST Thought/Action/Input
- Ignores any subsequent steps
- Returns errors for malformed responses

```python
def _parse_response(self, response: str) -> Dict[str, Any]:
    # Find the FIRST Thought/Action/Action Input sequence only
    # This prevents the agent from planning multiple steps ahead
    ...
```

### 6. Error Feedback Loop

If parsing fails, the agent gets feedback:

```python
if 'error' in parsed:
    self.display.print_error(
        parsed['error'],
        "Please use the correct format..."
    )
    # Give agent another chance
    conversation_history.append({
        "role": "user", 
        "content": f"Error: {parsed['error']}. Please provide a valid action."
    })
```

## Testing Anti-Hallucination

### Good Behavior ✅
```
Thought: I need to fetch the webpage to see its content
Action: fetch_web_content
Action Input: {"url": "http://example.com"}

[AGENT STOPS AND WAITS FOR TOOL EXECUTION]
```

### Bad Behavior ❌ (Prevented)
```
Thought: I'll fetch the page
Action: fetch_web_content
Action Input: {"url": "http://example.com"}

Thought: Then I'll decode the base64  [STOPPED BY STOP SEQUENCE]
```

## Verification

Run a test challenge and check:

1. **Agent displays ONE action per iteration**
   - ✅ Each cycle shows: Thinking → Tool Call → Tool Response
   - ❌ Shows multiple thought/action pairs at once

2. **Tool outputs are REAL**
   - ✅ Tool Response shows actual HTTP content, decoded strings, etc.
   - ❌ Tool Response is "made up" or generic

3. **Agent waits for observations**
   - ✅ Next thought references previous tool output
   - ❌ Next thought ignores previous output

4. **No duplicate actions**
   - ✅ Agent tries different approaches if one fails
   - ❌ Agent repeats same failed action

## Configuration Checklist

- [ ] Using prompts from `prompts/system_prompts.py`
- [ ] Stop sequences configured in agent
- [ ] Token limit set to 512 or less
- [ ] Temperature at 0.3 or lower
- [ ] Response parser extracts only FIRST action
- [ ] Error feedback loop in place
- [ ] Clear tool execution display

## If Hallucination Still Occurs

1. **Check the model**: Some models are more prone to hallucination
   - llama3.1 works well
   - qwen2.5-coder works well
   - Smaller models (<7B) may struggle

2. **Adjust temperature**: Try 0.1 or 0.2 for even more focus

3. **Add more stop sequences**: Include patterns the model uses

4. **Simplify prompts**: Remove examples that might confuse

5. **Use stricter parsing**: Reject any response with multiple actions

## Further Reading

- [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629)
- [LangChain ReAct Agent Documentation](https://python.langchain.com/docs/modules/agents/agent_types/react)
