"""Analyze missed calls: who was never called back?"""
import json, sys, time, logging
from collections import defaultdict
from datetime import datetime
import requests

API_URL = "https://api.justcall.io/v1/calls/query"
API_KEY = "daf60d953694336f07c84c74205eb311dd85c996"
API_SECRET = "20612f8fcb80ef33845cbdc226bc8174853c82dd"
ACCOUNTS = {"academie": "301418", "formateur": "302145"}
logging.basicConfig(level=logging.INFO)

def fetch_all(date_str):
    headers = {"Accept": "application/json", "Authorization": f"{API_KEY}:{API_SECRET}"}
    all_calls = []
    for acct, aid in ACCOUNTS.items():
        page = 1
        while page <= 15:
            body = {"from_date": date_str, "to_date": date_str, "agent_id": aid, "per_page": 100, "page": page}
            try:
                resp = requests.post(API_URL, json=body, headers=headers, timeout=30)
                calls = resp.json().get("data", [])
                if not calls: break
                on_date = [c for c in calls if (c.get("time","") or "").startswith(date_str)]
                for c in on_date: c["_acct"] = acct
                all_calls.extend(on_date)
                before = [c for c in calls if (c.get("time","") or "") < date_str]
                if before: break
                if len(calls) < 100: break
                page += 1
                time.sleep(0.5)
            except Exception as e:
                print(f"Error: {e}")
                break
    return all_calls

def analyze(date_str):
    all_calls = fetch_all(date_str)
    print(f"Total raw calls: {len(all_calls)}")

    by_number = defaultdict(list)
    for c in all_calls:
        num = (c.get("contact_number") or "").strip()
        if num and len(num) >= 7:
            by_number[num].append(c)

    missed_no_callback = []
    missed_called_back = []
    missed_answered_later = []

    for num, calls in by_number.items():
        inbound = [c for c in calls if c.get("direction") == "1"]
        outbound = [c for c in calls if c.get("direction") != "1"]

        in_missed = [c for c in inbound if int(c.get("duration", 0) or 0) == 0]
        in_answered = [c for c in inbound if int(c.get("duration", 0) or 0) > 0]
        out_connected = [c for c in outbound if int(c.get("duration", 0) or 0) > 0]

        if not in_missed:
            continue

        name = ""
        for c in calls:
            if c.get("contact_name"):
                name = c["contact_name"]
                break

        first_miss = min(c.get("time", "") for c in in_missed)
        total_missed = len(in_missed)

        if in_answered:
            missed_answered_later.append({"num": num, "name": name, "missed": total_missed, "first_miss": first_miss})
        elif out_connected:
            missed_called_back.append({"num": num, "name": name, "missed": total_missed, "callbacks": len(out_connected), "first_miss": first_miss})
        else:
            missed_no_callback.append({"num": num, "name": name, "missed": total_missed, "first_miss": first_miss})

    missed_no_callback.sort(key=lambda x: -x["missed"])
    missed_called_back.sort(key=lambda x: -x["missed"])
    missed_answered_later.sort(key=lambda x: -x["missed"])

    print()
    print("=" * 70)
    print(f"  ANALYSE APPELS MANQUES — {date_str}")
    print("=" * 70)
    print()
    total_contacts_missed = len(missed_no_callback) + len(missed_called_back) + len(missed_answered_later)
    print(f"Contacts uniques avec appels manques: {total_contacts_missed}")
    print()
    print(f"  CLIENT A RAPPELE ET A ETE REPONDU:    {len(missed_answered_later):3d} contacts")
    print(f"  AGENT A RAPPELE LE CLIENT:             {len(missed_called_back):3d} contacts")
    print(f"  JAMAIS RAPPELE NI REPONDU:             {len(missed_no_callback):3d} contacts  <-- CLIENTS PERDUS")
    print()

    if missed_answered_later:
        print("--- Clients qui ont rappele et ont ete repondus ---")
        for c in missed_answered_later[:5]:
            print(f"  {(c['name'] or c['num'])[:35]:35s} | {c['missed']}x manque avant | 1er appel: {c['first_miss'].split(' ')[1][:5]}")
        print()

    if missed_called_back:
        print("--- Clients rappeles par l'agent ---")
        for c in missed_called_back[:5]:
            print(f"  {(c['name'] or c['num'])[:35]:35s} | {c['missed']}x manque | {c['callbacks']}x rappele | 1er: {c['first_miss'].split(' ')[1][:5]}")
        print()

    print("=" * 70)
    print(f"  {len(missed_no_callback)} CLIENTS JAMAIS RAPPELES")
    print("=" * 70)
    print()
    for c in missed_no_callback[:25]:
        print(f"  {(c['name'] or c['num'])[:35]:35s} | {c['missed']}x manque | 1er appel: {c['first_miss'].split(' ')[1][:5]}")

    total_lost_calls = sum(c["missed"] for c in missed_no_callback)
    print()
    print(f"Total clients perdus: {len(missed_no_callback)}")
    print(f"Total appels manques de ces clients: {total_lost_calls}")

    # Potential revenue loss
    print()
    print("--- IMPACT ---")
    avg_inscription = 450  # $ average inscription value
    conversion_rate = 0.15  # 15% of callers would have signed up
    potential_lost = round(len(missed_no_callback) * conversion_rate * avg_inscription)
    print(f"Si {int(conversion_rate*100)}% de ces {len(missed_no_callback)} contacts se seraient inscrits a {avg_inscription}$:")
    print(f"  REVENUS POTENTIELS PERDUS: ~{potential_lost}$ pour cette journee")

if __name__ == "__main__":
    date_str = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y-%m-%d")
    analyze(date_str)
