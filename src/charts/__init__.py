"""Chart registry: id → module exposing build(tables, mode) -> go.Figure."""
from src.charts import c01_every_race, c02_title_races, c03_teammate_gap

REGISTRY = {
    "c01": c01_every_race,
    "c02": c02_title_races,
    "c03": c03_teammate_gap,
}
