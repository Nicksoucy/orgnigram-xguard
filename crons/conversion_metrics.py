"""
Conversion Metrics — Calculates stats for daily/weekly reports.
"""

import logging
from datetime import datetime, timedelta

from kb_config import sb_get, sb_count

log = logging.getLogger("conversion_metrics")


def get_conversion_stats(days=30):
    """Get conversion statistics for the last N days."""
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    conversions = sb_get(
        f"conversions?enrollment_date=gte.{since}"
        f"&select=*&order=enrollment_date.desc"
    )

    if not conversions:
        return {
            "total": 0, "period_days": days,
            "call_to_conversion_rate": 0, "avg_days": 0,
            "by_pipeline": {}, "by_agent": {}, "recent": [],
        }

    total = len(conversions)

    # Avg days to conversion
    days_list = [c["days_to_conversion"] for c in conversions if c.get("days_to_conversion") is not None]
    avg_days = round(sum(days_list) / len(days_list), 1) if days_list else 0

    # By pipeline
    by_pipeline = {}
    for c in conversions:
        p = c.get("pipeline_source", "?")
        if p not in by_pipeline:
            by_pipeline[p] = {"count": 0, "value": 0}
        by_pipeline[p]["count"] += 1
        by_pipeline[p]["value"] += c.get("monetary_value") or 0

    # By agent
    by_agent = {}
    for c in conversions:
        a = c.get("attributed_agent") or "non_attribue"
        if a not in by_agent:
            by_agent[a] = {"count": 0, "scores": []}
        by_agent[a]["count"] += 1
        if c.get("avg_call_score"):
            by_agent[a]["scores"].append(c["avg_call_score"])
    for a in by_agent:
        s = by_agent[a]["scores"]
        by_agent[a]["avg_score"] = round(sum(s) / len(s), 1) if s else 0

    # Call-to-conversion rate
    inscription_callers = sb_count("sac_contacts", f"primary_category=eq.inscription&first_call_date=gte.{since}")
    converted_callers = len([c for c in conversions if c.get("total_calls_before", 0) > 0])
    rate = round(converted_callers / max(inscription_callers, 1) * 100, 1)

    # Score vs conversion
    high_score = [c for c in conversions if (c.get("avg_call_score") or 0) >= 6]
    low_score = [c for c in conversions if (c.get("avg_call_score") or 0) > 0 and (c.get("avg_call_score") or 0) < 4]

    # Recent
    recent = []
    for c in conversions[:5]:
        recent.append({
            "name": c.get("contact_name", "?")[:25],
            "program": c.get("program_type", "?"),
            "agent": c.get("attributed_agent", "?"),
            "days": c.get("days_to_conversion"),
            "date": (c.get("enrollment_date") or "")[:10],
            "score": c.get("avg_call_score"),
        })

    return {
        "total": total,
        "period_days": days,
        "call_to_conversion_rate": rate,
        "avg_days": avg_days,
        "by_pipeline": by_pipeline,
        "by_agent": by_agent,
        "high_score_converts": len(high_score),
        "low_score_converts": len(low_score),
        "recent": recent,
    }


AGENT_NAMES = {"L3": "Hamza", "s2": "Lilia", "s3": "Sekou", "v1": "Heidys", "t11": "Domingos"}
PIPELINE_LABELS = {"heidys_gardiennage": "Gardiennage", "domingos_drone": "Drone", "sac_direct": "SAC Direct"}


