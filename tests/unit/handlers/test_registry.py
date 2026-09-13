import re
from unittest.mock import MagicMock

from kodzu_thon.handlers import register_all


def test_register_all_collects_compiled_command_patterns(fake_ctx):
    fake_ctx.command_patterns = []
    fake_ctx.help_lines = []

    register_all(MagicMock(), fake_ctx)

    patterns = fake_ctx.command_patterns
    assert patterns and all(isinstance(p, re.Pattern) for p in patterns)
    texts = [
        "ai hello",
        "ppo",
        "🦔",
        "loading",
        "!h",
        "хня",
        "!m 20 m",
        "!lk 👍 3",
        "scan",
        "scans",
        "scraps",
        "summ",
        "tr",
        "TR",
        "!t",
        "!a hi",
        "!v hi",
        "year",
    ]
    for text in texts:
        assert any(p.match(text) for p in patterns), text
    assert not any(p.match("just chatting") for p in patterns)
    assert len(fake_ctx.help_lines) >= 18  # every command module also contributes HELP
