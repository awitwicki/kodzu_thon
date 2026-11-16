"""Route modules. Each exposes `router`; `ROUTERS` is what create_app mounts.
Later tasks import their module here and append its router."""

from kodzu_thon.web.routes import chats, graph, health, login, media, messages, search, users

ROUTERS = [
    health.router,
    login.router,
    chats.router,
    messages.router,
    users.router,
    graph.router,
    search.router,
    media.router,
]
