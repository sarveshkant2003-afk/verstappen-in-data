"""Chart registry: id → module exposing build(tables, mode) -> go.Figure.

c14_lap_one.py exists but is not registered: EDA showed lap-1 gains are mostly an
artefact of grid position (from pole the best is 0), so it was cut from the story.
C05/C06 are added once their telemetry sessions are downloaded.
"""
from src.charts import (c01_every_race, c02_title_races, c03_teammate_gap, c04_grid_to_flag, c07_dominance, c08_signature_race, c09_reset,
                        c10_greats, c11_season_fingerprints, c12_world_map, c13_dnf_anatomy)

REGISTRY = {
    "c01": c01_every_race,
    "c02": c02_title_races,
    "c03": c03_teammate_gap,
    "c04": c04_grid_to_flag,
    "c07": c07_dominance,
    "c08": c08_signature_race,
    "c09": c09_reset,
    "c10": c10_greats,
    "c11": c11_season_fingerprints,
    "c12": c12_world_map,
    "c13": c13_dnf_anatomy,
}
