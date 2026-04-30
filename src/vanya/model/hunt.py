class Hunt:
    def __init__(self, area_id, name, max_hit):
        self.area_id = area_id
        self.name = name
        self.max_hit = max_hit

    def __repr__(self):
        return f"Hunt(area_id={self.area_id}, name='{self.name}', max_hit={self.max_hit})"
