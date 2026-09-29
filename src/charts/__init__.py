"""Chart registry: id → module exposing build(tables, mode) -> go.Figure."""
from src.charts import c01_every_race, c02_title_races, c03_teammate_gap, c04_grid_to_flag, c08_signature_race, c10_greats

REGISTRY = {
    "c01": c01_every_race,
    "c02": c02_title_races,
    "c03": c03_teammate_gap,
    "c04": c04_grid_to_flag,
    "c08": c08_signature_race,
    "c10": c10_greats,
}
