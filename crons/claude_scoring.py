"""
Claude CLI Wrapper — Calls claude.exe on Nitro in non-interactive mode.
Uses the Max subscription via Claude Code CLI (-p flag).
Supports Haiku (per-call scoring) and Opus (weekly report).
"""

import json
import logging
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

log = logging.getLogger("claude_scoring")

CLAUDE_EXE = r"C:\Users\User\AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\claude-code\2.1.63\claude.exe"
GIT_BASH = r"C:\Program Files\Git\bin\bash.exe"

# ---------------------------------------------------------------------------
# Low-level call
# ---------------------------------------------------------------------------

def call_claude(prompt: str, model: str = "haiku", max_turns: int = 1, timeout: int = 120) -> str:
    """Call Claude CLI in print mode. Returns raw text output."""
    env = os.environ.copy()
    env["CLAUDE_CODE_GIT_BASH_PATH"] = GIT_BASH

    cmd = [CLAUDE_EXE, "-p", "--model", model, "--max-turns", str(max_turns)]

    try:
        result = subprocess.run(
            cmd, input=prompt, capture_output=True, text=True,
            env=env, timeout=timeout, cwd=r"C:\Users\user"
        )
        if result.returncode != 0:
            log.warning("Claude CLI returned %d: %s", result.returncode, result.stderr[:200])
            return ""
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        log.warning("Claude CLI timed out after %ds (model=%s)", timeout, model)
        return ""
    except Exception as e:
        log.error("Claude CLI error: %s", e)
        return ""


def call_claude_json(prompt: str, model: str = "haiku", timeout: int = 120) -> dict:
    """Call Claude CLI and parse JSON from response."""
    raw = call_claude(prompt, model=model, timeout=timeout)
    if not raw:
        return {}

    # Extract JSON from response (might have text around it)
    try:
        # Try direct parse first
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Try to find JSON in the response
    for start_char, end_char in [("{", "}"), ("[", "]")]:
        start = raw.find(start_char)
        if start == -1:
            continue
        # Find matching end
        depth = 0
        for i in range(start, len(raw)):
            if raw[i] == start_char:
                depth += 1
            elif raw[i] == end_char:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(raw[start:i + 1])
                    except json.JSONDecodeError:
                        break

    log.warning("Could not parse JSON from Claude response: %s", raw[:200])
    return {}


# ---------------------------------------------------------------------------
# Haiku scoring (per call)
# ---------------------------------------------------------------------------

HAIKU_PROMPT_TEMPLATE = """Tu es un evaluateur de qualite d'appels pour l'Academie XGuard (formation en securite au Quebec).
Analyse ce transcript et score chaque dimension de 0 a 10.

Agent: {agent}
Duree: {duration} secondes
Direction: {direction}

TRANSCRIPT:
{transcript}

Score ces 10 dimensions:
1. accueil - L'agent s'est-il presente clairement (nom + XGuard + offre d'aide)?
2. ecoute - A-t-il reformule et montre qu'il comprend le besoin?
3. resolution - Le probleme/question a-t-il ete resolu concretement?
4. patience - A-t-il pris le temps necessaire sans presser?
5. professionnalisme - Langage professionnel, courtoisie, bonne cloture?
6. vente_subtile - A-t-il propose naturellement l'inscription quand pertinent?
7. qualification - A-t-il pose des questions avant de repondre?
8. gestion_objections - A-t-il gere les objections/plaintes avec empathie + solution?
9. energie - Ton positif, enthousiasme naturel?
10. engagement - Dialogue naturel ou echange mecanique?

Reponds UNIQUEMENT en JSON valide, rien d'autre:
{{"accueil":0,"ecoute":0,"resolution":0,"patience":0,"professionnalisme":0,"vente_subtile":0,"qualification":0,"gestion_objections":0,"energie":0,"engagement":0,"coaching_note":"une phrase de coaching"}}"""


