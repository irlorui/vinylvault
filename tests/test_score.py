"""Unit tests for GameScore."""

from src.backend.score import WIN_SCORE, GameScore


def test_win_score_constant():
    assert WIN_SCORE == 4


def test_initial_value():
    score = GameScore()
    assert score.value == 0


def test_initial_not_won():
    score = GameScore()
    assert score.won is False


def test_reset_sets_value_to_one():
    score = GameScore()
    score.reset()
    assert score.value == 1


def test_reset_not_won():
    score = GameScore()
    score.reset()
    assert score.won is False


def test_add_increments():
    score = GameScore()
    score.add()
    assert score.value == 1
    score.add()
    assert score.value == 2


def test_won_false_below_threshold():
    score = GameScore()
    for _ in range(WIN_SCORE - 1):
        score.add()
    assert score.won is False


def test_won_true_at_threshold():
    score = GameScore()
    for _ in range(WIN_SCORE):
        score.add()
    assert score.won is True


def test_won_true_above_threshold():
    score = GameScore()
    for _ in range(WIN_SCORE + 2):
        score.add()
    assert score.won is True


def test_reset_after_add():
    score = GameScore()
    score.add()
    score.add()
    score.reset()
    assert score.value == 1
    assert score.won is False
