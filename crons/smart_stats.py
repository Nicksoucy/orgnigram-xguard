"""
Smart SAC Stats v2 — Hamza's 39-indicator framework.
Fetches ALL raw calls from JustCall and computes:
- Raw stats (brut)
- Deduped stats (same client calling multiple times)
- Real stats (excluding calls missed while agent was on another call)
- Callback tracking (taux de rappel)
- 39 indicators across 7 dimensions
- Weighted score /100
"""

import json
import logging
import re
import time
from collections import defaultdict
from datetime import datetime, timedelta

import requests

from phone_utils import normalize_number

JUSTCALL_API_URL = "https://api.justcall.io/v1/calls/query"
JUSTCALL_API_KEY = "daf60d953694336f07c84c74205eb311dd85c996"
JUSTCALL_API_SECRET = "20612f8fcb80ef33845cbdc226bc8174853c82dd"

JUSTCALL_ACCOUNTS = {
    "academie": "301418",
    "formateur": "302145",
}

log = logging.getLogger("smart_stats")


def fetch_all_raw(date_str):
    """Fetch ALL raw calls for a date from both accounts, with deep pagination."""
    headers = {"Accept": "application/json", "Authorization": f"{JUSTCALL_API_KEY}:{JUSTCALL_API_SECRET}"}
    all_calls = []

    for acct_name, agent_id in JUSTCALL_ACCOUNTS.items():
        page = 1
        while page <= 15:
            try:
                body = {"from_date": date_str, "to_date": date_str,
                        "agent_id": agent_id, "per_page": 100, "page": page}
                resp = requests.post(JUSTCALL_API_URL, json=body, headers=headers, timeout=(10, 30))
                resp.raise_for_status()
                calls = resp.json().get("data", [])
                if not calls:
                    break

                on_date = [c for c in calls if (c.get("time", "") or "").startswith(date_str)]
                for c in on_date:
                    c["_account"] = acct_name
                all_calls.extend(on_date)

                # Stop if we went past the target date
                before = [c for c in calls if (c.get("time", "") or "") < date_str]
                if before:
                    break
                if len(calls) < 100:
                    break
                page += 1
                time.sleep(0.5)
            except Exception as e:
                log.warning("JustCall fetch error (%s p%d): %s", acct_name, page, e)
                break

    return all_calls


def parse_call(c):
    """Parse a raw JustCall call into a standardized dict."""
    time_str = c.get("time", "")
    dur = int(c.get("duration", 0) or 0)
    is_in = c.get("direction") == "1"

    # Parse datetime
    dt = None
    try:
        dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
    except Exception:
        pass

    # missed_call_type: '1'=No Answer (agent libre), '2'=Busy, '3'=Abandoned (client raccroche)
    mct = str(c.get("missed_call_type") or "")

    return {
        "id": c.get("id"),
        "time": time_str,
        "dt": dt,
        "hour": dt.hour if dt else 0,
        "duration_s": dur,
        "is_inbound": is_in,
        "is_answered": is_in and dur > 0,
        "is_missed": is_in and dur == 0,
        "is_outbound": not is_in,
        "out_connected": not is_in and dur > 0,
        "contact_number": (c.get("contact_number") or "").strip(),
        "contact_name": c.get("contact_name", ""),
        "notes": (c.get("notes") or "").strip(),
        "missed_call_type": mct,  # '1'=no answer, '2'=busy, '3'=abandoned
        "account": c.get("_account", ""),
        "end_dt": (dt + timedelta(seconds=dur)) if dt and dur > 0 else None,
    }


# ===== Conformite patterns =====
SIGNATURE_RE = re.compile(r'\b(hm|hamza|lilia|lilya|sk|sekou|s[eé]coud[eé])\b', re.IGNORECASE)
DEJA_TRAITE_RE = re.compile(r'(d[eé]j[aà]\s*trait[eé]|d[eé]j[aà]\s*fait|already\s*done)', re.IGNORECASE)


