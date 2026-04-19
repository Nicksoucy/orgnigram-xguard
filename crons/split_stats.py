"""Split stats morning vs afternoon for a given date."""
import sys
sys.path.insert(0, "C:\\Users\\user\\crons")
from smart_stats import fetch_all_raw, parse_call
from collections import defaultdict

date_str = sys.argv[1] if len(sys.argv) > 1 else "2026-04-02"

raw = fetch_all_raw(date_str)
parsed = [parse_call(c) for c in raw]
parsed = [p for p in parsed if p["dt"] is not None and 8 <= p["hour"] < 18]

morning = [p for p in parsed if 8 <= p["hour"] < 12]
afternoon = [p for p in parsed if 12 <= p["hour"] < 18]

for label, calls in [("8h-12h (MATIN — Hamza seul)", morning), ("12h-18h (PM — Hamza + Lilia)", afternoon)]:
    total = len(calls)
    in_total = sum(1 for p in calls if p["is_inbound"])
    in_ans = sum(1 for p in calls if p["is_answered"])
    in_miss = sum(1 for p in calls if p["is_missed"])
    out_total = sum(1 for p in calls if p["is_outbound"])
    rate = round(in_ans / in_total * 100) if in_total > 0 else 0

    print(f"{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    print(f"  Total: {total} | Entrants: {in_total} | Sortants: {out_total}")
    print(f"  Repondus: {in_ans} | Manques: {in_miss} | Taux: {rate}%")
    print()

    for acct in ["academie", "formateur"]:
        ac = [p for p in calls if p["account"] == acct]
        ain = sum(1 for p in ac if p["is_inbound"])
        aans = sum(1 for p in ac if p["is_answered"])
        amiss = sum(1 for p in ac if p["is_missed"])
        aout = sum(1 for p in ac if p["is_outbound"])
        ar = round(aans / ain * 100) if ain > 0 else 0
        print(f"  {acct:12s}: {len(ac):3d} total | IN:{ain:3d} (rep:{aans:2d} miss:{amiss:3d}) | OUT:{aout:2d} | Taux:{ar}%")

    # Dedup for this window
    by_num = defaultdict(list)
    for p in calls:
        if p["is_inbound"] and p["contact_number"] and len(p["contact_number"]) >= 7:
            by_num[p["contact_number"]].append(p)

    dupes = 0
    for num, cs in by_num.items():
        missed = [c for c in cs if c["is_missed"]]
        answered = [c for c in cs if c["is_answered"]]
        if answered:
            dupes += len(missed)
        elif len(missed) > 1:
            dupes += len(missed) - 1

    real_missed = in_miss - dupes

    # Agent busy
    busy_windows = []
    for p in calls:
        if p["duration_s"] > 0 and p["dt"] and p["end_dt"]:
            busy_windows.append((p["dt"], p["end_dt"], p["account"]))

    justified = 0
    for p in calls:
        if not p["is_missed"]: continue
        for start, end, acct in busy_windows:
            if acct == p["account"] and start <= p["dt"] <= end:
                justified += 1
                break

    vrais = real_missed - justified
    if vrais < 0: vrais = 0
    real_rate = round(in_ans / (in_ans + vrais) * 100) if (in_ans + vrais) > 0 else 0

    print()
    print(f"  Doublons retires:     {dupes}")
    print(f"  Agent occupe:         {justified}")
    print(f"  VRAIS manques:        {vrais}")
    print(f"  Taux REEL:            {real_rate}%")
    print()
