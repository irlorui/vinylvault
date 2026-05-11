"""Game score, wildcard, and multi-player state tracking."""


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


class Player:
    """State for one player: name, score, and wildcards."""

    def __init__(self, name: str) -> None:
        """Create a player with the given name and zeroed counters."""
        self.name = name
        self.score = GameScore()
        self.wildcards = GameWildcard()


class GamePlayers:
    """Manages all players and whose turn it is."""

    def __init__(self) -> None:
        """Start with a single default player."""
        self.players: list[Player] = [Player("Player 1")]
        self.current_index: int = 0

    @property
    def current(self) -> Player:
        """Return the player whose turn it is."""
        return self.players[self.current_index]

    def init(self, names: list[str]) -> None:
        """Set up fresh players with the given names and reset all counters."""
        if not names:
            raise ValueError("At least one player name is required.")
        self.players = [Player(name) for name in names]
        self.current_index = 0
        for p in self.players:
            p.score.reset()
            p.wildcards.reset()

    def next_turn(self) -> None:
        """Advance to the next player, wrapping around."""
        self.current_index = (self.current_index + 1) % len(self.players)
