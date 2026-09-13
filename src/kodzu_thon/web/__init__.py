"""kodzuthon.web — read-only web viewer for the message archive.

Imports only `kodzu_thon.db` (schema version) and its own modules; never the
userbot's handlers/services, so its Docker image needs only the `web` extras."""
