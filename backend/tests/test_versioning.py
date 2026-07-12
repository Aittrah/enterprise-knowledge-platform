from pathlib import Path

from app.ingestion.versioning import VersionTracker


def test_first_ingestion_is_version_one(tmp_path: Path):
    tracker = VersionTracker(tmp_path / "versions.json")
    info = tracker.register("policy.txt", "aaa")
    assert info.version == 1
    assert not info.is_new_version
    assert not info.is_duplicate


def test_identical_content_is_duplicate(tmp_path: Path):
    tracker = VersionTracker(tmp_path / "versions.json")
    tracker.register("policy.txt", "aaa")
    info = tracker.register("policy.txt", "aaa")
    assert info.is_duplicate
    assert info.version == 1
    assert tracker.latest_version("policy.txt") == 1


def test_changed_content_creates_next_version(tmp_path: Path):
    tracker = VersionTracker(tmp_path / "versions.json")
    tracker.register("policy.txt", "aaa")
    info = tracker.register("policy.txt", "bbb")
    assert info.version == 2
    assert info.is_new_version
    assert not info.is_duplicate
    assert [v["version"] for v in tracker.history("policy.txt")] == [1, 2]


def test_versions_persist_across_instances(tmp_path: Path):
    store = tmp_path / "versions.json"
    VersionTracker(store).register("policy.txt", "aaa")
    reloaded = VersionTracker(store)
    assert reloaded.latest_version("policy.txt") == 1
    assert reloaded.register("policy.txt", "bbb").version == 2


def test_keys_are_independent(tmp_path: Path):
    tracker = VersionTracker(tmp_path / "versions.json")
    tracker.register("a.txt", "aaa")
    info = tracker.register("b.txt", "aaa")
    assert info.version == 1