def compute_callback_stats(work_hours, dedup_removed_ids, justified_ids):
    """Compute callback (rappel) tracking — Dimension 3 (x25% weight).

    For each missed-net call (after dedup + busy exclusion), search for an
    outbound call to the same contact_number with duration > 10s after the miss.
    """
    # Step 1: missed-net calls
    missed_net = [
        p for p in work_hours
        if p["is_missed"]
        and p["id"] not in dedup_removed_ids
        and p["id"] not in justified_ids
        and p["contact_number"]
        and len(p["contact_number"]) >= 7
    ]

    if not missed_net:
        return {
            "taux_rappel_corrige": 100.0,
            "rappeles_meme_shift": 0,
            "rappeles_shift_suivant": 0,
            "non_rappeles": [],
            "non_rappeles_count": 0,
            "manques_non_rappeles_fin_journee": 0,
            "delai_moyen_sec": 0,
            "delai_moyen_min": 0.0,
            "taux_rappel_heure": 100.0,
            "total_missed_net": 0,
            "total_rappeles": 0,
            "rappeles_detail": [],
        }

    # Step 2: outbound calls indexed by normalized number
    outbound_by_num = defaultdict(list)
    for p in work_hours:
        if p["is_outbound"] and p["duration_s"] > 10 and p["contact_number"]:
            norm = normalize_number(p["contact_number"])
            if norm:
                outbound_by_num[norm].append(p)

    # Also check answered inbound (client may have called back and been answered)
    answered_by_num = defaultdict(list)
    for p in work_hours:
        if p["is_answered"] and p["contact_number"]:
            norm = normalize_number(p["contact_number"])
            if norm:
                answered_by_num[norm].append(p)

    for num in outbound_by_num:
        outbound_by_num[num].sort(key=lambda x: x["dt"])
    for num in answered_by_num:
        answered_by_num[num].sort(key=lambda x: x["dt"])

    # Step 3: match each miss to a callback
    rappeles = []
    non_rappeles = []
    delays = []
    rappel_same_shift = 0
    rappel_within_hour = 0

    for miss in missed_net:
        norm_num = normalize_number(miss["contact_number"])
        if not norm_num:
            non_rappeles.append({
                "number": miss["contact_number"],
                "name": miss["contact_name"],
                "miss_time": miss["time"],
                "attempts": 0,
            })
            continue

        # Check outbound callbacks
        found_callback = None
        callbacks = outbound_by_num.get(norm_num, [])
        for cb in callbacks:
            if cb["dt"] > miss["dt"]:
                found_callback = cb
                break

        # Also check if client called again and WAS answered
        if not found_callback:
            answered = answered_by_num.get(norm_num, [])
            for ans in answered:
                if ans["dt"] > miss["dt"]:
                    found_callback = ans
                    break

        if found_callback:
            delay_sec = (found_callback["dt"] - miss["dt"]).total_seconds()
            delays.append(delay_sec)

            # Same shift = same calendar day before 18h
            if found_callback["dt"].date() == miss["dt"].date():
                rappel_same_shift += 1

            if delay_sec <= 3600:
                rappel_within_hour += 1

            rappeles.append({
                "number": miss["contact_number"],
                "name": miss["contact_name"],
                "miss_time": miss["time"],
                "callback_time": found_callback["time"],
                "delay_min": round(delay_sec / 60),
            })
        else:
            # Count failed outbound attempts (duration <= 10s)
            short_attempts = len([
                c for c in outbound_by_num.get(norm_num, [])
                if c["duration_s"] <= 10 and c["dt"] > miss["dt"]
            ])
            non_rappeles.append({
                "number": miss["contact_number"],
                "name": miss["contact_name"],
                "miss_time": miss["time"],
                "attempts": short_attempts,
            })

    total_net = len(missed_net)
    rappel_next_shift = len(rappeles) - rappel_same_shift

    return {
        "taux_rappel_corrige": round(len(rappeles) / total_net * 100, 1) if total_net > 0 else 100.0,
        "rappeles_meme_shift": rappel_same_shift,
        "rappeles_shift_suivant": max(0, rappel_next_shift),
        "non_rappeles": non_rappeles,
        "non_rappeles_count": len(non_rappeles),
        "manques_non_rappeles_fin_journee": len(non_rappeles),
        "delai_moyen_sec": round(sum(delays) / len(delays)) if delays else 0,
        "delai_moyen_min": round(sum(delays) / len(delays) / 60, 1) if delays else 0.0,
        "taux_rappel_heure": round(rappel_within_hour / total_net * 100, 1) if total_net > 0 else 100.0,
        "total_missed_net": total_net,
        "total_rappeles": len(rappeles),
        "rappeles_detail": rappeles[:10],
    }


