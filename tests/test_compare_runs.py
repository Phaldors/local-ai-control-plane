import json

from scripts.compare_runs import latest_runs, sign_test


def test_sign_test_known_values():
    assert sign_test(0, 0) == 1.0
    assert sign_test(5, 5) == 1.0
    assert abs(sign_test(0, 6) - 2 / 64) < 1e-12  # two-sided, 6 discordant pairs all one way
    assert abs(sign_test(1, 9) - 2 * (1 + 10) / 1024) < 1e-12


def write_run(root, name, max_tokens, suite="extraction", runtime="ollama", model="m:1"):
    directory = root / name
    directory.mkdir()
    meta = {
        "runtime": runtime,
        "model": model,
        "suite": suite,
        "think": False,
        "max_tokens": max_tokens,
        "guard": False,
        "case_count": 1,
    }
    (directory / "report.json").write_text(json.dumps({"meta": meta, "tasks": {}}))


def test_runs_with_a_different_max_tokens_are_never_compared(tmp_path):
    write_run(tmp_path, "20261001T000000Z-a", 1024)
    write_run(tmp_path, "20261002T000000Z-a", 40)  # the deliberate regression demo, newer
    found = latest_runs(tmp_path, "ollama", "m_1")
    assert list(found.values()) == [tmp_path / "20261001T000000Z-a"]
