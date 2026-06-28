"""Analytics aggregation.

Click *capture* happens on the write path (``Repository.record_click``). This
module owns the *read* side: turning raw click rows into the aggregates the API
exposes. Keeping aggregation separate from capture means analytics queries can
later be moved to a read replica or a warehouse without changing the hot path.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .storage import Repository


@dataclass
class AnalyticsSummary:
    short_code: str
    total_clicks: int
    last_clicked: str | None
    clicks_by_day: dict[str, int] = field(default_factory=dict)
    top_referrers: list[tuple[str, int]] = field(default_factory=list)


class Analytics:
    def __init__(self, repository: Repository) -> None:
        self._repo = repository

    def summary(self, short_code: str, *, top_n: int = 5) -> AnalyticsSummary:
        clicks = self._repo.get_clicks(short_code)
        if not clicks:
            return AnalyticsSummary(short_code, 0, None)

        by_day: Counter[str] = Counter()
        referrers: Counter[str] = Counter()
        for click in clicks:
            day = click.clicked_at[:10]  # ISO date prefix (YYYY-MM-DD)
            by_day[day] += 1
            if click.referrer:
                referrers[click.referrer] += 1

        return AnalyticsSummary(
            short_code=short_code,
            total_clicks=len(clicks),
            last_clicked=clicks[-1].clicked_at,
            clicks_by_day=dict(sorted(by_day.items())),
            top_referrers=referrers.most_common(top_n),
        )
