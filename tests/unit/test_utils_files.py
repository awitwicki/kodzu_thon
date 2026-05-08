from kodzu_thon.utils.files import safe_remove


def test_safe_remove_deletes_existing_file(tmp_path):
    f = tmp_path / "x.txt"
    f.write_text("x")
    safe_remove(str(f))
    assert not f.exists()


def test_safe_remove_swallows_missing_file():
    safe_remove("/definitely/missing/path.txt")  # no exception
