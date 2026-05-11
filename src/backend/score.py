"""Game score management."""


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


class GameWildcard:
    """Tracks available wildcards for one game session."""

    def __init__(self) -> None:
        """Initialize with zero wildcards."""
        self.value: int = 0

    def add(self) -> None:
        """Award one wildcard."""
        self.value += 1

    def use(self) -> None:
        """Spend one wildcard; raises ValueError if none available."""
        if self.value <= 0:
            raise ValueError("No wildcards available.")
        self.value -= 1

    def reset(self) -> None:
        """Reset wildcards to zero."""
        self.value = 0
