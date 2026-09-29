# 33 → 1 → 3 — Max Verstappen's Formula 1 Career in Data

A visualization-first data story about one Formula 1 career, told through his three car numbers:
**#33** (the rise), **#1** (the reign) and **#3** (the 2026 reset).

> 🚧 Work in progress. The data pipeline and coverage audit are done; charts and the case-study page are next.

This is a descriptive, editorial project: prose and charts, not a dashboard or a model. (For forward-looking ML
on F1, see my separate F1 Race Predictor.)

## Reproduce

```bash
make setup   # Python 3.12 venv + pinned dependencies
make data    # fetch (cached) Jolpica data, build data/processed/*.parquet
make test    # stat-rule unit tests
```

## Data

* [Jolpica-F1](https://github.com/jolpica/jolpica-f1) (Ergast-compatible API): results, qualifying, standings, 2015 → today.
* [FastF1](https://github.com/theOehrly/Fast-F1): live-timing laps, stints and telemetry, **2018 onwards only**.

Unofficial project, not associated in any way with the Formula 1 companies. F1, FORMULA ONE and related marks are
trademarks of Formula One Licensing B.V.

## Author

Sarvesh Kant · [sarveshkantonline.com](https://sarveshkantonline.com) · [GitHub](https://github.com/sarveshkant2003-afk)

License: MIT (code).
