from dataclasses import dataclass


@dataclass(slots=True)
class Boss:
    boss_id: int
    stage: int
    name: str
    life: int
    xp: int
    required_level: int

    def __repr__(self):
        return f"{self.name} ({self.life})"


@dataclass(slots=True)
class NexusBoss:
    boss_id: int
    name: str
    image: str
    current_life: int
    max_life: int
    life_percent: float
    is_alive: bool
    respawn_at: int

    def __repr__(self):
        return f"{self.name} ({self.life_percent:.2f}%)"
