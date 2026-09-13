"""Handler registry. Each handler module registers itself by adding an import
plus an entry in _MODULES. Populated incrementally as handler tasks land."""

import re

from kodzu_thon.handlers import (
    ai,
    air_alarm,
    animations,
    autoresponder,
    bg_voice,
    memes,
    moderation,
    reactions,
    recorder,
    scan,
    summarize,
    translate,
    voice_synth,
    year,
)
from kodzu_thon.handlers import help as help_module
from kodzu_thon.handlers import typing as typing_module

# Order matters: bg_voice has no pattern and matches all outgoing — register last.
_MODULES = [
    help_module,
    ai,
    summarize,
    reactions,
    scan,
    air_alarm,
    translate,
    typing_module,
    year,
    moderation,
    animations,
    voice_synth,
    memes,
    autoresponder,
    recorder,
    bg_voice,
]


def register_all(client, ctx) -> None:
    for module in _MODULES:
        if hasattr(module, "HELP"):
            ctx.help_lines.extend(module.HELP)
        for pattern in getattr(module, "COMMAND_PATTERNS", []):
            ctx.command_patterns.append(
                pattern if isinstance(pattern, re.Pattern) else re.compile(pattern)
            )
        module.register(client, ctx)
