from dataclasses import dataclass


@dataclass(slots=True)
class MarketListing:
    listing_id: int
    name: str
    price: int
    meta: str
    stats: str
    csrf_token: str

    def __repr__(self):
        return f"{self.name} @ {self.price:,}g"
