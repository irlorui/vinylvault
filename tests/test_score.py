"""Unit tests for GameScore, GameWildcard, Player, and GamePlayers."""

import pytest

from src.backend.score import GamePlayers, GameScore, GameWildcard, Player

# ─── GameScore ────────────────────────────────────────────────────────────────


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


def test_game_score_reset_idempotent():
    score = GameScore()
    score.reset()
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
    with pytest.raises(ValueError):
        wc.use()


def test_wildcard_reset_clears_value():
    wc = GameWildcard()
    wc.add()
    wc.add()
    wc.reset()
    assert wc.value == 0


def test_wildcard_sequential_exhaustion():
    wc = GameWildcard()
    wc.add()
    wc.add()
    wc.use()
    wc.use()
    assert wc.value == 0
    with pytest.raises(ValueError):
        wc.use()


# ─── Player ───────────────────────────────────────────────────────────────────


def test_player_initial_state():
    p = Player("Alice")
    assert p.name == "Alice"
    assert p.score.value == 0
    assert p.wildcards.value == 0


def test_player_score_and_wildcard_independent():
    p = Player("Bob")
    p.score.add()
    p.wildcards.add()
    assert p.score.value == 1
    assert p.wildcards.value == 1


# ─── GamePlayers ──────────────────────────────────────────────────────────────


def test_game_players_default():
    gp = GamePlayers()
    assert len(gp.players) == 1
    assert gp.players[0].name == "Player 1"
    assert gp.current_index == 0


def test_game_players_current():
    gp = GamePlayers()
    assert gp.current.name == "Player 1"


def test_game_players_init_single():
    gp = GamePlayers()
    gp.init(["Alice"])
    assert len(gp.players) == 1
    assert gp.players[0].name == "Alice"
    assert gp.current_index == 0


def test_game_players_init_multi():
    gp = GamePlayers()
    gp.init(["Alice", "Bob", "Carol"])
    assert len(gp.players) == 3
    assert [p.name for p in gp.players] == ["Alice", "Bob", "Carol"]


def test_game_players_init_resets_scores():
    gp = GamePlayers()
    gp.init(["Alice", "Bob"])
    gp.current.score.add()
    gp.init(["Alice", "Bob"])
    assert gp.current.score.value == 1  # reset() sets to 1


def test_game_players_init_resets_wildcards():
    gp = GamePlayers()
    gp.init(["Alice"])
    gp.current.wildcards.add()
    gp.init(["Alice"])
    assert gp.current.wildcards.value == 0


def test_game_players_next_turn_advances():
    gp = GamePlayers()
    gp.init(["Alice", "Bob"])
    assert gp.current_index == 0
    gp.next_turn()
    assert gp.current_index == 1
    assert gp.current.name == "Bob"


def test_game_players_next_turn_wraps():
    gp = GamePlayers()
    gp.init(["Alice", "Bob"])
    gp.next_turn()
    gp.next_turn()
    assert gp.current_index == 0
    assert gp.current.name == "Alice"


def test_game_players_init_rejects_empty_names():
    gp = GamePlayers()
    with pytest.raises(ValueError):
        gp.init([])


def test_game_players_next_turn_single_player_stays_at_zero():
    gp = GamePlayers()
    gp.init(["Alice"])
    gp.next_turn()
    assert gp.current_index == 0
    assert gp.current.name == "Alice"


def test_game_players_init_clears_previous_players():
    gp = GamePlayers()
    gp.init(["Alice", "Bob", "Carol"])
    gp.init(["Dave"])
    assert len(gp.players) == 1
    assert gp.players[0].name == "Dave"
    assert gp.current_index == 0


def test_game_players_scores_independent():
    gp = GamePlayers()
    gp.init(["Alice", "Bob"])  # both start at score=1 (reset)
    gp.current.score.add()  # Alice: 1 → 2
    gp.next_turn()
    assert gp.current.score.value == 1  # Bob still at 1
    gp.players[0].score.add()  # Alice: 2 → 3
    assert gp.players[0].score.value == 3
    assert gp.players[1].score.value == 1