def score_call_haiku(call: dict) -> dict:
    """Score a single call with Haiku. Returns {ai_scores, ai_global, coaching_note}."""
    transcript = call.get("transcript", "")
    if not transcript or len(transcript) < 20:
        return {}

    # Truncate very long transcripts to save tokens
    words = transcript.split()
    if len(words) > 1500:
        transcript = " ".join(words[:1500]) + "... [tronque]"

    agent = call.get("agent", call.get("person_id", "?"))
    duration = call.get("duration_s", 0)
    direction = call.get("direction", "?")

    prompt = HAIKU_PROMPT_TEMPLATE.format(
        agent=agent, duration=duration, direction=direction, transcript=transcript
    )

    result = call_claude_json(prompt, model="haiku", timeout=60)

    if not result:
        return {}

    # Extract scores
    dims = ["accueil", "ecoute", "resolution", "patience", "professionnalisme",
            "vente_subtile", "qualification", "gestion_objections", "energie", "engagement"]

    scores = {}
    for d in dims:
        val = result.get(d)
        if isinstance(val, (int, float)):
            scores[d] = round(min(10.0, max(0.0, float(val))), 1)

    if not scores:
        return {}

    global_score = round(sum(scores.values()) / len(scores), 1) if scores else 0
    coaching_note = result.get("coaching_note", "")

    return {
        "ai_scores": scores,
        "ai_global_score": global_score,
        "coaching_note": coaching_note,
    }


def score_calls_batch(calls: list, max_workers: int = 5, delay: float = 1.0) -> list:
    """Score multiple calls with Haiku in parallel. Returns list of results."""
    results = [None] * len(calls)

    def process_one(idx, call):
        time.sleep(delay * (idx % max_workers))  # Stagger starts
        return idx, score_call_haiku(call)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_one, i, c): i for i, c in enumerate(calls)}
        done = 0
        for future in as_completed(futures):
            try:
                idx, result = future.result()
                results[idx] = result
                done += 1
                if done % 10 == 0:
                    log.info("  Haiku scored %d/%d calls", done, len(calls))
            except Exception as e:
                idx = futures[future]
                log.warning("  Haiku failed for call %d: %s", idx, e)
                results[idx] = {}

    return results


# ---------------------------------------------------------------------------
# Heidys VENTES scoring (per call) — 8 dimensions + summary + next step
# ---------------------------------------------------------------------------

HEIDYS_PROMPT_TEMPLATE = """Tu es un coach de vente telephonique pour l'Academie XGuard (formation gardiennage/securite au Quebec).
Analyse cet appel de vente sortant et evalue la performance de la vendeuse Heidys.

Duree: {duration} secondes

TRANSCRIPT:
{transcript}

Score ces 8 dimensions de 0 a 10:
1. intro - S'est-elle presentee clairement (nom + Academie XGuard + raison de l'appel)?
2. qualification - A-t-elle pose des questions pour comprendre le besoin AVANT de donner le prix?
3. objections - A-t-elle gere les objections avec empathie et propose des solutions?
4. closing - A-t-elle tente de conclure la vente ou fixer un prochain pas concret?
5. empathie - A-t-elle montre de l'empathie et personnalise la conversation?
6. energie - Ton positif, enthousiaste, pas robotique?
7. duree - L'appel etait-il assez long pour qualifier correctement? (court=mauvais si prospect interesse)
8. engagement - Dialogue naturel a deux sens ou monologue?

AUSSI fournir:
- resume: 2-3 phrases resumant ce qui s'est passe dans l'appel
- objections_detectees: liste des objections du prospect (ex: "trop cher", "pas le temps")
- next_step: ce qui a ete convenu comme prochaine etape (ex: "rappeler mardi", "envoyer entente")
- callback_date: si un rappel a ete mentionne, la date au format YYYY-MM-DD (ou null si aucun)
- coaching_note: 1 phrase de conseil specifique pour cet appel

Reponds UNIQUEMENT en JSON valide:
{{"intro":0,"qualification":0,"objections":0,"closing":0,"empathie":0,"energie":0,"duree":0,"engagement":0,"resume":"...","objections_detectees":[],"next_step":"...","callback_date":null,"coaching_note":"..."}}"""


