"""Web CTF mode configuration"""

from modes.base import Mode
from prompts.system_prompts import WEB_CTF_SYSTEM_PROMPT


def get_web_ctf_mode() -> Mode:
    """Get the Web CTF mode configuration with structured prompts"""
    # Use the raw template string - it will be formatted by the agent
    mode = Mode(
        name="web-ctf",
        display_name="Web CTF",
        description="Specialized mode for Web Capture The Flag challenges", 
        system_context=WEB_CTF_SYSTEM_PROMPT  # Raw template with {tools_description} and {format_instructions}
    )
    return mode


# Module-level instance
WEB_CTF_MODE = get_web_ctf_mode()
