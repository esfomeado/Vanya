from dataclasses import dataclass
from typing import Optional


@dataclass
class InventoryItem:
    name: str
    slot: str
    quantity: int
    equippable: bool
    equipped: bool
    stats: Optional[str]
    image: str

    def __repr__(self):
        return f"{self.name} ({self.quantity})"