def conversion_html_section(stats):
    """Generate HTML section for the daily email report."""
    if not stats or stats.get("total", 0) == 0:
        return ""

    total = stats["total"]
    rate = stats["call_to_conversion_rate"]
    avg_days = stats["avg_days"]

    rate_color = "#2E7D32" if rate >= 20 else "#E65100" if rate >= 10 else "#C62828"

    # Pipeline breakdown
    pipeline_html = ""
    for p, data in sorted(stats.get("by_pipeline", {}).items(), key=lambda x: -x[1]["count"]):
        label = PIPELINE_LABELS.get(p, p)
        val = f"${data['value']:,.0f}" if data["value"] > 0 else ""
        pipeline_html += f'<span style="display:inline-block;background:#E8EAF6;color:#283593;padding:2px 8px;border-radius:10px;font-size:11px;margin:2px;">{label}: {data["count"]} {val}</span> '

    # Recent conversions
    recent_rows = ""
    for r in stats.get("recent", []):
        agent = AGENT_NAMES.get(r["agent"], r["agent"] or "?")
        days_str = f'{r["days"]}j' if r["days"] is not None else "?"
        score_str = f'{r["score"]}/10' if r["score"] else "-"
        recent_rows += f"""
        <tr style="border-bottom:1px solid #eee;">
          <td style="padding:4px;font-size:11px;font-weight:bold;">{r['name']}</td>
          <td style="padding:4px;font-size:11px;text-align:center;">{r['program']}</td>
          <td style="padding:4px;font-size:11px;text-align:center;">{agent}</td>
          <td style="padding:4px;font-size:11px;text-align:center;">{days_str}</td>
          <td style="padding:4px;font-size:11px;text-align:center;">{score_str}</td>
          <td style="padding:4px;font-size:11px;color:#777;">{r['date']}</td>
        </tr>"""

    html = f"""
<!-- CONVERSIONS SECTION -->
<h2 style="color:#2E7D32;border-bottom:2px solid #2E7D32;padding-bottom:5px;font-size:15px;">Conversions ({stats['period_days']} derniers jours)</h2>

<table style="width:100%;border-collapse:collapse;margin:0 0 10px;">
  <tr>
    <td style="padding:10px;text-align:center;background:#E8F5E9;border:1px solid #C8E6C9;">
      <div style="font-size:22px;font-weight:bold;color:#2E7D32;">{total}</div>
      <div style="font-size:10px;color:#777;">Inscriptions</div>
    </td>
    <td style="padding:10px;text-align:center;background:#E3F2FD;border:1px solid #BBDEFB;">
      <div style="font-size:22px;font-weight:bold;color:{rate_color};">{rate}%</div>
      <div style="font-size:10px;color:#777;">Taux conversion</div>
    </td>
    <td style="padding:10px;text-align:center;background:#FFF8E1;border:1px solid #FFF176;">
      <div style="font-size:22px;font-weight:bold;color:#F57F17;">{avg_days}</div>
      <div style="font-size:10px;color:#777;">Jours moy.</div>
    </td>
    <td style="padding:10px;text-align:center;background:#E8F5E9;border:1px solid #C8E6C9;">
      <div style="font-size:22px;font-weight:bold;color:#2E7D32;">{stats.get('high_score_converts', 0)}</div>
      <div style="font-size:10px;color:#777;">Score 6+ converti</div>
    </td>
  </tr>
</table>

<div style="margin:5px 0 10px;">{pipeline_html}</div>

{f'''<table style="width:100%;border-collapse:collapse;margin:8px 0 15px;font-size:12px;">
  <tr style="background:#E8F5E9;"><th style="padding:5px;text-align:left;">Contact</th><th style="padding:5px;">Programme</th><th style="padding:5px;">Agent</th><th style="padding:5px;">Delai</th><th style="padding:5px;">Score</th><th style="padding:5px;">Date</th></tr>
  {recent_rows}
</table>''' if recent_rows else ''}
"""
    return html


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    stats = get_conversion_stats(days)
    print(f"Conversions ({days} days): {stats['total']}")
    print(f"  Rate: {stats['call_to_conversion_rate']}%")
    print(f"  Avg days: {stats['avg_days']}")
    print(f"  By pipeline: {stats['by_pipeline']}")
    print(f"  By agent: {stats['by_agent']}")
    for r in stats.get("recent", []):
        print(f"  {r['date']} | {r['name']:20s} | {r['program']:12s} | {r['agent']:5s} | {r.get('days','?')} days | score {r.get('score','?')}")
