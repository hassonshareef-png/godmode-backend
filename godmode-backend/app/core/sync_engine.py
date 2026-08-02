from dataclasses import dataclass
from typing import List, Tuple, Dict, Any, Optional


# ---------- Core data structures ----------

@dataclass
class Draw:
    """
    Represents a single Pick 3 draw as three digits.
    Example: '117' -> Draw(d1=1, d2=1, d3=7)
    """
    d1: int
    d2: int
    d3: int

    @classmethod
    def from_str(cls, s: str) -> "Draw":
        s = s.strip()
        if len(s) != 3 or not s.isdigit():
            raise ValueError(f"Invalid draw string: {s}")
        return cls(int(s[0]), int(s[1]), int(s[2]))

    def to_tuple(self) -> Tuple[int, int, int]:
        return (self.d1, self.d2, self.d3)


def parse_draws(raw_list: List[str]) -> List[Draw]:
    """
    Convert a list of 3-digit strings into a list of Draw objects.
    """
    return [Draw.from_str(s) for s in raw_list]


def diff_draws(prev: Draw, curr: Draw) -> Tuple[int, int, int]:
    """
    Compute digit-wise differences: curr - prev for each digit.
    Example: prev=051, curr=162 -> (1, 1, 1)
    """
    return (
        curr.d1 - prev.d1,
        curr.d2 - prev.d2,
        curr.d3 - prev.d3,
    )


# ---------- Event structures ----------

@dataclass
class SyncEvent:
    """
    Generic full-sync event: all digits move by the same delta.
    """
    index: int              # index of curr draw in the list
    prev_index: int         # index of prev draw
    prev_draw: Draw
    curr_draw: Draw
    delta: Tuple[int, int, int]


# ---------- Detection logic ----------

def detect_sync_events(
    draws: List[Draw],
    allowed_deltas: Optional[List[int]] = None,
) -> List[SyncEvent]:
    """
    Detect full synchronization events where all three digits move
    by the same delta and that delta is in allowed_deltas.

    allowed_deltas: list of integers (e.g. [1, -1, 2, 3, 4])
    If None, any equal delta is accepted.
    """
    events: List[SyncEvent] = []

    if len(draws) < 2:
        return events

    for i in range(1, len(draws)):
        prev = draws[i - 1]
        curr = draws[i]
        d = diff_draws(prev, curr)

        # all digits move by same amount
        if d[0] == d[1] == d[2]:
            delta_val = d[0]
            if allowed_deltas is None or delta_val in allowed_deltas:
                events.append(
                    SyncEvent(
                        index=i,
                        prev_index=i - 1,
                        prev_draw=prev,
                        curr_draw=curr,
                        delta=d,
                    )
                )

    return events


def detect_grand_slams(draws: List[Draw]) -> List[SyncEvent]:
    """
    Detect Grand Slam events: +1 +1 +1.
    """
    return detect_sync_events(draws, allowed_deltas=[1])


def detect_full_drops(draws: List[Draw]) -> List[SyncEvent]:
    """
    Detect Full Drop events: -1 -1 -1.
    """
    return detect_sync_events(draws, allowed_deltas=[-1])


# ---------- Summaries ----------

def summarize_state(
    name: str,
    draws: List[Draw],
    allowed_deltas: Optional[List[int]] = None,
) -> Dict[str, Any]:
    """
    Build a structured summary for a state:
    - total draws
    - number of sync events (for given allowed_deltas)
    - average gap between sync events
    - list of events (as dicts)
    """
    sync_events = detect_sync_events(draws, allowed_deltas)

    total_draws = len(draws)
    num_events = len(sync_events)

    # compute gaps between consecutive sync events
    gaps: List[int] = []
    for i in range(1, num_events):
        prev_idx = sync_events[i - 1].index
        curr_idx = sync_events[i].index
        gaps.append(curr_idx - prev_idx)

    avg_gap: Optional[float] = None
    if gaps:
        avg_gap = sum(gaps) / len(gaps)

    events_serialized = []
    for ev in sync_events:
        events_serialized.append(
            {
                "index": ev.index,
                "prev_index": ev.prev_index,
                "prev_draw": ev.prev_draw.to_tuple(),
                "curr_draw": ev.curr_draw.to_tuple(),
                "delta": ev.delta,
            }
        )

    summary = {
        "state": name,
        "total_draws": total_draws,
        "num_sync_events": num_events,
        "average_gap_between_sync_events": avg_gap,
        "events": events_serialized,
    }

    return summary


def summarize_grand_slams(name: str, draws: List[Draw]) -> Dict[str, Any]:
    """
    Summary focused only on +1 +1 +1 Grand Slams.
    """
    slams = detect_grand_slams(draws)

    gaps: List[int] = []
    for i in range(1, len(slams)):
        gaps.append(slams[i].index - slams[i - 1].index)

    avg_gap = sum(gaps) / len(gaps) if gaps else None

    return {
        "state": name,
        "total_draws": len(draws),
        "num_grand_slams": len(slams),
        "average_gap": avg_gap,
        "events": [
            {
                "index": ev.index,
                "prev_index": ev.prev_index,
                "prev_draw": ev.prev_draw.to_tuple(),
                "curr_draw": ev.curr_draw.to_tuple(),
                "delta": ev.delta,
            }
            for ev in slams
        ],
    }


def summarize_full_drops(name: str, draws: List[Draw]) -> Dict[str, Any]:
    """
    Summary focused only on -1 -1 -1 Full Drops.
    """
    drops = detect_full_drops(draws)

    gaps: List[int] = []
    for i in range(1, len(drops)):
        gaps.append(drops[i].index - drops[i - 1].index)

    avg_gap = sum(gaps) / len(gaps) if gaps else None

    return {
        "state": name,
        "total_draws": len(draws),
        "num_full_drops": len(drops),
        "average_gap": avg_gap,
        "events": [
            {
                "index": ev.index,
                "prev_index": ev.prev_index,
                "prev_draw": ev.prev_draw.to_tuple(),
                "curr_draw": ev.curr_draw.to_tuple(),
                "delta": ev.delta,
            }
            for ev in drops
        ],
    }


# ---------- Example wiring (you can adapt/remove in backend) ----------

if __name__ == "__main__":
    # Example: New Mexico style sequence with a Grand Slam
    nm_raw = [
        "051", "162", "243", "354", "465", "576"
    ]
    nm_draws = parse_draws(nm_raw)

    print("=== NM Grand Slams ===")
    print(summarize_grand_slams("New Mexico", nm_draws))

    print("\n=== NM Full Drops (none expected here) ===")
    print(summarize_full_drops("New Mexico", nm_draws))

    # Example: generic sync summary for +1, -1, +2, +3, +4
    allowed = [1, -1, 2, 3, 4]
    print("\n=== NM Sync Summary (multi-delta) ===")
    print(summarize_state("New Mexico", nm_draws, allowed_deltas=allowed))
