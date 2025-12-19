"""Initialize modes package"""

from modes.base import Mode
from modes.web_ctf import get_web_ctf_mode, WEB_CTF_MODE


# Available modes registry
AVAILABLE_MODES = {
    'web-ctf': WEB_CTF_MODE,
    'web_ctf': WEB_CTF_MODE,
    'webctf': WEB_CTF_MODE,
}


def get_mode(mode_name: str) -> Mode:
    """Get mode by name"""
    mode_name = mode_name.lower().replace(' ', '-')
    if mode_name in AVAILABLE_MODES:
        return AVAILABLE_MODES[mode_name]
    return None


def list_modes() -> list[str]:
    """List available mode names"""
    return ['web-ctf']


__all__ = ['Mode', 'get_mode', 'list_modes', 'get_web_ctf_mode']
