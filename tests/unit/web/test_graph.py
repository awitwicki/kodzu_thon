from kodzu_thon.web.graph import HEIGHT, MAX_DOTS, WIDTH, shared_members_graph


def rows(*memberships):
    return [
        {"user_id": user, "chat_id": chat, "name": f"U{user}"}
        for user, chats in memberships
        for chat in chats
    ]


CHATS = {-1: "Alpha", -2: "Beta", -3: None, -4: "Unrelated"}


def test_counts_pairs_and_per_chat_shared_members():
    graph = shared_members_graph(
        rows((1, [-1, -2]), (2, [-1, -2]), (3, [-1, -2, -3]), (4, [-1])), CHATS
    )
    assert graph["people"] == 3 and graph["people_drawn"] == 3  # user 4 is in one chat only
    assert {c["id"]: c["shared"] for c in graph["chats"]} == {-1: 3, -2: 3, -3: 1}
    assert [(p["a"], p["b"], p["shared"]) for p in graph["pairs"]] == [
        (-2, -1, 3),
        (-3, -2, 1),
        (-3, -1, 1),
    ]
    assert graph["pairs"][1]["a_title"] == "-3"  # an untitled chat falls back to its id
    labels = {c["label"] for c in graph["clusters"]}
    assert labels == {"2 shared by Alpha, Beta", "1 shared by -3, Alpha, Beta"}
    assert {d["label"] for d in graph["dots"]} >= {"U1: Alpha, Beta", "U3: -3, Alpha, Beta"}


def test_layout_is_deterministic_and_inside_the_canvas():
    data = rows(*[(u, [-1, -2] if u % 2 else [-2, -3, -4]) for u in range(1, 60)])
    first, second = shared_members_graph(data, CHATS), shared_members_graph(data, CHATS)
    assert first == second
    for chat in first["chats"]:
        assert chat["r"] < chat["x"] < WIDTH - chat["r"]
        assert chat["r"] < chat["y"] < HEIGHT - chat["r"]
    assert len({(c["x"], c["y"]) for c in first["chats"]}) == 4
    assert len({(d["x"], d["y"]) for d in first["dots"]}) == len(first["dots"])


def test_dots_are_capped_but_counts_cover_everyone():
    data = rows(*[(u, [-1, -2]) for u in range(1, MAX_DOTS + 51)], (9999, [-1, -2, -3]))
    graph = shared_members_graph(data, CHATS)
    assert graph["people"] == MAX_DOTS + 51 and graph["people_drawn"] == MAX_DOTS
    assert graph["dots"][0]["user_id"] == 9999  # the most connected person is drawn first
    assert graph["pairs"][0]["shared"] == MAX_DOTS + 51


def test_empty_and_single_pair():
    empty = shared_members_graph([], CHATS)
    assert empty["chats"] == [] and empty["dots"] == [] and empty["pairs"] == []
    one = shared_members_graph(rows((1, [-1, -2])), CHATS)
    assert len(one["chats"]) == 2 and one["chats"][0]["x"] != one["chats"][1]["x"]