def score_heidys_call(call: dict) -> dict:
    """Score a single Heidys sales call with Haiku. Returns full analysis."""
    transcript = call.get("transcript", "")
    if not transcript or len(transcript) < 20:
        return {}

    words = transcript.split()
    if len(words) > 1500:
        transcript = " ".join(words[:1500]) + "... [tronque]"

    duration = call.get("duration_s", 0)

    prompt = HEIDYS_PROMPT_TEMPLATE.format(duration=duration, transcript=transcript)
    result = call_claude_json(prompt, model="haiku", timeout=90)

    if not result:
        return {}

    dims = ["intro", "qualification", "objections", "closing", "empathie", "energie", "duree", "engagement"]
    scores = {}
    for d in dims:
        val = result.get(d)
        if isinstance(val, (int, float)):
            scores[d] = round(min(10.0, max(0.0, float(val))), 1)

    if not scores:
        return {}

    global_score = round(sum(scores.values()) / len(scores), 1)

    return {
        "ai_scores": scores,
        "ai_global_score": global_score,
        "coaching_note": result.get("coaching_note", ""),
        "call_summary": result.get("resume", ""),
        "objections_detected": result.get("objections_detectees", []),
        "next_step": result.get("next_step", ""),
        "callback_date": result.get("callback_date"),
    }


def score_heidys_batch(calls: list, max_workers: int = 3, delay: float = 2.0) -> list:
    """Score multiple Heidys calls in parallel."""
    results = [None] * len(calls)

    def process_one(idx, call):
        time.sleep(delay * (idx % max_workers))
        return idx, score_heidys_call(call)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_one, i, c): i for i, c in enumerate(calls)}
        done = 0
        for future in as_completed(futures):
            try:
                idx, result = future.result()
                results[idx] = result
                done += 1
                if done % 5 == 0:
                    log.info("  Haiku scored %d/%d Heidys calls", done, len(calls))
            except Exception as e:
                idx = futures[future]
                log.warning("  Haiku failed for Heidys call %d: %s", idx, e)
                results[idx] = {}

    return results


# ---------------------------------------------------------------------------
# Opus report (weekly summary)
# ---------------------------------------------------------------------------

OPUS_PROMPT_TEMPLATE = """Tu es le directeur coaching de l'Academie XGuard. Analyse les donnees de la semaine pour l'equipe SAC (Service a la Clientele).

L'Academie XGuard offre des formations en securite (gardiennage), drone, et secourisme au Quebec.
L'equipe SAC repond aux appels entrants et fait des suivis sortants. Leur role est de repondre aux questions, aider aux inscriptions, et gerer les plaintes.

DONNEES DE LA SEMAINE:
{data}

Genere un rapport de coaching en francais qui inclut:

1. RESUME EXECUTIF (3-4 phrases percutantes)

2. PROFIL HAMZA (Responsable SAC, Lun-Ven 8h-16h):
   - Score global et evolution
   - Top 3 forces avec exemples concrets d'appels (cite le nom du client et ce qui s'est passe)
   - Top 3 points a ameliorer avec exemples concrets
   - UN moment cle de la semaine (cite le transcript)
   - 3 recommandations specifiques avec quoi dire exactement

3. PROFIL LILIA (Agente SAC, Lun-Ven 12h-18h):
   - Meme format que Hamza

4. PROFIL SEKOU (Agent SAC, Sam-Dim):
   - Meme format que Hamza

5. PATTERNS EQUIPE:
   - Qu'est-ce que toute l'equipe fait bien?
   - Qu'est-ce que toute l'equipe doit ameliorer?
   - Objections les plus frequentes et comment y repondre
   - Clients recurrents qui rappellent souvent (signe de non-resolution)

6. TOP 5 ACTIONS PRIORITAIRES (numerotees, avec responsable et echeance)

Sois direct, concret, et cite des moments reels des appels. Pas de generalites vagues.
Le rapport sera lu par Hamza (le manager) et partage avec l'equipe."""


def generate_opus_report(weekly_data: dict) -> str:
    """Generate the weekly coaching report with Opus. Returns markdown text."""
    data_str = json.dumps(weekly_data, ensure_ascii=False, indent=2)

    # Truncate if too large (Opus has limits)
    if len(data_str) > 80000:
        data_str = data_str[:80000] + "\n... [donnees tronquees]"

    prompt = OPUS_PROMPT_TEMPLATE.format(data=data_str)

    log.info("Calling Opus for weekly report...")
    result = call_claude(prompt, model="opus", max_turns=1, timeout=300)

    if not result:
        log.error("Opus report generation failed")
        return "Erreur: le rapport Opus n'a pas pu etre genere."

    log.info("Opus report generated (%d chars)", len(result))
    return result