def compute_39_indicators(work_hours, raw, dedup_removed_ids, justified_ids, real_missed):
    """Compute all 39 indicators from Hamza's framework.

    Returns a dict with all indicator values + dimension scores + global /100.
    """
    in_answered = raw["in_answered"]
    in_total = raw["in_total"]

    # --- DIMENSION 1: VOLUME & ACTIVITE ---

    # Ind.2: Contacts uniques (all directions)
    all_numbers = set()
    for p in work_hours:
        if p["contact_number"] and len(p["contact_number"]) >= 7:
            all_numbers.add(normalize_number(p["contact_number"]))
    contacts_uniques = len(all_numbers)

    # Ind.3: Doublons exclus
    doublons_exclus = raw["total"] - contacts_uniques

    # Ind.4: Appels en double 2+ meme jour (inbound same number)
    by_num_in = defaultdict(int)
    for p in work_hours:
        if p["is_inbound"] and p["contact_number"] and len(p["contact_number"]) >= 7:
            by_num_in[normalize_number(p["contact_number"])] += 1
    doubles_count = sum(1 for v in by_num_in.values() if v >= 2)
    unique_inbound_contacts = len(by_num_in)
    pct_doubles = round(doubles_count / unique_inbound_contacts * 100, 1) if unique_inbound_contacts > 0 else 0

    # Ind.7: Rappels rapides < 10 min (client re-calls inbound within 10 min)
    by_num_in_times = defaultdict(list)
    for p in work_hours:
        if p["is_inbound"] and p["contact_number"] and p["dt"]:
            by_num_in_times[normalize_number(p["contact_number"])].append(p["dt"])
    rapid_recalls = 0
    for num, times in by_num_in_times.items():
        times_sorted = sorted(times)
        for i in range(1, len(times_sorted)):
            if (times_sorted[i] - times_sorted[i - 1]).total_seconds() < 600:
                rapid_recalls += 1
    pct_rapid_recalls = round(rapid_recalls / in_total * 100, 1) if in_total > 0 else 0

    # --- DIMENSION 2: REPONSE & DISPONIBILITE ---

    # Ind.10: Taux reponse entrant (unique contacts)
    taux_reponse_entrant = round(in_answered / unique_inbound_contacts * 100, 1) if unique_inbound_contacts > 0 else 0

    # Ind.11: Taux connexion sortant
    unique_out_contacts = len(set(
        normalize_number(p["contact_number"]) for p in work_hours
        if p["is_outbound"] and p["contact_number"] and len(p["contact_number"]) >= 7
    ))
    out_connected = raw["out_connected"]
    taux_connexion_sortant = round(out_connected / unique_out_contacts * 100, 1) if unique_out_contacts > 0 else 0

    # --- DIMENSION 3: TAUX DE RAPPEL ---
    callback = compute_callback_stats(work_hours, dedup_removed_ids, justified_ids)

    # --- DIMENSION 4: QUALITE DE TRAITEMENT ---

    # Ind.22-23: Duree
    completed = [p for p in work_hours if p["duration_s"] > 0]
    avg_duration = round(sum(p["duration_s"] for p in completed) / len(completed), 1) if completed else 0
    in_target = sum(1 for p in completed if 60 <= p["duration_s"] <= 600)
    pct_in_target = round(in_target / len(completed) * 100, 1) if completed else 0

    # Ind.24: Taux d'occupation (talk time / worked hours)
    total_talk_s = sum(p["duration_s"] for p in completed)
    # Detect actual worked hours from first to last call
    call_times = [p["dt"] for p in work_hours if p["dt"]]
    if call_times:
        first_call = min(call_times)
        last_call = max(call_times)
        worked_seconds = max((last_call - first_call).total_seconds(), 3600)  # min 1 hour
    else:
        worked_seconds = 36000  # fallback 10h
    worked_hours = worked_seconds / 3600
    taux_occupation = round(total_talk_s / worked_seconds * 100, 1) if worked_seconds > 0 else 0

    # Ind.26: Capacite theorique max
    capacite_max = round(3600 / avg_duration, 1) if avg_duration > 0 else 0

    # Ind.27: Nb moyen tentatives avant traitement
    attempts_list = []
    for num, times_list in by_num_in_times.items():
        calls_for_num = sorted(
            [p for p in work_hours if p["is_inbound"] and normalize_number(p["contact_number"]) == num],
            key=lambda p: p["dt"]
        )
        attempt = 0
        for c in calls_for_num:
            attempt += 1
            if c["is_answered"]:
                break
        attempts_list.append(attempt)
    avg_attempts = round(sum(attempts_list) / len(attempts_list), 2) if attempts_list else 1.0

    # --- DIMENSION 5: FILE D'ATTENTE & SATURATION ---

    # Ind.32: Saturation file = rappels rapides / total (reuses ind.7)
    saturation_file = pct_rapid_recalls

    # Ind.33: Facteur rush horaire
    hourly_volumes = [hd["total"] for hd in raw["by_hour"].values()] if raw["by_hour"] else [0]
    peak_volume = max(hourly_volumes) if hourly_volumes else 0
    avg_hourly = sum(hourly_volumes) / len(hourly_volumes) if hourly_volumes else 1
    facteur_rush = round(peak_volume / avg_hourly, 2) if avg_hourly > 0 else 0

    # --- DIMENSION 6: CONFORMITE & TRACABILITE ---

    answered_calls = [p for p in work_hours if p["is_answered"] or p["out_connected"]]

    # Ind.34: Conformite signature
    signed = sum(1 for p in answered_calls if SIGNATURE_RE.search(p["notes"]))
    conformite_signature = round(signed / len(answered_calls) * 100, 1) if answered_calls else 0

    # Ind.35: Dossiers deja traites
    deja_traite = sum(1 for p in work_hours if DEJA_TRAITE_RE.search(p["notes"]))
    pct_deja_traite = round(deja_traite / len(work_hours) * 100, 1) if work_hours else 0

    # Ind.36: Notes avec motif documente (content beyond just signature)
    def has_motif(notes_str):
        clean = SIGNATURE_RE.sub('', notes_str).strip()
        clean = re.sub(r'[,\.\s\-]', '', clean)
        return len(clean) >= 3
    with_motif = sum(1 for p in answered_calls if has_motif(p["notes"]))
    pct_motif = round(with_motif / len(answered_calls) * 100, 1) if answered_calls else 0

    # --- DIMENSION 7: EFFICACITE & CHARGE ---

    # Ind.38: Productivite horaire
    productivite_horaire = round(in_answered / worked_hours, 1) if worked_hours > 0 else 0

    # Ind.39: Taux utilisation capacite
    taux_utilisation = round(productivite_horaire / capacite_max * 100, 1) if capacite_max > 0 else 0

    # Ind.40: Jours sans non-rappeles (binary for daily)
    jour_sans_non_rappeles = 1 if callback["non_rappeles_count"] == 0 else 0

    # ===== Build indicators dict =====
    ind = {
        # Dim 1: Volume
        "appels_bruts": raw["total"],
        "contacts_uniques": contacts_uniques,
        "doublons_exclus": doublons_exclus,
        "pct_doubles_2plus": pct_doubles,
        "appels_entrants": in_total,
        "appels_sortants": raw["out_total"],
        "rappels_rapides_10min": rapid_recalls,
        "pct_rappels_rapides": pct_rapid_recalls,

        # Dim 2: Reponse & Disponibilite
        "taux_reponse_brut": raw["response_rate"],
        "disponibilite_reelle": round(
            in_answered / (in_answered + sum(1 for p in work_hours if p["is_missed"] and p["missed_call_type"] == "1")) * 100, 1
        ) if in_answered > 0 else 0,
        "taux_reponse_entrant": taux_reponse_entrant,
        "taux_connexion_sortant": taux_connexion_sortant,
        "busy_miss": sum(1 for p in work_hours if p["is_missed"] and p["missed_call_type"] == "2"),
        "manques_agent_libre": sum(1 for p in work_hours if p["is_missed"] and p["missed_call_type"] == "1"),
        "abandons_avant_sonnerie": sum(1 for p in work_hours if p["is_missed"] and p["missed_call_type"] == "3"),

        # Dim 3: Taux de Rappel
        "taux_rappel_corrige": callback["taux_rappel_corrige"],
        "rappeles_meme_shift": callback["rappeles_meme_shift"],
        "rappeles_shift_suivant": callback["rappeles_shift_suivant"],
        "non_rappeles_count": callback["non_rappeles_count"],
        "non_rappeles": callback["non_rappeles"],
        "manques_non_rappeles_fin_journee": callback["manques_non_rappeles_fin_journee"],
        "delai_moyen_min": callback["delai_moyen_min"],
        "taux_rappel_heure": callback["taux_rappel_heure"],

        # Dim 4: Qualite de Traitement
        "duree_moyenne_s": avg_duration,
        "duree_moyenne_min": round(avg_duration / 60, 1) if avg_duration > 0 else 0,
        "duree_dans_cible_pct": pct_in_target,
        "taux_occupation": taux_occupation,
        "taux_callback_honore": None,  # Phase 2: needs call_traits
        "capacite_theorique_max": capacite_max,
        "nb_tentatives_avant_traitement": avg_attempts,

        # Dim 5: File d'Attente & Saturation
        "attente_moyenne_file": None,  # Phase 2: needs queue_wait_time
        "pct_passes_en_file": None,
        "pct_raccroches_file": None,
        "appels_60s_attente": None,
        "saturation_file": saturation_file,
        "facteur_rush": facteur_rush,

        # Dim 6: Conformite & Tracabilite
        "conformite_signature": conformite_signature,
        "dossiers_deja_traites_pct": pct_deja_traite,
        "notes_avec_motif_pct": pct_motif,
        "contacts_recurrents_multi_jours": None,  # weekly only

        # Dim 7: Efficacite & Charge
        "productivite_horaire": productivite_horaire,
        "taux_utilisation_capacite": taux_utilisation,
        "jours_sans_non_rappeles": jour_sans_non_rappeles,

        # Supporting data
        "worked_hours": round(worked_hours, 1),
        "total_talk_min": round(total_talk_s / 60),
    }

    # ===== WEIGHTED SCORE /100 =====
    score = compute_weighted_score(ind)
    ind["dimensions"] = score["dimensions"]
    ind["global_score"] = score["global_score"]

    return ind


