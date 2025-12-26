from dataclasses import dataclass


@dataclass(slots=True)
class Boss:
    boss_id: int
    stage: int
    name: str
    life: int
    xp: int
    required_level: int
    boosted: bool

    def __repr__(self):
        return f"{self.name} ({self.life})"
