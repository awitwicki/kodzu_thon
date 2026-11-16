"""Layout for the "chats and shared members" graph, drawn as inline SVG (no JavaScript).

A member of a chat is a user who has sent at least one recorded message there. Chats are
placed by a small force simulation in which chats sharing more members pull closer; the
people shared by one particular set of chats are then drawn as a cluster of dots at the
middle of those chats, with one line from the cluster to each of them. Everything is
deterministic: the same archive always draws the same picture."""

import math
from collections import defaultdict
from itertools import combinations

WIDTH, HEIGHT = 1000, 680
PADDING = 80
MAX_DOTS = 400  # people drawn; the counts and the table always cover everyone
DOT_SPACING = 7.5
GOLDEN_ANGLE = math.pi * (3 - math.sqrt(5))
ITERATIONS = 300


def _layout_chats(chat_ids: list[int], weights: dict[tuple[int, int], int]) -> dict[int, tuple]:
    """Fruchterman-Reingold in the unit square, then stretched to the padded canvas."""
    n = len(chat_ids)
    if n == 1:
        return {chat_ids[0]: (WIDTH / 2, HEIGHT / 2)}
    pos = {
        cid: [0.5 + 0.4 * math.cos(2 * math.pi * i / n), 0.5 + 0.4 * math.sin(2 * math.pi * i / n)]
        for i, cid in enumerate(chat_ids)
    }
    k = 1 / math.sqrt(n)
    top = math.log1p(max(weights.values(), default=1))
    for step in range(ITERATIONS):
        move = {cid: [0.0, 0.0] for cid in chat_ids}
        for a, b in combinations(chat_ids, 2):
            dx, dy = pos[a][0] - pos[b][0], pos[a][1] - pos[b][1]
            dist = math.hypot(dx, dy) or 1e-6
            force = k * k / dist  # every pair repels
            weight = weights.get((a, b))
            if weight:  # chats sharing members attract, more strongly the more they share
                force -= dist * dist / k * (0.3 + 0.7 * math.log1p(weight) / top)
            move[a][0] += dx / dist * force
            move[a][1] += dy / dist * force
            move[b][0] -= dx / dist * force
            move[b][1] -= dy / dist * force
        heat = 0.1 * (1 - step / ITERATIONS)
        for cid in chat_ids:
            mx = move[cid][0] + (0.5 - pos[cid][0]) * 0.05  # mild pull to the centre keeps
            my = move[cid][1] + (0.5 - pos[cid][1]) * 0.05  # unconnected groups on canvas
            length = math.hypot(mx, my) or 1e-6
            pos[cid][0] += mx / length * min(length, heat)
            pos[cid][1] += my / length * min(length, heat)
    xs, ys = [p[0] for p in pos.values()], [p[1] for p in pos.values()]
    span_x, span_y = (max(xs) - min(xs)) or 1, (max(ys) - min(ys)) or 1
    return {
        cid: (
            PADDING + (x - min(xs)) / span_x * (WIDTH - 2 * PADDING),
            PADDING + (y - min(ys)) / span_y * (HEIGHT - 2 * PADDING),
        )
        for cid, (x, y) in pos.items()
    }


def shared_members_graph(rows: list[dict], chats: dict[int, str]) -> dict:
    """`rows`: one {user_id, chat_id, name} per (person, chat they wrote in), only for people
    seen in two or more chats (Repository.shared_members). `chats`: id -> title."""
    user_chats: dict[int, set[int]] = defaultdict(set)
    names: dict[int, str] = {}
    for row in rows:
        user_chats[row["user_id"]].add(row["chat_id"])
        names[row["user_id"]] = row["name"]
    user_chats = {u: c for u, c in user_chats.items() if len(c) >= 2}

    weights: dict[tuple[int, int], int] = defaultdict(int)
    shared_per_chat: dict[int, int] = defaultdict(int)
    for members_chats in user_chats.values():
        for cid in members_chats:
            shared_per_chat[cid] += 1
        for pair in combinations(sorted(members_chats), 2):
            weights[pair] += 1
    chat_ids = sorted(shared_per_chat)
    title = {cid: chats.get(cid) or str(cid) for cid in chat_ids}
    pos = _layout_chats(chat_ids, weights) if chat_ids else {}

    # People sharing exactly the same set of chats form one cluster. Most-connected first,
    # so when the archive has more people than MAX_DOTS the ones left out are the least so.
    groups: dict[frozenset, list[int]] = defaultdict(list)
    for user_id in sorted(user_chats, key=lambda u: (-len(user_chats[u]), u)):
        groups[frozenset(user_chats[user_id])].append(user_id)
    clusters, dots, budget = [], [], MAX_DOTS
    for members_chats, members in groups.items():
        cx = sum(pos[c][0] for c in members_chats) / len(members_chats)
        cy = sum(pos[c][1] for c in members_chats) / len(members_chats)
        chat_names = ", ".join(sorted(title[c] for c in members_chats))
        clusters.append(
            {
                "lines": [
                    {"x1": round(cx, 1), "y1": round(cy, 1), "x2": round(pos[c][0], 1),
                     "y2": round(pos[c][1], 1)}
                    for c in sorted(members_chats)
                ],
                "width": round(1 + math.log2(len(members)), 1),
                "label": f"{len(members)} shared by {chat_names}",
            }
        )
        for i, user_id in enumerate(members[: max(budget, 0)]):
            radius, angle = DOT_SPACING * math.sqrt(i), i * GOLDEN_ANGLE
            dots.append(
                {
                    "user_id": user_id,
                    "x": round(cx + radius * math.cos(angle), 1),
                    "y": round(cy + radius * math.sin(angle), 1),
                    "label": f"{names[user_id]}: {chat_names}",
                }
            )
        budget -= len(members)

    biggest = max(shared_per_chat.values(), default=1)
    return {
        "width": WIDTH,
        "height": HEIGHT,
        "chats": [
            {
                "id": cid,
                "title": title[cid],
                "short_title": title[cid] if len(title[cid]) <= 24 else title[cid][:23] + "…",
                "x": round(pos[cid][0], 1),
                "y": round(pos[cid][1], 1),
                "r": round(9 + 13 * math.sqrt(shared_per_chat[cid] / biggest), 1),
                "shared": shared_per_chat[cid],
            }
            for cid in chat_ids
        ],
        "clusters": clusters,
        "dots": dots,
        "people": len(user_chats),
        "people_drawn": len(dots),
        "pairs": [
            {"a": a, "a_title": title[a], "b": b, "b_title": title[b], "shared": n}
            for (a, b), n in sorted(weights.items(), key=lambda item: (-item[1], item[0]))
        ],
    }
