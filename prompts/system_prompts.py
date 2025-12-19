"""
System prompts for Red Teaming AI agents
"""

from prompts.base import (
    get_react_format_instructions,
    get_base_system_prompt,
    REACT_FORMAT_INSTRUCTIONS,
    BASE_SYSTEM_PROMPT
)
from prompts.modes.web_ctf import (
    get_web_ctf_system_prompt,
    WEB_CTF_SYSTEM_PROMPT
)
