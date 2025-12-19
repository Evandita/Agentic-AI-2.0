"""Initialize prompts package"""

from prompts.system_prompts import (
    get_react_format_instructions,
    get_base_system_prompt,
    get_web_ctf_system_prompt,
    REACT_FORMAT_INSTRUCTIONS,
    BASE_SYSTEM_PROMPT,
    WEB_CTF_SYSTEM_PROMPT
)

__all__ = [
    'get_react_format_instructions',
    'get_base_system_prompt',
    'get_web_ctf_system_prompt',
    'REACT_FORMAT_INSTRUCTIONS',
    'BASE_SYSTEM_PROMPT',
    'WEB_CTF_SYSTEM_PROMPT'
]
