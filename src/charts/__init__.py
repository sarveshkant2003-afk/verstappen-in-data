"""Chart registry: id → module exposing build(tables, mode) -> go.Figure."""
from src.charts import c01_every_race

REGISTRY = {
    "c01": c01_every_race,
}