def score_indicator(value, target, higher_is_better=True):
    """Score a single indicator 0-10 based on how close to target."""
    if value is None:
        return None
    if higher_is_better:
        return min(10.0, round(value / target * 10, 1)) if target > 0 else 10.0
    else:
        if value <= target:
            return 10.0
        return max(0.0, round((1 - (value - target) / max(target, 1)) * 10, 1))


def compute_weighted_score(ind):
    """Compute Hamza's 7-dimension weighted score /100."""

    WEIGHTS = {
        "reponse_disponibilite": 0.25,
        "taux_rappel": 0.25,
        "qualite_traitement": 0.20,
        "file_attente_saturation": 0.08,
        "conformite_tracabilite": 0.10,
        "efficacite_charge": 0.12,
    }

    def avg_valid(scores):
        valid = [s for s in scores if s is not None]
        return round(sum(valid) / len(valid), 1) if valid else None

    dim_scores = {
        "reponse_disponibilite": avg_valid([
            score_indicator(ind["taux_reponse_brut"], 75),
            score_indicator(ind["disponibilite_reelle"], 90),
            score_indicator(ind["taux_reponse_entrant"], 70),
            score_indicator(ind["taux_connexion_sortant"], 80),
        ]),
        "taux_rappel": avg_valid([
            score_indicator(ind["taux_rappel_corrige"], 95),
            score_indicator(ind["taux_rappel_heure"], 70),
            score_indicator(ind["delai_moyen_min"], 60, higher_is_better=False),
        ]),
        "qualite_traitement": avg_valid([
            score_indicator(ind["duree_dans_cible_pct"], 80),
            score_indicator(ind["taux_occupation"], 55),
            score_indicator(ind["nb_tentatives_avant_traitement"], 2, higher_is_better=False),
        ]),
        "file_attente_saturation": avg_valid([
            score_indicator(ind["saturation_file"], 30, higher_is_better=False),
            score_indicator(ind["facteur_rush"], 1.5, higher_is_better=False),
        ]),
        "conformite_tracabilite": avg_valid([
            score_indicator(ind["conformite_signature"], 95),
            score_indicator(ind["dossiers_deja_traites_pct"], 1, higher_is_better=False),
            score_indicator(ind["notes_avec_motif_pct"], 20),
        ]),
        "efficacite_charge": avg_valid([
            score_indicator(ind["taux_utilisation_capacite"], 55),
            score_indicator(ind["productivite_horaire"], 15),
        ]),
    }

    # Global score /100
    total = 0.0
    weight_sum = 0.0
    for dim_name, weight in WEIGHTS.items():
        score = dim_scores.get(dim_name)
        if score is not None:
            total += score * weight
            weight_sum += weight

    global_100 = round(total / weight_sum * 10, 1) if weight_sum > 0 else 0

    return {
        "dimensions": dim_scores,
        "global_score": global_100,
    }


