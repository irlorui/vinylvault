"""Game score management."""

WIN_SCORE = 4


class GameScore:
    """Tracks points for a single game session."""

    def __init__(self) -> None:
        """Initialize with a zero score."""
        self.value: int = 0

    def reset(self) -> None:
        """Reset to 1 — the reference card is the first point."""
        self.value = 1

    def add(self) -> None:
        """Add one point for a correct card placement."""
        self.value += 1

    @property
    def won(self) -> bool:
        """Return True when the player has reached the win threshold."""
        return self.value >= WIN_SCORE
