from dataclasses import dataclass

@dataclass(slots=True)
class Visage:
    name: str
    bonus: str
    image_url: str
    is_equipped: bool
    filename: str

    def __repr__(self):
        status = "[Equipped]" if self.is_equipped else ""
        return f"{self.name} ({self.bonus}) {status}".strip()