def compute_smart_stats(date_str):
    """Compute all 3 levels of stats: raw, deduped, real."""
    raw_calls = fetch_all_raw(date_str)
    parsed = [parse_call(c) for c in raw_calls]
    parsed = [p for p in parsed if p["dt"] is not None]

    # Detect weekend
    dt_date = datetime.strptime(date_str, "%Y-%m-%d")
    is_weekend = dt_date.weekday() >= 5  # 5=Saturday, 6=Sunday

    # Filter to work hours only (8h-18h weekday, 8h-17h weekend)
    end_hour = 17 if is_weekend else 18
    work_hours = [p for p in parsed if 8 <= p["hour"] < end_hour]
    after_hours = [p for p in parsed if p["hour"] < 8 or p["hour"] >= end_hour]
    after_hours_missed = sum(1 for p in after_hours if p["is_missed"])

    # Weekend: exclude formateur@ from stats (nobody covers it)
    if is_weekend:
        formateur_excluded = [p for p in work_hours if p["account"] == "formateur"]
        work_hours = [p for p in work_hours if p["account"] != "formateur"]

    # ===== LEVEL 1: RAW STATS (work hours only) =====
    # Use work_hours for all stats, track after_hours separately
    raw = {
        "total": len(work_hours),
        "total_all": len(parsed),
        "after_hours": len(after_hours),
        "after_hours_missed": after_hours_missed,
        "in_total": sum(1 for p in work_hours if p["is_inbound"]),
        "in_answered": sum(1 for p in work_hours if p["is_answered"]),
        "in_missed": sum(1 for p in work_hours if p["is_missed"]),
        "out_total": sum(1 for p in work_hours if p["is_outbound"]),
        "out_connected": sum(1 for p in work_hours if p["out_connected"]),
    }
    raw["response_rate"] = round(raw["in_answered"] / raw["in_total"] * 100) if raw["in_total"] > 0 else 0

    # By account
    raw["by_account"] = {}
    for acct in JUSTCALL_ACCOUNTS:
        ac = [p for p in work_hours if p["account"] == acct]
        ain = sum(1 for p in ac if p["is_inbound"])
        aans = sum(1 for p in ac if p["is_answered"])
        amiss = sum(1 for p in ac if p["is_missed"])
        aout = sum(1 for p in ac if p["is_outbound"])
        raw["by_account"][acct] = {
            "total": len(ac), "in": ain, "in_answered": aans, "in_missed": amiss,
            "out": aout, "response_rate": round(aans / ain * 100) if ain > 0 else 0,
        }

    # By hour (work hours only)
    raw["by_hour"] = {}
    for p in work_hours:
        h = p["hour"]
        if h not in raw["by_hour"]:
            raw["by_hour"][h] = {"total": 0, "answered": 0, "missed": 0, "outbound": 0}
        raw["by_hour"][h]["total"] += 1
        if p["is_answered"]: raw["by_hour"][h]["answered"] += 1
        elif p["is_missed"]: raw["by_hour"][h]["missed"] += 1
        elif p["is_outbound"]: raw["by_hour"][h]["outbound"] += 1

    # ===== LEVEL 2: DEDUPED (same client calling multiple times) =====
    by_number = defaultdict(list)
    for p in work_hours:
        if p["is_inbound"] and p["contact_number"] and len(p["contact_number"]) >= 7:
            by_number[p["contact_number"]].append(p)

    dedup_removed = 0
    dedup_details = []
    dedup_removed_ids = set()

    for num, calls in by_number.items():
        missed = [c for c in calls if c["is_missed"]]
        answered = [c for c in calls if c["is_answered"]]

        if len(missed) <= 1 and not answered:
            continue

        name = ""
        for c in calls:
            if c["contact_name"]:
                name = c["contact_name"]
                break

        if answered:
            # Client got answered eventually — all missed are dupes
            for c in missed:
                dedup_removed_ids.add(c["id"])
                dedup_removed += 1
            if missed:
                dedup_details.append({"number": num, "name": name, "removed": len(missed), "reason": "repondu apres"})
        elif len(missed) > 1:
            # Never answered — keep first, remove rest
            missed_sorted = sorted(missed, key=lambda c: c["time"])
            for c in missed_sorted[1:]:
                dedup_removed_ids.add(c["id"])
                dedup_removed += 1
            dedup_details.append({"number": num, "name": name, "removed": len(missed) - 1, "reason": "rappels"})

    deduped_parsed = [p for p in work_hours if p["id"] not in dedup_removed_ids]
    dedup = {
        "removed": dedup_removed,
        "details": sorted(dedup_details, key=lambda x: -x["removed"])[:10],
        "in_missed": sum(1 for p in deduped_parsed if p["is_missed"]),
        "response_rate": round(raw["in_answered"] / (raw["in_answered"] + sum(1 for p in deduped_parsed if p["is_missed"])) * 100) if (raw["in_answered"] + sum(1 for p in deduped_parsed if p["is_missed"])) > 0 else 0,
    }

    # ===== LEVEL 3: REAL (exclude missed while agent was busy) =====
    # Build busy windows from ALL answered calls during work hours
    busy_windows = []
    for p in work_hours:
        if p["duration_s"] > 0 and p["dt"] and p["end_dt"]:
            busy_windows.append((p["dt"], p["end_dt"], p["account"]))

    # Sort by start time
    busy_windows.sort(key=lambda x: x[0])

    # For each missed call (after dedup), check if an agent was busy at that time on that account
    justified_missed = 0
    justified_ids = set()
    real_missed = 0

    deduped_missed = [p for p in deduped_parsed if p["is_missed"]]
    for p in deduped_missed:
        was_busy = False
        for start, end, acct in busy_windows:
            if acct == p["account"] and start <= p["dt"] <= end:
                was_busy = True
                break
        if was_busy:
            justified_missed += 1
            justified_ids.add(p["id"])
        else:
            real_missed += 1

    real_rate = round(raw["in_answered"] / (raw["in_answered"] + real_missed) * 100) if (raw["in_answered"] + real_missed) > 0 else 0

    real = {
        "justified_missed": justified_missed,
        "real_missed": real_missed,
        "response_rate": real_rate,
    }

    # ===== LEVEL 4: SHIFT SPLIT =====
    shifts = {}
    if is_weekend:
        shift_config = [
            ("journee", 8, 17, "8h-17h (Sekou)"),
        ]
    else:
        shift_config = [
            ("matin", 8, 12, "8h-12h (Hamza seul)"),
            ("apres_midi", 12, 18, "12h-18h (Hamza + Lilia)"),
        ]
    for shift_name, h_start, h_end, label in shift_config:
        sc = [p for p in work_hours if h_start <= p["hour"] < h_end]
        s_in = sum(1 for p in sc if p["is_inbound"])
        s_ans = sum(1 for p in sc if p["is_answered"])
        s_miss = sum(1 for p in sc if p["is_missed"])
        s_out = sum(1 for p in sc if p["is_outbound"])

        # Per account for this shift
        s_accounts = {}
        for acct in JUSTCALL_ACCOUNTS:
            ac = [p for p in sc if p["account"] == acct]
            ain = sum(1 for p in ac if p["is_inbound"])
            aans = sum(1 for p in ac if p["is_answered"])
            amiss = sum(1 for p in ac if p["is_missed"])
            aout = sum(1 for p in ac if p["is_outbound"])
            s_accounts[acct] = {
                "total": len(ac), "in": ain, "in_answered": aans, "in_missed": amiss,
                "out": aout, "response_rate": round(aans / ain * 100) if ain > 0 else 0,
            }

        # Dedup for this shift
        s_by_num = defaultdict(list)
        for p in sc:
            if p["is_inbound"] and p["contact_number"] and len(p["contact_number"]) >= 7:
                s_by_num[p["contact_number"]].append(p)
        s_dupes = 0
        for num, cs in s_by_num.items():
            missed_c = [c for c in cs if c["is_missed"]]
            answered_c = [c for c in cs if c["is_answered"]]
            if answered_c: s_dupes += len(missed_c)
            elif len(missed_c) > 1: s_dupes += len(missed_c) - 1

        # Agent busy for this shift
        s_busy = [(s, e, a) for s, e, a in busy_windows if h_start <= s.hour < h_end]
        s_justified = 0
        for p in sc:
            if not p["is_missed"]: continue
            for bs, be, ba in s_busy:
                if ba == p["account"] and bs <= p["dt"] <= be:
                    s_justified += 1
                    break
        s_vrais = max(0, s_miss - s_dupes - s_justified)
        s_real_rate = round(s_ans / (s_ans + s_vrais) * 100) if (s_ans + s_vrais) > 0 else 0

        shifts[shift_name] = {
            "label": label, "total": len(sc),
            "in_total": s_in, "in_answered": s_ans, "in_missed": s_miss,
            "out_total": s_out,
            "response_rate_brut": round(s_ans / s_in * 100) if s_in > 0 else 0,
            "doublons": s_dupes, "agent_occupe": s_justified,
            "vrais_manques": s_vrais, "taux_reel": s_real_rate,
            "by_account": s_accounts,
        }

    # ===== LEVEL 5: 39 INDICATORS (Hamza's framework) =====
    indicators = compute_39_indicators(
        work_hours, raw, dedup_removed_ids, justified_ids, real_missed
    )

    # ===== LEVEL 6: ALERTS =====

    # Fix 1: Agent name for the day
    if is_weekend:
        agent_du_jour = "Sekou"
    else:
        agent_du_jour = "Hamza + Lilia"

    # Fix 3: Ultra-frustrated clients (5+ calls same day)
    frustrated_clients = []
    call_counts = defaultdict(lambda: {"count": 0, "name": "", "missed": 0})
    for p in work_hours:
        if p["is_inbound"] and p["contact_number"] and len(p["contact_number"]) >= 7:
            norm = normalize_number(p["contact_number"])
            call_counts[norm]["count"] += 1
            if p["contact_name"]:
                call_counts[norm]["name"] = p["contact_name"]
            if p["is_missed"]:
                call_counts[norm]["missed"] += 1
    for num, info in call_counts.items():
        if info["count"] >= 5:
            frustrated_clients.append({
                "number": num,
                "name": info["name"],
                "calls": info["count"],
                "missed": info["missed"],
            })
    frustrated_clients.sort(key=lambda x: -x["calls"])

    # Fix 4: Hourly miss alerts (hours with >70% miss rate and 3+ misses)
    alert_hours = []
    for h, hd in raw["by_hour"].items():
        inbound_h = hd.get("answered", 0) + hd.get("missed", 0)
        if inbound_h >= 3 and hd["missed"] >= 3:
            miss_rate = round(hd["missed"] / inbound_h * 100)
            if miss_rate >= 70:
                alert_hours.append({"hour": h, "missed": hd["missed"], "total_in": inbound_h, "miss_rate": miss_rate})
    alert_hours.sort(key=lambda x: -x["miss_rate"])

    # ===== SUMMARY =====
    return {
        "date": date_str,
        "is_weekend": is_weekend,
        "agent_du_jour": agent_du_jour,
        "raw": raw,
        "dedup": dedup,
        "real": real,
        "shifts": shifts,
        "indicators": indicators,
        "frustrated_clients": frustrated_clients,
        "alert_hours": alert_hours,
        "summary": {
            "total_calls": raw["total"],
            "total_all_including_after_hours": raw["total_all"],
            "after_hours_excluded": raw["after_hours"],
            "after_hours_missed": raw["after_hours_missed"],
            "total_inbound": raw["in_total"],
            "total_outbound": raw["out_total"],
            "answered": raw["in_answered"],
            "missed_brut": raw["in_missed"],
            "missed_doublons": dedup_removed,
            "missed_agent_occupe": justified_missed,
            "vrais_manques": real_missed,
            "taux_brut": raw["response_rate"],
            "taux_deduplique": dedup["response_rate"],
            "taux_reel": real_rate,
        },
    }


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    date_str = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y-%m-%d")
    log.info("Computing smart stats for %s...", date_str)

    stats = compute_smart_stats(date_str)
    s = stats["summary"]
    ind = stats.get("indicators", {})

    print()
    print("=" * 60)
    print(f"  SMART STATS v2 — {date_str}")
    print("=" * 60)
    print()
    print(f"Total appels (8h-18h): {s['total_calls']}")
    print(f"  (+ {s['after_hours_excluded']} hors heures, exclus dont {s['after_hours_missed']} manques)")
    print(f"Entrants:         {s['total_inbound']} | Sortants: {s['total_outbound']}")
    print()
    print(f"--- ANALYSE DES MANQUES ---")
    print(f"Repondus:             {s['answered']}")
    print(f"Manques bruts:        {s['missed_brut']}")
    print(f"  - Doublons retires: {s['missed_doublons']} (meme client qui rappelle)")
    print(f"  - Agent occupe:     {s['missed_agent_occupe']} (deja en appel)")
    print(f"  = VRAIS MANQUES:    {s['vrais_manques']} (agent libre mais pas repondu)")
    print()
    print(f"--- TAUX DE REPONSE ---")
    print(f"Brut:       {s['taux_brut']}%  (tous les manques)")
    print(f"Deduplique: {s['taux_deduplique']}%  (sans doublons)")
    print(f"REEL:       {s['taux_reel']}%  (sans doublons ni agent occupe)")
    print()

    # 39 Indicators
    if ind:
        print("=" * 60)
        print(f"  39 INDICATEURS — SCORE GLOBAL: {ind.get('global_score', 0)}/100")
        print("=" * 60)

        dims = ind.get("dimensions", {})
        DIM_LABELS = {
            "reponse_disponibilite": ("Reponse & Dispo", "25%"),
            "taux_rappel": ("Taux de Rappel", "25%"),
            "qualite_traitement": ("Qualite Traitement", "20%"),
            "file_attente_saturation": ("File & Saturation", "8%"),
            "conformite_tracabilite": ("Conformite", "10%"),
            "efficacite_charge": ("Efficacite", "12%"),
        }
        for dim_key, (label, pct) in DIM_LABELS.items():
            v = dims.get(dim_key)
            filled = int((v or 0))
            bar = "#" * filled + "." * (10 - filled)
            print(f"  {label:<22} {(v or 0):>5}/10  [{bar}]  x{pct}")

        print()
        print("--- DIM 1: VOLUME ---")
        print(f"  Appels bruts:           {ind['appels_bruts']}")
        print(f"  Contacts uniques:       {ind['contacts_uniques']}")
        print(f"  Doublons exclus:        {ind['doublons_exclus']}")
        print(f"  En double 2+:           {ind['pct_doubles_2plus']}% (std <15%)")
        print(f"  Rappels rapides <10min: {ind['rappels_rapides_10min']} ({ind['pct_rappels_rapides']}%, std <20%)")

        print()
        print("--- DIM 2: REPONSE ---")
        print(f"  Taux reponse brut:      {ind['taux_reponse_brut']}% (std >75%)")
        print(f"  Disponibilite reelle:   {ind['disponibilite_reelle']}% (std >90%)")
        print(f"  Taux reponse entrant:   {ind['taux_reponse_entrant']}% (std >70%)")
        print(f"  Taux connexion sortant: {ind['taux_connexion_sortant']}% (std >80%)")
        print(f"  Manques agent libre:    {ind['manques_agent_libre']} (std <50/mois)")

        print()
        print("--- DIM 3: RAPPEL (x25%) ---")
        print(f"  Taux rappel corrige:    {ind['taux_rappel_corrige']}% (std >95%)")
        print(f"  Rappeles meme shift:    {ind['rappeles_meme_shift']}")
        print(f"  Rappeles shift suivant: {ind['rappeles_shift_suivant']}")
        print(f"  Non rappeles:           {ind['non_rappeles_count']} (std =0)")
        print(f"  Delai moyen rappel:     {ind['delai_moyen_min']} min (std <60)")
        print(f"  Rappel dans l'heure:    {ind['taux_rappel_heure']}% (std >70%)")
        if ind["non_rappeles"]:
            print(f"  --- LISTE NON RAPPELES ---")
            for nr in ind["non_rappeles"][:10]:
                name = (nr['name'] or nr['number']).encode('ascii', 'replace').decode('ascii')
                print(f"    {name} manque a {nr['miss_time'][-8:]} ({nr['attempts']} tentatives)")

        print()
        print("--- DIM 4: QUALITE ---")
        print(f"  Duree moyenne:          {ind['duree_moyenne_min']} min ({ind['duree_moyenne_s']}s, std 60-600s)")
        print(f"  Duree dans cible:       {ind['duree_dans_cible_pct']}% (std >80%)")
        print(f"  Taux occupation:        {ind['taux_occupation']}% (std 40-70%)")
        print(f"  Capacite max:           {ind['capacite_theorique_max']} appels/h")
        print(f"  Tentatives avg:         {ind['nb_tentatives_avant_traitement']} (std <2)")

        print()
        print("--- DIM 5: FILE D'ATTENTE ---")
        print(f"  Saturation file:        {ind['saturation_file']}% (std <30%)")
        print(f"  Facteur rush:           {ind['facteur_rush']}x (std <1.5x)")
        print(f"  (Attente moy, % file, raccroches, >60s = Phase 2 / API)")

        print()
        print("--- DIM 6: CONFORMITE ---")
        print(f"  Conformite signature:   {ind['conformite_signature']}% (std >95%)")
        print(f"  Dossiers deja traites:  {ind['dossiers_deja_traites_pct']}% (std <1%)")
        print(f"  Notes avec motif:       {ind['notes_avec_motif_pct']}% (std >20%)")

        print()
        print("--- DIM 7: EFFICACITE ---")
        print(f"  Productivite horaire:   {ind['productivite_horaire']} appels/h")
        print(f"  Utilisation capacite:   {ind['taux_utilisation_capacite']}% (std 40-70%)")
        print(f"  Heures travaillees:     {ind['worked_hours']}h")
        print(f"  Temps total appels:     {ind['total_talk_min']} min")
        print(f"  Jour sans non-rappeles: {'OUI' if ind['jours_sans_non_rappeles'] else 'NON'}")

    # Save JSON
    with open(f"smart_stats_{date_str}.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, default=str, ensure_ascii=False)
    print(f"\nJSON: smart_stats_{date_str}.json")
