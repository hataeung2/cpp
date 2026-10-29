"""Per-key span aggregates for the Timings view (spec 070-06 §2.3, design record §2.4).

The runner feeds every `span` line of a run's trace file here instead of sending it to the page
one by one. Memory depends on the number of keys, not on the number of spans: each key keeps
exact count, total, min and max, and a uniform sample of at most `sample_size` durations over
the whole run (reservoir sampling, Algorithm R) for p50, p95 and the distribution bars.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

SAMPLE_SIZE = 1024
BINS = 20

Key = tuple[str, int, str, str]  # (file, line, label, meter): the key of 020-06 spanStats()


@dataclass
class _Entry:
    count: int = 0
    total: int = 0
    min: int = 0
    max: int = 0
    sample: list[int] = field(default_factory=list)


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def percentile(ordered: list[int], p: float) -> int:
    """Nearest-rank percentile of a sorted, non-empty list."""
    rank = max(1, math.ceil(p / 100 * len(ordered)))
    return ordered[rank - 1]


def histogram(ordered: list[int], bins: int) -> dict:
    """Counts of a sorted, non-empty sample in `bins` buckets on a log(x + 1) scale from min to max."""
    lo, hi = ordered[0], ordered[-1]
    if lo == hi:
        return {"loNs": lo, "hiNs": hi, "bins": [len(ordered)]}
    a, b = math.log(lo + 1), math.log(hi + 1)
    counts = [0] * bins
    for value in ordered:
        counts[min(bins - 1, int((math.log(value + 1) - a) / (b - a) * bins))] += 1
    return {"loNs": lo, "hiNs": hi, "bins": counts}


class SpanAggregator:
    def __init__(self, sample_size: int = SAMPLE_SIZE, bins: int = BINS, seed: int | None = None) -> None:
        self.sample_size = sample_size
        self.bins = bins
        self.random = random.Random(seed)
        self.entries: dict[Key, _Entry] = {}
        self.changed: set[Key] = set()
        self.lines = 0  # spans accepted

    def add(self, obj: dict) -> bool:
        """Add one parsed `span` line; False (and nothing changes) when a field is missing or wrong."""
        file, line, label, meter, dur = (obj.get(k) for k in ("file", "line", "label", "meter", "durNs"))
        if not (isinstance(file, str) and _is_int(line) and line >= 0 and isinstance(label, str)
                and isinstance(meter, str) and _is_int(dur) and dur >= 0):
            return False
        key = (file, line, label, meter)
        entry = self.entries.get(key)
        if entry is None:
            entry = self.entries[key] = _Entry(min=dur, max=dur)
        entry.count += 1
        entry.total += dur
        entry.min = min(entry.min, dur)
        entry.max = max(entry.max, dur)
        if len(entry.sample) < self.sample_size:
            entry.sample.append(dur)
        else:  # Algorithm R: the n-th value replaces a random slot with probability size / n
            slot = self.random.randrange(entry.count)
            if slot < self.sample_size:
                entry.sample[slot] = dur
        self.changed.add(key)
        self.lines += 1
        return True

    def drain(self) -> list[dict]:
        """Rows of the keys changed since the last drain (cumulative values)."""
        rows = [self._row(key) for key in sorted(self.changed)]
        self.changed.clear()
        return rows

    def snapshot(self) -> list[dict]:
        """Rows of every key."""
        return [self._row(key) for key in sorted(self.entries)]

    def _row(self, key: Key) -> dict:
        entry = self.entries[key]
        ordered = sorted(entry.sample)
        file, line, label, meter = key
        return {"file": file, "line": line, "label": label, "meter": meter,
                "count": entry.count, "totalNs": entry.total, "minNs": entry.min, "maxNs": entry.max,
                "p50Ns": percentile(ordered, 50), "p95Ns": percentile(ordered, 95),
                "hist": histogram(ordered, self.bins)}
