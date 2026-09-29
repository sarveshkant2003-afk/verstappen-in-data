"""Stat-rule tests on tiny hand-made data (CLAUDE.md §12)."""
import math

import numpy as np
import pandas as pd
import pytest

from src import stats


def test_sprint_results_excluded_from_gp_counts():
    df = pd.DataFrame({
        "session": ["gp", "sprint", "gp", "sprint", "gp"],
        "position_text": ["1", "1", "3", "2", "R"],
        "status_cat": ["Finished", "Finished", "Finished", "Finished", "DNF-incident"],
    })
    assert stats.gp_counts(df) == {"starts": 3, "wins": 1, "podiums": 2}


def test_dns_is_not_a_start():
    df = pd.DataFrame({"session": ["gp", "gp"], "position_text": ["W", "4"], "status_cat": ["DNS", "Finished"]})
    assert stats.gp_counts(df)["starts"] == 1


def test_status_strings_map_to_right_category():
    smap = pd.DataFrame({"status": ["Finished", "+1 Lap", "Engine", "Collision", "Disqualified", "Did not start"],
                         "category": ["Finished", "Lapped", "DNF-mechanical", "DNF-incident", "DSQ", "DNS"]})
    out = stats.map_status(pd.Series(["Engine", "+1 Lap", "Collision", "Did not start"]), smap)
    assert list(out) == ["DNF-mechanical", "Lapped", "DNF-incident", "DNS"]


def test_unmapped_status_raises():
    smap = pd.DataFrame({"status": ["Finished"], "category": ["Finished"]})
    with pytest.raises(ValueError, match="Unmapped"):
        stats.map_status(pd.Series(["Alien abduction"]), smap)


def test_classified_uses_position_text():
    assert stats.is_classified("7")
    assert not any(stats.is_classified(t) for t in ["R", "D", "W", "N", "E", "F"])


def test_positions_gained_skips_non_classified():
    assert stats.positions_gained(grid=10, finish=3, classified=True, field_size=20) == 7
    assert math.isnan(stats.positions_gained(grid=10, finish=18, classified=False, field_size=20))


def test_pit_lane_start_is_back_of_grid():
    assert stats.effective_grid(0, 20) == 20
    assert stats.positions_gained(grid=0, finish=6, classified=True, field_size=20) == 14


def test_rescoring_p1_25_p11_0():
    assert stats.rescore(1, True) == 25
    assert stats.rescore(10, True) == 1
    assert stats.rescore(11, True) == 0
    assert stats.rescore(1, False) == 0


def test_quali_gap_uses_last_common_session():
    # Max reached Q3, teammate out in Q2 → compare Q2 times.
    mine = {"q1": 80.0, "q2": 79.5, "q3": 79.0}
    theirs = {"q1": 80.2, "q2": 79.9, "q3": math.nan}
    session, a, b = stats.last_common_session(mine, theirs)
    assert (session, a, b) == ("q2", 79.5, 79.9)
    assert stats.quali_gap_pct(a, b) == pytest.approx(100 * -0.4 / 79.5)


def test_quali_gap_no_common_session():
    assert stats.last_common_session({"q1": math.nan}, {"q1": 80.0})[0] is None


def test_laptime_parsing_roundtrip():
    assert stats.laptime_to_seconds("1:23.456") == pytest.approx(83.456)
    assert math.isnan(stats.laptime_to_seconds(""))
    assert stats.format_laptime(83.456) == "1:23.456"


def test_clean_lap_filter_drops_lap1_pit_and_sc_laps():
    t = pd.Timedelta
    laps = pd.DataFrame({
        "LapNumber":  [1, 2, 3, 4, 5, 6],
        "LapTime":    [t(seconds=95)] + [t(seconds=90)] * 5,
        "PitInTime":  [pd.NaT, pd.NaT, t(seconds=1), pd.NaT, pd.NaT, pd.NaT],
        "PitOutTime": [pd.NaT, pd.NaT, pd.NaT, t(seconds=2), pd.NaT, pd.NaT],
        "TrackStatus": ["1", "1", "1", "1", "14", "12"],
        "IsAccurate": [True] * 6,
        "Deleted":    [False] * 6,
    })
    # lap 1 out, lap 3 in-lap, lap 4 out-lap, lap 5 SC; lap 6 (yellow) stays
    assert list(stats.clean_laps(laps)["LapNumber"]) == [2, 6]


def test_gap_seconds_needs_same_lap():
    assert stats.gap_seconds(5_000_000, 5_012_345, 57, 57) == pytest.approx(12.345)
    assert math.isnan(stats.gap_seconds(5_000_000, math.nan, 57, 56))


def test_distance_interpolation_returns_common_grid():
    grid = stats.distance_grid(100, step_m=25)
    out = stats.interpolate_to_distance(np.array([0, 50, 50, 100]), np.array([100, 200, 200, 300]), grid)
    assert list(grid) == [0, 25, 50, 75]
    assert list(out) == [100, 150, 200, 250]


def test_bootstrap_ci_brackets_median():
    med, lo, hi = stats.bootstrap_median_ci(np.arange(1, 101, dtype=float))
    assert lo <= med <= hi
