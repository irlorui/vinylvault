"""Unit tests for GameScore and GameWildcard."""

from src.backend.score import GameScore, GameWildcard


def test_initial_value():
    score = GameScore()
    assert score.value == 0


def test_reset_sets_value_to_one():
    score = GameScore()
    score.reset()
    assert score.value == 1


def test_add_increments():
    score = GameScore()
    score.add()
    assert score.value == 1
    score.add()
    assert score.value == 2


def test_reset_after_add():
    score = GameScore()
    score.add()
    score.add()
    score.reset()
    assert score.value == 1


# ─── GameWildcard ─────────────────────────────────────────────────────────────


def test_wildcard_initial_value():
    wc = GameWildcard()
    assert wc.value == 0


def test_wildcard_add_increments():
    wc = GameWildcard()
    wc.add()
    assert wc.value == 1
    wc.add()
    assert wc.value == 2


def test_wildcard_use_decrements():
    wc = GameWildcard()
    wc.add()
    wc.use()
    assert wc.value == 0


def test_wildcard_use_raises_when_empty():
    wc = GameWildcard()
    try:
        wc.use()
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_wildcard_reset_clears_value():
    wc = GameWildcard()
    wc.add()
    wc.add()
    wc.reset()
    assert wc.value == 0
