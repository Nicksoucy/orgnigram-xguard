# Decompiled with PyLingual (https://pylingual.io)
# Internal filename: 'C:\\Users\\User\\crons\\telegram_bot.py'
# Bytecode version: 3.11a7e (3495)
# Source timestamp: 2026-04-18 13:39:58 UTC (1776519598)

global last_transcription
global chat_history
global ANTHROPIC_CLIENT
"""\nXGuard Telegram Bot — Interactive two-way bot.\nRuns continuously, listens for commands, responds in real-time.\n\nCommands:\n    /status     — Full cron status report\n    /short      — Compact summary\n    /failures   — Only show failed/errored tasks\n    /running    — Show currently running tasks\n    /stale      — Show tasks that haven\'t run in 48h+\n    /wsl        — Show WSL crontab entries\n    /help       — List commands\n\nRun:\n    python telegram_bot.py\n"""
import subprocess
import json
import logging
import asyncio
import os
import re
import sys
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler
sys.path.insert(0, 'C:\\Users\\User\\crons')
try:
    import obsidian_vault
    VAULT_ENABLED = True
except ImportError:
    VAULT_ENABLED = False
try:
    import ghl_tools
    GHL_ENABLED = True
except ImportError:
    GHL_ENABLED = False
BOT_TOKEN = '8040724534:AAHRLbkH2v0ji0swXQlv1aNrSxUXCwobRps'
AUTHORIZED_CHAT_ID = 8546527139
import anthropic
ANTHROPIC_CLIENT = None
def get_anthropic_client():
    """Lazy-init the Anthropic client. Tries OAuth token, then falls back to API key."""
    global ANTHROPIC_CLIENT
    if ANTHROPIC_CLIENT:
        return ANTHROPIC_CLIENT
    else:
        oauth_token = os.environ.get('CLAUDE_CODE_OAUTH_TOKEN', '')
        api_key = os.environ.get('ANTHROPIC_API_KEY', '')
        if oauth_token:
            ANTHROPIC_CLIENT = anthropic.Anthropic(api_key=oauth_token)
            log.info('Using env OAuth token for Claude API')
        else:
            if api_key:
                ANTHROPIC_CLIENT = anthropic.Anthropic(api_key=api_key)
                log.info('Using env API key for Claude API')
            else:
                token_file = Path('C:\\Users\\User\\.claude\\.credentials.json')
                if token_file.exists():
                    try:
                        creds = json.loads(token_file.read_text(encoding='utf-8'))
                        token = creds.get('claudeAiOauth', {}).get('accessToken', '')
                        if token:
                            ANTHROPIC_CLIENT = anthropic.Anthropic(api_key=token)
                            log.info('Using stored OAuth accessToken for Claude API')
                    except Exception as e:
                        log.error('Failed to read credentials: %s', e)
        return ANTHROPIC_CLIENT
chat_history = []
MAX_HISTORY = 20
last_transcription = {'url': None, 'language': None, 'duration': None, 'full_text': None, 'recap': None, 'saved_path': None, 'timestamp': None}
MASTER_SYSTEM_PROMPT = 'You are an AI assistant running inside a Telegram bot on the user\'s Windows machine.\nYou are not a generic chatbot — you are connected to a full automation stack:\n\nCAPABILITIES YOU HAVE (via bot commands, do NOT claim to lack these):\n- 🔗 GoHighLevel (GHL) CRM: connected via API. You CAN:\n    • Search contacts by name/email/phone\n    • Add notes to any contact\n    • Add tasks with due dates\n    • Send SMS immediately\n    • Schedule SMS for future delivery\n  When the user asks to do something with a GHL contact (like \"text John Friday 9am\"),\n  DO NOT deny having access. Confirm what you\'ll do and the bot will execute it.\n- 🧠 Obsidian vault (second brain): daily chat logs, transcriptions, snapshots, wiki\n    • Use /recall to search past notes\n- 📊 Pipeline stats (daily at 7:15 AM): closing rate, no-show rate, etc.\n- 🎤 Voice messages: transcribed on GPU\n- 🖼 Images: you can read them\n- 🎬 Instagram reels: transcribe + AI recap\n- 📅 Scheduled cron monitoring\n\nCOMMUNICATION STYLE:\n- Keep responses concise (under 500 words) — this is Telegram\n- Match the user\'s language (French or English)\n- Don\'t pretend you lack memory — you have chat_history passed to you\n- Don\'t deny having capabilities listed above\n- Be specific and actionable, not generic\n\nCRM ACTIONS:\nWhen the user wants to do something with a GHL contact, respond with a brief confirmation\n(e.g., \"Scheduling SMS to Jonathon Dick for Friday at 9am: \'Hey John...\'\") — the bot will execute the action.\nDon\'t say \"I need the API key\" or \"I can\'t access GHL\" — you ARE connected.\n'
IGNORED_TASKS = {'OneDrive Reporting Task-S-1-5-21-1942389513-315412866-111657725-1001', 'OneDrive Startup Task-S-1-5-21-1942389513-315412866-111657725-1001', 'OneDrive Standalone Update Task-S-1-5-21-1942389513-315412866-111657725-1001', 'OpenClaw Gateway', 'NVIDIA App SelfUpdate_{B2FE1952-0186-46C3-BAEC-A80AA35AC5B8}'}
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s — %(message)s')
log = logging.getLogger('xguard_bot')
def authorized(func):
    """Only allow the authorized user."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_chat.id!= AUTHORIZED_CHAT_ID:
            await update.message.reply_text('⛔ Unauthorized.')
            return
        else:
            return await func(update, context)
    return wrapper
def get_windows_tasks():
    """Fetch custom scheduled tasks from Windows Task Scheduler."""
    ps_cmd = '\n    Get-ScheduledTask | Where-Object {$_.TaskPath -eq \'\\\' -and $_.TaskName -notmatch \'NVIDIA|OneDrive|OpenClaw Gateway\'} | ForEach-Object {\n        $info = Get-ScheduledTaskInfo -TaskName $_.TaskName -ErrorAction SilentlyContinue\n        [PSCustomObject]@{\n            Name        = $_.TaskName\n            State       = [string]$_.State\n            LastRun     = if($info.LastRunTime) {$info.LastRunTime.ToString(\'yyyy-MM-dd HH:mm:ss\')} else {\'Never\'}\n            NextRun     = if($info.NextRunTime) {$info.NextRunTime.ToString(\'yyyy-MM-dd HH:mm:ss\')} else {\'N/A\'}\n            LastResult  = $info.LastTaskResult\n        }\n    } | ConvertTo-Json -Depth 2\n    '
    try:
        result = subprocess.run(['powershell.exe', '-NoProfile', '-Command', ps_cmd], capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return []
        data = json.loads(result.stdout)
        if isinstance(data, dict):
            data = [data]
        return data
    except Exception as e:
        log.error('Failed to get Windows tasks: %s', e)
        return []
def get_wsl_crontab():
    """Fetch WSL crontab entries."""
    try:
        result = subprocess.run(['wsl', 'crontab', '-l'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and result.stdout.strip():
            return [l.strip() for l in result.stdout.splitlines() if l.strip() and (not l.startswith('#'))]
        return []
    except Exception:
        return []
def result_code_to_status(code):
    codes = {0: ('OK', '✅'), 267009: ('Running', '⏳'), 267011: ('Queued', '⏳'), 267014: ('Stopped', '⏸'), 2147750687: ('Already running', '⚠️'), 3221225786: ('App terminated', '❌')}
    if code in codes:
        return codes[code]
    else:
        if code == 0:
            return ('OK', '✅')
        else:
            return (f'Code {code}', '❌')
def is_stale(last_run_str, hours=48):
    if last_run_str in ['Never', 'N/A', None, '']:
        return True
    try:
        last_run = datetime.strptime(last_run_str, '%Y-%m-%d %H:%M:%S')
        return datetime.now() - last_run > timedelta(hours=hours)
    except Exception:
        return False
_sp = 'C:\\Users\\User\\AppData\\Local\\Programs\\Python\\Python311\\Lib\\site-packages'
for _pkg in ['nvidia\\cublas\\bin', 'nvidia\\cudnn\\bin']:
    _p = os.path.join(_sp, _pkg)
    if os.path.isdir(_p) and _p not in os.environ.get('PATH', ''):
            os.environ['PATH'] = _p + os.pathsep + os.environ.get('PATH', '')
INSTAGRAM_RE = re.compile('https?://(?:www\\.)?instagram\\.com/(?:reel|p|tv)/[\\w-]+')
VIDEO_DIR = Path('C:/Users/User/instagram_videos')
VIDEO_DIR.mkdir(parents=True, exist_ok=True)
def download_instagram_video(url):
    """Download Instagram video using yt-dlp. Returns path to downloaded file."""
    out_template = str(VIDEO_DIR / '%(id)s.%(ext)s')
    try:
        result = subprocess.run(['yt-dlp', '--no-playlist', '--no-warnings', '-f', 'best', '-o', out_template, '--print', 'after_move:filepath', url], capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            log.error('yt-dlp error: %s', result.stderr[:300])
            return (None, result.stderr[:200])
        filepath = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else None
        if filepath and Path(filepath).exists():
            return (filepath, None)
        files = sorted(VIDEO_DIR.glob('*'), key=lambda f: f.stat().st_mtime, reverse=True)
        if files:
            return (str(files[0]), None)
        return (None, 'Download completed but file not found')
    except subprocess.TimeoutExpired:
        return (None, 'Download timed out (120s)')
    except Exception as e:
        return (None, str(e))
def transcribe_video(filepath):
    """Transcribe video audio using faster-whisper with GPU. Auto-detects language."""
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel('medium', device='cuda', compute_type='int8_float16')
        segments, info = model.transcribe(filepath, beam_size=3, vad_filter=True)
        text_parts = []
        for seg in segments:
            text_parts.append(seg.text.strip())
        full_text = ' '.join(text_parts)
        return (full_text, info.language, info.duration)
    except Exception as e:
        log.error('Transcription error: %s', e)
        try:
            from faster_whisper import WhisperModel
            model = WhisperModel('small', device='cpu', compute_type='int8')
            segments, info = model.transcribe(filepath, beam_size=3, vad_filter=True)
            full_text = ' '.join((seg.text.strip() for seg in segments))
            return (full_text, info.language, info.duration)
        except Exception as e2:
            return (None, None, None)
def _find_claude_exe():
    """Find the latest claude.exe version dynamically."""
    base = Path('C:\\Users\\User\\AppData\\Local\\Packages\\Claude_pzs8sxrjxfjjc\\LocalCache\\Roaming\\Claude\\claude-code')
    if not base.exists():
        return
    else:
        versions = sorted([d for d in base.iterdir() if d.is_dir()], key=lambda d: d.name, reverse=True)
        for v in versions:
            exe = v / 'claude.exe'
            if exe.exists():
                return str(exe)
CLAUDE_EXE = _find_claude_exe() or 'C:\\Users\\User\\AppData\\Local\\Packages\\Claude_pzs8sxrjxfjjc\\LocalCache\\Roaming\\Claude\\claude-code\\2.1.111\\claude.exe'
import threading
_cli_lock = threading.Lock()
def _single_claude_call(prompt, system, model='haiku', timeout=60):
    """One attempt to call Claude CLI. Returns (output, error_reason) tuple."""
    exe = _find_claude_exe() or CLAUDE_EXE
    if not Path(exe).exists():
        return (None, f'claude.exe not found at {exe}')
    env = os.environ.copy()
    env['CLAUDE_CODE_GIT_BASH_PATH'] = 'C:\\Program Files\\Git\\bin\\bash.exe'
    env['HOME'] = 'C:\\Users\\User'
    env['USERPROFILE'] = 'C:\\Users\\User'
    cmd = [exe, '-p', '--model', model, '--max-turns', '1']
    if system:
        cmd.extend(['--append-system-prompt', system])
    proc = None
    try:
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env, encoding='utf-8', errors='replace')
        stdout, stderr = proc.communicate(input=prompt, timeout=timeout)
        if proc.returncode == 0 and stdout.strip():
            return (stdout.strip(), None)
        return (None, f"rc={proc.returncode}, stderr={(stderr or '')[:200]}")
    except subprocess.TimeoutExpired:
        try:
            if proc:
                proc.kill()
                proc.communicate(timeout=5)
        except Exception:
            pass
        return (None, f'timeout after {timeout}s')
    except Exception as e:
        return (None, f'exception: {e}')
def call_claude_cli(prompt, system=None, model='haiku', max_retries=2, base_timeout=60):
    """
    Call Claude CLI with:
    - Serialization (lock) so concurrent callers don't collide
    - Automatic retry with exponential backoff
    - Fallback to sonnet if haiku keeps failing
    - Truncation of very long prompts
    """
    MAX_PROMPT = 20000
    if len(prompt) > MAX_PROMPT:
        log.warning('Truncating prompt from %d to %d chars', len(prompt), MAX_PROMPT)
        prompt = prompt[:MAX_PROMPT] + '\n\n[...truncated]'
    with _cli_lock:
        last_error = None
        for attempt in range(max_retries + 1):
            timeout = base_timeout + attempt * 30
            current_model = model if attempt < max_retries else 'sonnet'
            log.info('Claude CLI attempt %d/%d (model=%s, timeout=%ds)', attempt + 1, max_retries + 1, current_model, timeout)
            output, error = _single_claude_call(prompt, system, model=current_model, timeout=timeout)
            if output:
                if attempt > 0:
                    log.info('Claude CLI succeeded on retry %d', attempt)
                return output
            last_error = error
            log.warning('Claude CLI attempt %d failed: %s', attempt + 1, error)
            if attempt < max_retries:
                backoff = 2 ** attempt
                import time
                time.sleep(backoff)
        log.error('Claude CLI FAILED after %d attempts. Last error: %s', max_retries + 1, last_error)
        return None
def summarize_with_claude(text, language):
    """Use Claude to create an intelligent recap of transcribed text."""
    lang_name = {'fr': 'French', 'en': 'English', 'es': 'Spanish', 'pt': 'Portuguese'}.get(language, language)
    system = f'You are summarizing an Instagram video transcription. The video is in {lang_name}. Write your recap in the SAME language as the video ({lang_name}). Provide: 1) A 1-2 sentence TL;DR, 2) Main points (3-5 bullets), 3) Any notable takeaways. Be concise. Use emojis sparingly. Output plain text, no markdown headers.'
    return call_claude_cli(text, system=system)
def summarize_text(text, duration=None):
    """Create a simple recap of the transcribed text."""
    words = text.split()
    word_count = len(words)
    lines = []
    if duration:
        mins = int(duration // 60)
        secs = int(duration % 60)
        lines.append(f'⏱ Duration: {mins}m{secs}s')
    lines.append(f'📝 Words: {word_count}')
    lines.append('')
    if word_count > 150:
        preview = ' '.join(words[:100]) + '...'
        lines.append(f'<b>Preview:</b>\n{preview}')
    else:
        lines.append(f'<b>Full text:</b>\n{text}')
    return '\n'.join(lines)
@authorized
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('🤖 <b>XGuard Second-Brain Bot</b> — Online!\n\n💬 <b>Chat:</b> Just talk to me like ChatGPT — ask anything!\n\n<b>🧠 Memory / Vault:</b>\n/recall &lt;query&gt; — Ask about anything in your vault\n/search &lt;query&gt; — Raw grep-style search\nOr just say: \"what did I transcribe about X?\"\n\n<b>📋 Cron Commands:</b>\n/status — Full cron report\n/short — Compact summary\n/failures — Failed tasks only\n/running — Currently running tasks\n/stale — Tasks not run in 48h+\n/wsl — WSL crontab entries\n\n<b>🎬 Instagram:</b>\nPaste any Instagram reel link\n→ Downloads, transcribes, AI recap, extracts entities\n\n<b>Other:</b>\n/clear — Reset chat history\n/help — This message', parse_mode='HTML')
@authorized
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_start(update, context)
@authorized
async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('⏳ Collecting task data...')
    tasks = get_windows_tasks()
    wsl = get_wsl_crontab()
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    lines = [f'📋 <b>Full Cron Report</b>  —  {now}', '']
    for t in sorted(tasks, key=lambda x: x['Name']):
        status_text, icon = result_code_to_status(t.get('LastResult', 0))
        state = t.get('State', '?')
        if state == 'Disabled':
            state_icon = '⏸'
        else:
            if state == 'Running':
                state_icon = '▶'
            else:
                state_icon = '✅'
        stale_flag = ' 🔴' if is_stale(t.get('LastRun'), 48) and state!= 'Disabled' else ''
        lines.append(f"{state_icon} <b>{t['Name']}</b>{stale_flag}")
        lines.append(f"    {icon} {status_text} | Last: {t.get('LastRun', '?')}")
        lines.append(f"    Next: {t.get('NextRun', 'N/A')}")
        lines.append('')
    if wsl:
        lines.append(f'🐧 <b>WSL Crontab ({len(wsl)})</b>')
        for c in wsl:
            lines.append(f'  <code>{c[:80]}</code>')
    report = '\n'.join(lines)
    if len(report) > 4000:
        for i in range(0, len(report), 3900):
            chunk = report[i:i + 3900]
            await update.message.reply_text(chunk, parse_mode='HTML')
    else:
        await update.message.reply_text(report, parse_mode='HTML')
@authorized
async def cmd_short(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tasks = get_windows_tasks()
    wsl = get_wsl_crontab()
    running = [t for t in tasks if t['State'] == 'Running']
    ready = [t for t in tasks if t['State'] == 'Ready']
    disabled = [t for t in tasks if t['State'] == 'Disabled']
    failed = [t for t in tasks if t.get('LastResult', 0) not in [0, 267009, 267011]]
    stale = [t for t in ready if is_stale(t.get('LastRun'), 48)]
    msg = f'📊 <b>Quick Summary</b>\n\n▶ Running: {len(running)}\n✅ Ready: {len(ready)}\n⏸ Disabled: {len(disabled)}\n❌ Failed: {len(failed)}\n🔴 Stale (48h+): {len(stale)}\n🐧 WSL crons: {len(wsl)}'
    if failed:
        msg += '\n\n<b>Failed:</b>'
        for t in failed:
            status_text, icon = result_code_to_status(t.get('LastResult', (-1)))
            msg += f"\n  {icon} {t['Name']} — {status_text}"
    await update.message.reply_text(msg, parse_mode='HTML')
@authorized
async def cmd_failures(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tasks = get_windows_tasks()
    failed = [t for t in tasks if t.get('LastResult', 0) not in [0, 267009, 267011]]
    if not failed:
        await update.message.reply_text('✅ No failures! All tasks are healthy.')
        return
    else:
        lines = [f'❌ <b>{len(failed)} Failed Task(s)</b>', '']
        for t in failed:
            status_text, icon = result_code_to_status(t.get('LastResult', (-1)))
            lines.append(f"{icon} <b>{t['Name']}</b>")
            lines.append(f'    {status_text}')
            lines.append(f"    Last: {t.get('LastRun', 'N/A')}")
            lines.append('')
        await update.message.reply_text('\n'.join(lines), parse_mode='HTML')
@authorized
async def cmd_running(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tasks = get_windows_tasks()
    running = [t for t in tasks if t['State'] == 'Running']
    if not running:
        await update.message.reply_text('⏸ No tasks currently running.')
        return
    else:
        lines = [f'▶ <b>{len(running)} Running Task(s)</b>', '']
        for t in running:
            lines.append(f"▶ <b>{t['Name']}</b>")
            lines.append(f"    Started: {t.get('LastRun', '?')}")
            lines.append('')
        await update.message.reply_text('\n'.join(lines), parse_mode='HTML')
@authorized
async def cmd_stale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tasks = get_windows_tasks()
    stale = [t for t in tasks if t['State'] == 'Ready' and is_stale(t.get('LastRun'), 48)]
    if not stale:
        await update.message.reply_text('✅ All tasks ran within the last 48 hours.')
        return
    else:
        lines = [f'🔴 <b>{len(stale)} Stale Task(s) (48h+)</b>', '']
        for t in stale:
            lines.append(f"🔴 <b>{t['Name']}</b>")
            lines.append(f"    Last run: {t.get('LastRun', 'Never')}")
            lines.append('')
        await update.message.reply_text('\n'.join(lines), parse_mode='HTML')
@authorized
async def cmd_wsl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wsl = get_wsl_crontab()
    if not wsl:
        await update.message.reply_text('🐧 No WSL crontab entries found.')
        return
    else:
        lines = [f'🐧 <b>WSL Crontab ({len(wsl)} entries)</b>', '']
        for c in wsl:
            lines.append(f'<code>{c}</code>')
        await update.message.reply_text('\n'.join(lines), parse_mode='HTML')
@authorized
async def handle_instagram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Download, transcribe, and summarize an Instagram video."""
    global last_transcription
    text = (update.message.text or '').strip()
    match = INSTAGRAM_RE.search(text)
    if not match:
        return
    else:
        url = match.group(0)
        extra_instruction = text.replace(url, '').strip()
        await update.message.reply_text(f'📥 Downloading video...\n<code>{url}</code>', parse_mode='HTML')
        loop = asyncio.get_event_loop()
        filepath, error = await loop.run_in_executor(None, download_instagram_video, url)
        if not filepath:
            await update.message.reply_text(f'❌ Download failed:\n{error}')
            return
        else:
            await update.message.reply_text('🎤 Transcribing audio (GPU)...')
            full_text, language, duration = await loop.run_in_executor(None, transcribe_video, filepath)
            if not full_text:
                await update.message.reply_text('❌ Transcription failed. The video may have no audio.')
                return
            else:
                mins = int(duration // 60) if duration else 0
                secs = int(duration % 60) if duration else 0
                lang_name = {'fr': 'Français', 'en': 'English', 'es': 'Español', 'pt': 'Português'}.get(language, language or '?')
                header = f'🎬 <b>Instagram Video</b>\n🌐 {lang_name} | ⏱ {mins}m{secs}s | 📝 {len(full_text.split())} words'
                await update.message.reply_text(header, parse_mode='HTML')
                await update.message.reply_text('🧠 Getting recap from Claude...')
                loop = asyncio.get_event_loop()
                recap = await loop.run_in_executor(None, summarize_with_claude, full_text, language)
                if recap:
                    await update.message.reply_text(f'📋 <b>Recap:</b>\n\n{recap}', parse_mode='HTML')
                else:
                    await update.message.reply_text('⚠️ AI recap failed, sending raw text only.')
                full_header = '📄 <b>Full Transcription:</b>\n\n'
                full_msg = full_header + full_text
                if len(full_msg) > 4000:
                    await update.message.reply_text(full_header + full_text[:3900], parse_mode='HTML')
                    remaining = full_text[3900:]
                    for i in range(0, len(remaining), 4000):
                        await update.message.reply_text(remaining[i:i + 4000])
                else:
                    await update.message.reply_text(full_msg, parse_mode='HTML')
                if VAULT_ENABLED:
                    try:
                        saved_path = await loop.run_in_executor(None, obsidian_vault.save_transcription, url, language, duration, full_text, recap)
                        await update.message.reply_text('💾 Saved to Obsidian vault')
                        if saved_path:
                            source_ref = Path(saved_path).stem
                            await update.message.reply_text('🧠 Extracting entities & concepts...')
                            summary = await loop.run_in_executor(None, obsidian_vault.ingest_source, full_text, source_ref, 'transcription')
                            if summary.get('entities') or summary.get('concepts'):
                                await update.message.reply_text(f"🔗 Updated {summary.get('entities', 0)} entity page(s) and {summary.get('concepts', 0)} concept page(s).")
                    except Exception as e:
                        log.error('Vault save/ingest failed: %s', e)
                last_transcription = {'url': url, 'language': language, 'duration': duration, 'full_text': full_text, 'recap': recap or '', 'saved_path': saved_path if VAULT_ENABLED else None, 'timestamp': datetime.now()}
                chat_history.append(('user', f'[Instagram video] {url}'))
                summary_for_history = f'[Transcribed {lang_name} video, {mins}m{secs}s]'
                if recap:
                    summary_for_history += f'\n\nRecap: {recap[:800]}'
                summary_for_history += f'\n\n[Full transcript available — {len(full_text)} chars]'
                chat_history.append(('assistant', summary_for_history))
                if len(chat_history) > MAX_HISTORY * 2:
                    del chat_history[:2]
                instruction_clean = extra_instruction
                if instruction_clean:
                    instruction_clean = re.sub('[?&]?igsh=[A-Za-z0-9=]+', '', instruction_clean).strip()
                    instruction_clean = re.sub('^/\\??', '', instruction_clean).strip()
                if instruction_clean and len(instruction_clean) > 5 and any((c.isalpha() for c in instruction_clean)):
                            await update.message.reply_text(f'💭 Answering: <i>{instruction_clean[:200]}</i>', parse_mode='HTML')
                            answer_system = 'You are a helpful assistant. The user sent an Instagram video with a specific question/task. Use ONLY the transcript below to answer. Be concise and specific. If they ask about a tool/skill/product/person mentioned, name it and quote relevant context. Match the user\'s language.'
                            answer_prompt = f"Transcript:\n{full_text[:3500]}\n\nRecap:\n{recap or '(no recap)'}\n\nUser\'s question: {instruction_clean}"
                            answer = await loop.run_in_executor(None, call_claude_cli, answer_prompt, answer_system)
                            if answer:
                                if len(answer) > 4000:
                                    for i in range(0, len(answer), 4000):
                                        await update.message.reply_text(answer[i:i + 4000])
                                else:
                                    await update.message.reply_text(answer)
                                chat_history.append(('user', instruction_clean))
                                chat_history.append(('assistant', answer))
                            else:
                                await update.message.reply_text(f'⚠️ Couldn\'t generate an answer to your question, but the transcript + recap are saved.\nTry asking again: <i>{instruction_clean[:100]}</i>', parse_mode='HTML')
                try:
                    Path(filepath).unlink(missing_ok=True)
                except Exception:
                    return None
async def handle_ghl_intent(update, context, user_message, image_path=None):
    """
    When the user's message involves a GHL contact action, this orchestrates:
    1. Ask Claude to identify the contact name + action from the message
    2. Look up the contact in GHL
    3. Execute the action (note, task, SMS, scheduled SMS)
    Returns True if handled, False if not GHL-related.
    """
    if not GHL_ENABLED:
        return False
    loop = asyncio.get_event_loop()
    intent_system = 'You are a GHL (GoHighLevel CRM) intent classifier. Extract the action the user wants to perform on a contact. Return ONLY valid JSON, no other text.\n\nFormat:\n{\n  "is_ghl_action": true/false,\n  "contact_name": "first last name mentioned, or name visible in any screenshot",\n  "action": "add_note|add_task|send_sms|schedule_sms|lookup|none",\n  "message": "text to send or task title/body",\n  "scheduled_time": "YYYY-MM-DD HH:MM or null",\n  "days_from_now": 0\n}\n\nRules:\n- is_ghl_action=true only if the user clearly wants to do something WITH a CRM contact\n- If user says \'remind me to text him Friday at 9am\' → action=schedule_sms with scheduled_time\n- If user says \'add a note\' → action=add_note\n- If user says \'call him\' → action=add_task with title=\'Call <name>\'\n- If just asking who someone is → action=lookup\n- Parse relative dates (next Friday, tomorrow, in 3 days) into days_from_now\n- Current date context: today is ' + datetime.now().strftime('%Y-%m-%d (%A)')
    prompt = user_message
    if image_path:
        prompt = f'{user_message}\n\nScreenshot attached: @{image_path}'
    intent_response = await loop.run_in_executor(None, call_claude_cli, prompt, intent_system)
    if not intent_response:
        return False
    start = intent_response.find('{')
    end = intent_response.rfind('}')
    if start < 0 or end <= start:
        return False
    try:
        intent = json.loads(intent_response[start:end + 1])
        if not intent.get('is_ghl_action'):
            return False
        contact_name = intent.get('contact_name', '').strip()
        action = intent.get('action', 'none')
        message = intent.get('message', '')
        days_from_now = intent.get('days_from_now', 0) or 0
        scheduled_time = intent.get('scheduled_time')
        if not contact_name:
            await update.message.reply_text('⚠️ I didn\'t catch which contact you meant. Can you say the name?')
            return True
        await update.message.reply_text(f'🔍 Looking up <b>{contact_name}</b> in GHL...', parse_mode='HTML')
        contact, summary = await loop.run_in_executor(None, ghl_tools.contact_lookup_summary, contact_name)
        if not contact:
            await update.message.reply_text(summary)
            return True
        if isinstance(contact, list):
            await update.message.reply_text(f'{summary}\n\nWhich one? Reply with the number or full name.')
            return True
        contact_id = contact['id']
        contact_display = contact['name']
        if action == 'lookup':
            await update.message.reply_text(f'👤 <b>{contact_display}</b>\n{summary}', parse_mode='HTML')
        elif action == 'add_note':
            note_body = f"{message}\n\n— via Telegram bot, {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            note_id = await loop.run_in_executor(None, ghl_tools.add_note, contact_id, note_body)
            if note_id:
                await update.message.reply_text(f'✅ Note added to <b>{contact_display}</b>', parse_mode='HTML')
            else:
                await update.message.reply_text('❌ Failed to add note. Check logs.')
        elif action == 'add_task':
            due_iso = None
            if scheduled_time:
                try:
                    dt = datetime.strptime(scheduled_time, '%Y-%m-%d %H:%M')
                    due_iso = dt.strftime('%Y-%m-%dT%H:%M:%S-05:00')
                except Exception:
                    pass
            elif days_from_now > 0:
                due = datetime.now() + timedelta(days=days_from_now)
                due = due.replace(hour=9, minute=0, second=0, microsecond=0)
                due_iso = due.strftime('%Y-%m-%dT%H:%M:%S-05:00')
            title = message or f'Task for {contact_display}'
            task_id = await loop.run_in_executor(None, ghl_tools.add_task, contact_id, title[:200], message, due_iso)
            if task_id:
                due_str = f' (due {scheduled_time or due_iso})' if due_iso else ''
                await update.message.reply_text(f'✅ Task added to <b>{contact_display}</b>{due_str}\n<i>{title[:100]}</i>', parse_mode='HTML')
            else:
                await update.message.reply_text('❌ Failed to add task.')
        elif action == 'schedule_sms':
            try:
                if scheduled_time:
                    dt = datetime.strptime(scheduled_time, '%Y-%m-%d %H:%M')
                else:
                    dt = datetime.now() + timedelta(days=max(days_from_now, 1))
                    dt = dt.replace(hour=9, minute=0, second=0, microsecond=0)
                iso = dt.strftime('%Y-%m-%dT%H:%M:%S-05:00')
            except Exception:
                dt = datetime.now() + timedelta(days=1)
                iso = dt.strftime('%Y-%m-%dT09:00:00-05:00')
            msg_id = await loop.run_in_executor(None, ghl_tools.schedule_sms, contact_id, message, iso)
            if msg_id:
                await update.message.reply_text(f"✅ SMS scheduled to <b>{contact_display}</b> for {dt.strftime('%A %Y-%m-%d at %H:%M')}:\n\n<i>{message}</i>", parse_mode='HTML')
            else:
                title = f'Text {contact_display}'
                body = f'Scheduled text: {message}'
                task_id = await loop.run_in_executor(None, ghl_tools.add_task, contact_id, title, body, iso)
                if task_id:
                    await update.message.reply_text(f"⚠️ SMS scheduling failed, but added as a reminder task instead for {dt.strftime('%A %H:%M')}.")
                else:
                    await update.message.reply_text('❌ Failed to schedule SMS and fallback task failed.')
        elif action == 'send_sms':
            msg_id = await loop.run_in_executor(None, ghl_tools.send_sms, contact_id, message)
            if msg_id:
                await update.message.reply_text(f'✅ SMS sent to <b>{contact_display}</b>:\n<i>{message}</i>', parse_mode='HTML')
            else:
                await update.message.reply_text('❌ Failed to send SMS.')
        else:
            await update.message.reply_text(f'🤔 I found {contact_display} but wasn\'t sure what action to take.')
        return True
    except Exception as e:
        log.warning('Intent JSON parse failed: %s', e)
        return False
@authorized
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo messages — pass the image to Claude vision."""
    photos = update.message.photo or []
    document = update.message.document
    image_source = None
    if photos:
        image_source = photos[(-1)]
    else:
        if document and document.mime_type and document.mime_type.startswith('image/'):
                    image_source = document
    if not image_source:
        return
    caption = (update.message.caption or '').strip()
    await update.message.reply_text('🖼️ Analyzing image...')
    try:
        photo_file = await image_source.get_file()
        photo_dir = Path('C:\\Users\\User\\instagram_videos')
        photo_dir.mkdir(parents=True, exist_ok=True)
        photo_path = photo_dir / f"photo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        await photo_file.download_to_drive(str(photo_path))
    except Exception as e:
        log.error('Photo download failed: %s', e)
        await update.message.reply_text('❌ Failed to download image.')
        return None
    if caption and GHL_ENABLED:
        handled = await handle_ghl_intent(update, context, caption, image_path=str(photo_path))
        if handled:
            try:
                photo_path.unlink(missing_ok=True)
            except Exception:
                pass
            return None
    if caption:
        user_intent = caption
    else:
        user_intent = 'What is this image showing? Describe what you see and respond helpfully. If it looks like something I need to take action on, suggest what to do.'
    system = MASTER_SYSTEM_PROMPT + '\n\nThe user just sent an IMAGE. Read it carefully. If it\'s a screenshot of a GHL contact, you can perform actions on that contact — don\'t just describe the screenshot, offer to do something with it.'
    prompt = f'{user_intent}\n\nImage: @{photo_path}'
    if chat_history:
        recent = chat_history[(-4):]
        history_ctx = '\n\nRecent conversation:\n' + '\n'.join((f"{('User' if role == 'user' else 'You')}: {msg}" for role, msg in recent))
        prompt = history_ctx + '\n\nNew message with image:\n' + prompt
    await update.message.chat.send_action('typing')
    loop = asyncio.get_event_loop()
    reply = await loop.run_in_executor(None, call_claude_cli, prompt, system)
    try:
        photo_path.unlink(missing_ok=True)
    except Exception:
        pass
    if reply:
        msg_log = f'[photo] {caption}' if caption else '[photo only]'
        chat_history.append(('user', msg_log))
        chat_history.append(('assistant', reply))
        if len(chat_history) > MAX_HISTORY * 2:
            del chat_history[:2]
        if VAULT_ENABLED:
            try:
                await loop.run_in_executor(None, obsidian_vault.append_chat_exchange, msg_log, reply)
            except Exception:
                pass
        if len(reply) > 4000:
            for i in range(0, len(reply), 4000):
                await update.message.reply_text(reply[i:i + 4000])
        else:
            await update.message.reply_text(reply)
    else:
        await update.message.reply_text('⚠️ Claude didn\'t respond to the image. Try again or describe what you want help with.')
@authorized
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice messages — transcribe with GPU then process as text."""
    voice = update.message.voice or update.message.audio
    if not voice:
        return
    else:
        await update.message.reply_text('🎤 Transcribing your voice...')
        try:
            voice_file = await voice.get_file()
            voice_path = Path('C:\\Users\\User\\instagram_videos') / f"voice_{datetime.now().strftime('%Y%m%d_%H%M%S')}.ogg"
            await voice_file.download_to_drive(str(voice_path))
        except Exception as e:
            log.error('Voice download failed: %s', e)
            await update.message.reply_text('❌ Failed to download voice message.')
            return None
        loop = asyncio.get_event_loop()
        full_text, language, duration = await loop.run_in_executor(None, transcribe_video, str(voice_path))
        try:
            voice_path.unlink(missing_ok=True)
        except Exception:
            pass
        if not full_text:
            await update.message.reply_text('❌ Couldn\'t transcribe the audio. Try again?')
            return
        else:
            lang_name = {'fr': 'FR', 'en': 'EN', 'es': 'ES'}.get(language, language or '?')
            dur_sec = int(duration) if duration else 0
            await update.message.reply_text(f'📝 <b>Transcription</b> ({lang_name}, {dur_sec}s):\n\n<i>{full_text[:1000]}</i>', parse_mode='HTML')
            if INSTAGRAM_RE.search(full_text):
                await update.message.reply_text('🔗 Instagram link detected in voice — but paste it as text for best results.')
            text_lower = full_text.lower()
            recall_triggers = ['what did i', 'qu\'est-ce que j\'ai', 'do you remember', 'tu te souviens', 'what was', 'c\'etait quoi', 'find that', 'trouve', 'search for', 'cherche']
            if VAULT_ENABLED and any((t in text_lower for t in recall_triggers)):
                context.args = full_text.split()
                await cmd_recall(update, context)
            else:
                ghl_triggers = ['remind me', 'schedule', 'text him', 'text her', 'text them', 'call him', 'call her', 'add a note', 'add note', 'send sms', 'from go high level', 'from ghl', 'contact', 'reach out', 'follow up with', 'nurture', 'go high level', 'gave you access', 'prepare', 'set that up', 'two messages']
                if GHL_ENABLED and any((t in text_lower for t in ghl_triggers)):
                        handled = await handle_ghl_intent(update, context, full_text)
                        if handled:
                            return
                await update.message.chat.send_action('typing')
                system = MASTER_SYSTEM_PROMPT + '\n\nThe user just sent a VOICE MESSAGE which was transcribed. Interpret intent over typos.'
                history_context = ''
                if chat_history:
                    recent = chat_history[(-6):]
                    history_context = '\n\nRecent conversation:\n' + '\n'.join((f"{('User' if role == 'user' else 'You')}: {msg}" for role, msg in recent)) + '\n\nNew user message (from voice):\n'
                prompt = history_context + full_text
                reply = await loop.run_in_executor(None, call_claude_cli, prompt, system)
                if reply:
                    chat_history.append(('user', f'[voice] {full_text}'))
                    chat_history.append(('assistant', reply))
                    if len(chat_history) > MAX_HISTORY * 2:
                        del chat_history[:2]
                    if VAULT_ENABLED:
                        try:
                            await loop.run_in_executor(None, obsidian_vault.append_chat_exchange, f'[voice] {full_text}', reply)
                        except Exception:
                            pass
                    if len(reply) > 4000:
                        for i in range(0, len(reply), 4000):
                            await update.message.reply_text(reply[i:i + 4000])
                    else:
                        await update.message.reply_text(reply)
                else:
                    await update.message.reply_text('⚠️ Claude didn\'t respond. Try again or type your message.')
@authorized
async def cmd_recall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search the vault for a query and synthesize an answer from matching notes."""
    query = ' '.join(context.args) if context.args else ''
    if not query:
        await update.message.reply_text('Usage: <code>/recall &lt;query&gt;</code>\nExample: <code>/recall agent skills</code>', parse_mode='HTML')
        return
    else:
        await update.message.reply_text(f'🔍 Searching vault for: <i>{query}</i>', parse_mode='HTML')
        loop = asyncio.get_event_loop()
        context_text = await loop.run_in_executor(None, obsidian_vault.recall, query, 5)
        if not context_text:
            await update.message.reply_text(f'🤷 Nothing in the vault matches <i>{query}</i>.', parse_mode='HTML')
            return
        else:
            system = 'You are a second-brain recall assistant. The user asked a question and we found matching notes in their Obsidian vault. Synthesize a concise answer (under 400 words) using ONLY the information in the notes below. Cite specific note filenames in [[brackets]]. If the notes don\'t fully answer, say so. Match the user\'s language (French or English). Do not invent facts.'
            prompt = f'User question: {query}\n\nVault context:\n{context_text}'
            reply = await loop.run_in_executor(None, call_claude_cli, prompt, system)
            if reply:
                if len(reply) > 4000:
                    for i in range(0, len(reply), 4000):
                        await update.message.reply_text(reply[i:i + 4000])
                else:
                    await update.message.reply_text(reply)
            else:
                await update.message.reply_text('⚠️ Claude didn\'t respond. Vault search returned data but synthesis failed.')
@authorized
async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Raw grep-style search — returns matching notes and snippets."""
    query = ' '.join(context.args) if context.args else ''
    if not query:
        await update.message.reply_text('Usage: <code>/search &lt;query&gt;</code>', parse_mode='HTML')
        return
    else:
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, obsidian_vault.search_notes, query, None, 10)
        if not results:
            await update.message.reply_text(f'🤷 No matches for <i>{query}</i>.', parse_mode='HTML')
            return
        else:
            lines = [f'🔍 <b>{len(results)} matches for</b> <i>{query}</i>\n']
            vault_path = obsidian_vault.VAULT
            for path, matches in results[:10]:
                try:
                    rel = Path(path).relative_to(vault_path)
                    lines.append(f'📄 <code>{rel}</code>')
                    for m in matches[:2]:
                        snippet = m[:150]
                        lines.append(f'   <i>{snippet}</i>')
                    lines.append('')
                except Exception:
                    pass
            msg = '\n'.join(lines)
            if len(msg) > 4000:
                msg = msg[:4000] + '\n\n...[truncated]'
            await update.message.reply_text(msg, parse_mode='HTML')
@authorized
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle any text that isn\'t a command — routes to Claude for natural chat."""
    raw_text = (update.message.text or '').strip()
    text = raw_text.lower()
    if awaiting_response:
        handled = await handle_fathom_followup_text(update, context, raw_text)
        if handled:
            return
    if INSTAGRAM_RE.search(raw_text):
        await handle_instagram(update, context)
    else:
        if any((w in text for w in ['status', 'cron status', 'task status', 'how are crons', 'cron report'])):
            await cmd_short(update, context)
        else:
            if any((w in text for w in ['/failures', 'any failure', 'any error', 'failed task', 'broken task'])):
                await cmd_failures(update, context)
            else:
                if any((w in text for w in ['what\'s running', 'whats running', 'currently running', 'active task'])):
                    await cmd_running(update, context)
                else:
                    recall_triggers = ['what did i', 'qu\'est-ce que j\'ai', 'qu est ce que j ai', 'do you remember', 'tu te souviens', 'you remember', 'what was', 'c\'etait quoi', 'que disait', 'find that', 'trouve', 'search for', 'cherche', 'what did we talk', 'on a parle de', 'we talked about', 'last week', 'yesterday', 'recently', 'récemment', 'what did the video', 'the instagram', 'the reel', 'transcription about', 'mes notes sur', 'my notes about']
                    if VAULT_ENABLED and any((t in text for t in recall_triggers)):
                        context.args = raw_text.split()
                        await cmd_recall(update, context)
                    else:
                        ghl_triggers = ['remind me', 'schedule', 'text him', 'text her', 'text them', 'call him', 'call her', 'call them', 'add a note', 'add note to', 'note on', 'send sms', 'send a text', 'send him', 'send her', 'from go high level', 'from ghl', 'in ghl', 'go high level', 'follow up with', 'reach out to', 'nurture', 'gave you access', 'prepare', 'set that up', 'set it up', 'what we were talking', 'two messages', 'the messages']
                        if GHL_ENABLED and any((t in text for t in ghl_triggers)):
                                handled = await handle_ghl_intent(update, context, raw_text)
                                if handled:
                                    return
                        await update.message.chat.send_action('typing')
                        system = MASTER_SYSTEM_PROMPT
                        transcript_references = ['that video', 'that reel', 'this video', 'from the video', 'from the transcript', 'the transcript', 'the reel', 'that transcript', 'u just did', 'you just did', 'the skill', 'that skill', 'just transcribed']
                        transcription_context = ''
                        if last_transcription.get('full_text') and any((t in text for t in transcript_references)):
                                tr = last_transcription
                                transcription_context = f"\n\nRECENT TRANSCRIPTION CONTEXT (user is referring to this):\nURL: {tr['url']}\nLanguage: {tr['language']} | Duration: {int(tr['duration'] or 0)}s\nRecap: {tr['recap']}\n\nFull transcript:\n{tr['full_text'][:3500]}\n\n---\nAnswer the user\'s question based on this transcript.\n"
                        history_context = ''
                        if chat_history:
                            recent = chat_history[(-6):]
                            history_context = '\n\nRecent conversation:\n' + '\n'.join((f"{('User' if role == 'user' else 'You')}: {msg}" for role, msg in recent)) + '\n\nNew user message:\n'
                        if transcription_context:
                            history_context = transcription_context + history_context
                        prompt = history_context + raw_text
                        loop = asyncio.get_event_loop()
                        reply = await loop.run_in_executor(None, call_claude_cli, prompt, system)
                        if reply:
                            chat_history.append(('user', raw_text))
                            chat_history.append(('assistant', reply))
                            if len(chat_history) > MAX_HISTORY * 2:
                                del chat_history[:2]
                            if VAULT_ENABLED:
                                try:
                                    await loop.run_in_executor(None, obsidian_vault.append_chat_exchange, raw_text, reply)
                                except Exception as e:
                                    log.error('Vault chat log failed: %s', e)
                            if len(reply) > 4000:
                                for i in range(0, len(reply), 4000):
                                    await update.message.reply_text(reply[i:i + 4000])
                            else:
                                await update.message.reply_text(reply)
                        else:
                            await update.message.reply_text('⚠️ Claude didn\'t respond. Try again or use /help for commands.')
@authorized
async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear conversation history."""
    global chat_history
    chat_history = []
    await update.message.reply_text('🧹 Conversation history cleared.')
awaiting_response = {}
FATHOM_PENDING_FILE = Path('C:\\Users\\User\\crons\\fathom_pending.json')
def _load_fathom_pending():
    if FATHOM_PENDING_FILE.exists():
        try:
            return json.loads(FATHOM_PENDING_FILE.read_text(encoding='utf-8'))
        except Exception:
            return {}
    else:
        return {}
def _save_fathom_pending(data):
    FATHOM_PENDING_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
async def handle_fathom_callback(update, context):
    """Handle inline button taps on Fathom meeting prompts."""
    query = update.callback_query
    await query.answer()
    if query.from_user.id!= AUTHORIZED_CHAT_ID:
        await query.edit_message_text('⛔ Unauthorized.')
        return
    else:
        data = query.data
        parts = data.split(':', 2)
        if len(parts)!= 3 or parts[0]!= 'fm':
            return None
        else:
            _, action, meeting_id = parts
            pending = _load_fathom_pending()
            meeting = pending.get(meeting_id)
            if not meeting:
                await query.edit_message_text('⚠️ Meeting data expired or not found.')
                return
            else:
                title = meeting.get('title', 'Meeting')
                attendees = meeting.get('attendees', [])
                summary = meeting.get('summary', '')
                action_items = meeting.get('action_items', [])
                loop = asyncio.get_event_loop()
                if action == 'skip':
                    meeting['status'] = 'skipped'
                    _save_fathom_pending(pending)
                    await query.edit_message_text(f'⏭ Skipped: <i>{title}</i>\n\nStill saved in your Obsidian vault.', parse_mode='HTML')
                else:
                    if action == 'ghlnote':
                        await query.edit_message_text(f'⏳ Adding GHL note for <b>{title}</b>...', parse_mode='HTML')
                        note_body = _build_meeting_note(title, meeting)
                        pushed = await loop.run_in_executor(None, _push_meeting_to_ghl, attendees, note_body)
                        if pushed:
                            await context.bot.send_message(AUTHORIZED_CHAT_ID, f'✅ GHL note added to {pushed} contact(s) for <b>{title}</b>', parse_mode='HTML')
                        else:
                            await context.bot.send_message(AUTHORIZED_CHAT_ID, f'⚠️ No matching GHL contact found for attendees of <b>{title}</b>', parse_mode='HTML')
                        meeting['status'] = 'resolved'
                        _save_fathom_pending(pending)
                    else:
                        if action == 'ghl':
                            awaiting_response[meeting_id] = {'mode': 'ghl_followup', 'meeting': meeting}
                            await query.edit_message_text(f'🎯 <b>{title}</b> → GHL note + follow-up\n\nWhat should the follow-up SMS say? Reply to this chat with the message text.\nOr send /skip to just add the note.', parse_mode='HTML')
                        else:
                            if action == 'task':
                                awaiting_response[meeting_id] = {'mode': 'task', 'meeting': meeting}
                                suggested_date = (datetime.now() + timedelta(days=3)).strftime('%A %Y-%m-%d 9am')
                                await query.edit_message_text(f'✅ <b>{title}</b> → Create task\n\nReply with the task description + when (default: <i>{suggested_date}</i>).\nExamples:\n• <code>Call Alex about pricing Friday 2pm</code>\n• <code>Send proposal</code>\n• /skip to just create a basic reminder', parse_mode='HTML')
                            else:
                                if action == 'taskplus':
                                    awaiting_response[meeting_id] = {'mode': 'taskplus', 'meeting': meeting}
                                    await query.edit_message_text(f'📝 <b>{title}</b> → Note + reminder\n\nReply with:\n1. What note to add\n2. When to remind you (e.g. \'Friday 9am\')', parse_mode='HTML')
                                else:
                                    if action == 'remind':
                                        awaiting_response[meeting_id] = {'mode': 'remind', 'meeting': meeting}
                                        await query.edit_message_text(f'⏰ <b>{title}</b> → Set reminder\n\nReply with when to remind you (e.g. \'tomorrow 9am\', \'Friday afternoon\', \'in 2 hours\').', parse_mode='HTML')
                                    else:
                                        if action == 'verify':
                                            await query.edit_message_text(f'⏳ Analyzing follow-through tasks for <b>{title}</b>...', parse_mode='HTML')
                                            action_items_list = meeting.get('action_items') or []
                                            summary = meeting.get('summary') or ''
                                            transcript_snippet = meeting.get('transcript_snippet', '')[:3000]
                                            system = 'Extract the specific action items that the EMPLOYEE (not the manager) committed to in this meeting. Return a short bulleted list in French or English (match the meeting). Each item should be something the user can later verify was done (e.g., \'Hatem will send proposal by Friday\'). Max 6 items. Format as plain text bullets with - prefix. If no clear employee commitments, say \'No clear action items for this employee.\''
                                            prompt = f"Meeting: {title}\nEmployee: {meeting.get('special_person', 'unknown')}\nExisting action items: {action_items_list}\nSummary: {summary}\n\nTranscript:\n{transcript_snippet}"
                                            extracted = await loop.run_in_executor(None, call_claude_cli, prompt, system)
                                            if not extracted:
                                                extracted = '- Follow up to ensure action items from this meeting were completed'
                                            contact_id = None
                                            contact_name = None
                                            attendees = meeting.get('attendees', [])
                                            special_person = meeting.get('special_person', '')
                                            for a in attendees:
                                                name = (a.get('name') or '').lower()
                                                email = (a.get('email') or '').lower()
                                                if special_person and (special_person in name or special_person in email):
                                                        if email and '@' in email:
                                                                results = await loop.run_in_executor(None, ghl_tools.search_contacts, email, 1)
                                                                if results:
                                                                    contact_id = results[0]['id']
                                                                    contact_name = results[0]['name']
                                                                    break
                                                        results = await loop.run_in_executor(None, ghl_tools.search_contacts, a.get('name', ''), 1)
                                                        if results:
                                                            contact_id = results[0]['id']
                                                            contact_name = results[0]['name']
                                                            break
                                            due = (datetime.now() + timedelta(days=2)).replace(hour=9, minute=0, second=0)
                                            due_iso = due.strftime('%Y-%m-%dT%H:%M:%S-05:00')
                                            task_title = f"Verify: {title} — did {(special_person.title() if special_person else 'they')} follow through?"
                                            task_body = f"Meeting: {title}\nDate: {datetime.now().strftime('%Y-%m-%d')}\n\nAction items to verify:\n{extracted}\n\n— Auto-generated from Fathom"
                                            if contact_id:
                                                task_id = await loop.run_in_executor(None, ghl_tools.add_task, contact_id, task_title[:200], task_body, due_iso)
                                                if task_id:
                                                    await context.bot.send_message(AUTHORIZED_CHAT_ID, f"✅ <b>Verify task created</b>\nContact: <b>{contact_name}</b>\nDue: {due.strftime('%A %Y-%m-%d at 9:00 AM')}\n\n<b>To verify:</b>\n{extracted}", parse_mode='HTML')
                                                else:
                                                    await context.bot.send_message(AUTHORIZED_CHAT_ID, '⚠️ GHL task creation failed.')
                                            else:
                                                await context.bot.send_message(AUTHORIZED_CHAT_ID, f"📝 <b>Follow-through checklist</b> (no GHL contact matched)\n\n<b>Meeting:</b> {title}\n<b>Reminder for:</b> {due.strftime('%A %Y-%m-%d')}\n\n<b>To verify:</b>\n{extracted}", parse_mode='HTML')
                                            meeting['status'] = 'resolved'
                                            _save_fathom_pending(pending)
                                        else:
                                            if action == 'custom':
                                                awaiting_response[meeting_id] = {'mode': 'custom', 'meeting': meeting}
                                                await query.edit_message_text(f'💬 <b>{title}</b> → Custom action\n\nTell me what to do with this meeting. Examples:\n• Send summary to Alex on email\n• Add to my Friday review\n• Create 3 tasks: follow up with each attendee', parse_mode='HTML')
                                            else:
                                                await query.edit_message_text(f'Unknown action: {action}')
def _build_meeting_note(title, meeting):
    """Build a GHL-friendly note body from a meeting."""
    date = datetime.now().strftime('%Y-%m-%d')
    dur = meeting.get('duration_seconds', 0) // 60
    summary = meeting.get('summary', '')
    action_items = meeting.get('action_items', [])
    note = f'🎤 Meeting: {title}\n📅 {date} | ⏱ {dur} min\n\n'
    if summary:
        note += f'📋 Summary:\n{summary}\n\n'
    if action_items:
        note += '✅ Action Items:\n'
        for ai in action_items:
            item = ai if isinstance(ai, str) else ai.get('text', str(ai))
            note += f'• {item}\n'
    note += '\n— Auto-synced from Fathom'
    return note
def _push_meeting_to_ghl(attendees, note_body):
    """Push a note to each GHL contact matching an attendee\'s email."""
    if not GHL_ENABLED:
        return 0
    else:
        pushed = 0
        for a in attendees:
            email = a.get('email', '')
            if not email or '@' not in email:
                continue
            else:
                contact_id = ghl_tools.find_ghl_contact_by_email(email) if hasattr(ghl_tools, 'find_ghl_contact_by_email') else None
                if not contact_id:
                    results = ghl_tools.search_contacts(a.get('name', email), limit=1)
                    if results:
                        contact_id = results[0]['id']
                if contact_id and ghl_tools.add_note(contact_id, note_body):
                        pushed += 1
        return pushed
async def handle_fathom_followup_text(update, context, raw_text):
    """\n    Called from handle_message if there\'s a pending Fathom action awaiting free-form text.\n    Returns True if handled.\n    """
    if not awaiting_response:
        return False
    else:
        meeting_id = list(awaiting_response.keys())[(-1)]
        entry = awaiting_response.pop(meeting_id)
        mode = entry['mode']
        meeting = entry['meeting']
        title = meeting.get('title', 'Meeting')
        attendees = meeting.get('attendees', [])
        loop = asyncio.get_event_loop()
        if raw_text.lower().strip() in ['/skip', 'skip', 'cancel']:
            await update.message.reply_text(f'⏭ Cancelled follow-up for <b>{title}</b>.', parse_mode='HTML')
            return True
        else:
            if mode == 'ghl_followup':
                note_body = _build_meeting_note(title, meeting)
                pushed = await loop.run_in_executor(None, _push_meeting_to_ghl, attendees, note_body)
                scheduled = 0
                for a in attendees:
                    email = a.get('email', '')
                    if not email or '@' not in email:
                        continue
                    else:
                        results = await loop.run_in_executor(None, ghl_tools.search_contacts, email, 1)
                        if not results:
                            results = await loop.run_in_executor(None, ghl_tools.search_contacts, a.get('name', email), 1)
                        if results:
                            cid = results[0]['id']
                            when = (datetime.now() + timedelta(days=1)).replace(hour=9, minute=0, second=0)
                            iso = when.strftime('%Y-%m-%dT%H:%M:%S-05:00')
                            if await loop.run_in_executor(None, ghl_tools.schedule_sms, cid, raw_text, iso):
                                scheduled += 1
                await update.message.reply_text(f'✅ <b>{title}</b>\n  • Note added to {pushed} contact(s)\n  • SMS scheduled for {scheduled} contact(s) tomorrow 9 AM\n\n<i>Message:</i> {raw_text[:200]}', parse_mode='HTML')
            else:
                if mode == 'task':
                    system = 'Parse this task description into JSON. Return ONLY JSON: {"title": "...", "body": "...", "when": "YYYY-MM-DD HH:MM or null", "days_from_now": N}\nCurrent date: ' + datetime.now().strftime('%Y-%m-%d (%A)')
                    parsed = await loop.run_in_executor(None, call_claude_cli, raw_text, system)
                    try:
                        start = parsed.find('{')
                        end = parsed.rfind('}')
                        data = json.loads(parsed[start:end + 1])
                    except Exception:
                        data = {'title': raw_text[:80], 'body': raw_text, 'when': None, 'days_from_now': 3}
                    contact_id = None
                    contact_name = None
                    for a in attendees:
                        email = a.get('email', '')
                        if email and '@' in email:
                                results = await loop.run_in_executor(None, ghl_tools.search_contacts, email, 1)
                                if results:
                                    contact_id = results[0]['id']
                                    contact_name = results[0]['name']
                                    break
                    if not contact_id:
                        for a in attendees:
                            name = a.get('name', '')
                            if name:
                                results = await loop.run_in_executor(None, ghl_tools.search_contacts, name, 1)
                                if results:
                                    contact_id = results[0]['id']
                                    contact_name = results[0]['name']
                                    break
                    if not contact_id:
                        await update.message.reply_text(f'⚠️ Couldn\'t find a GHL contact for attendees of <b>{title}</b>. Task not created.', parse_mode='HTML')
                        return True
                    else:
                        due_iso = None
                        if data.get('when'):
                            try:
                                dt = datetime.strptime(data['when'], '%Y-%m-%d %H:%M')
                                due_iso = dt.strftime('%Y-%m-%dT%H:%M:%S-05:00')
                            except Exception:
                                pass
                        if not due_iso:
                            days = data.get('days_from_now', 3) or 3
                            due = (datetime.now() + timedelta(days=days)).replace(hour=9, minute=0, second=0)
                            due_iso = due.strftime('%Y-%m-%dT%H:%M:%S-05:00')
                        task_id = await loop.run_in_executor(None, ghl_tools.add_task, contact_id, data['title'][:200], data.get('body', ''), due_iso)
                        if task_id:
                            await update.message.reply_text(f"✅ Task created on <b>{contact_name}</b>\n<b>{data['title']}</b>\nDue: {due_iso[:16].replace('T', ' ')}", parse_mode='HTML')
                        else:
                            await update.message.reply_text('❌ Failed to create task.')
                else:
                    if mode == 'remind':
                        contact_id = None
                        contact_name = None
                        for a in attendees:
                            if a.get('email', '') and '@' in a['email']:
                                    results = await loop.run_in_executor(None, ghl_tools.search_contacts, a['email'], 1)
                                    if results:
                                        contact_id = results[0]['id']
                                        contact_name = results[0]['name']
                                        break
                        system = 'Parse this into ISO datetime. Current date: ' + datetime.now().strftime('%Y-%m-%d %H:%M') + '. Return ONLY: {"when": "YYYY-MM-DD HH:MM"}'
                        parsed = await loop.run_in_executor(None, call_claude_cli, raw_text, system)
                        try:
                            start = parsed.find('{')
                            end = parsed.rfind('}')
                            data = json.loads(parsed[start:end + 1])
                            dt = datetime.strptime(data['when'], '%Y-%m-%d %H:%M')
                        except Exception:
                            dt = datetime.now() + timedelta(days=1)
                            dt = dt.replace(hour=9, minute=0, second=0)
                        iso = dt.strftime('%Y-%m-%dT%H:%M:%S-05:00')
                        if contact_id:
                            task_id = await loop.run_in_executor(None, ghl_tools.add_task, contact_id, f'Follow up re: {title}'[:200], meeting.get('summary', '')[:500], iso)
                            if task_id:
                                await update.message.reply_text(f"⏰ Reminder set for <b>{contact_name}</b>\n{dt.strftime('%A %Y-%m-%d at %H:%M')}", parse_mode='HTML')
                            else:
                                await update.message.reply_text('❌ Failed to create reminder.')
                        else:
                            await update.message.reply_text(f"⏰ Noted: {dt.strftime('%A %Y-%m-%d at %H:%M')} re: <b>{title}</b>\n(No GHL contact matched — use Google Calendar or your own system for this one.)", parse_mode='HTML')
                    else:
                        if mode == 'custom':
                            system = 'You are a helpful assistant. The user has a meeting transcript/summary and a free-form instruction. Explain clearly what you WOULD do step by step. If an action involves GHL, name the contact + action. Don\'t execute anything — just propose.'
                            prompt = f"Meeting: {title}\nAttendees: {', '.join((a.get('name', a.get('email', '?')) for a in attendees))}\nSummary: {meeting.get('summary', '')[:800]}\n\nUser instruction: {raw_text}"
                            response = await loop.run_in_executor(None, call_claude_cli, prompt, system)
                            await update.message.reply_text(response or '⚠️ Claude didn\'t respond.', parse_mode='HTML')
                        else:
                            if mode == 'taskplus':
                                await update.message.reply_text(f'📝 Working on note + reminder for <b>{title}</b>...\nGive me a sec — I\'ll handle both.', parse_mode='HTML')
                                note_body = _build_meeting_note(title, meeting) + '\n\nNotes: ' + raw_text
                                pushed = await loop.run_in_executor(None, _push_meeting_to_ghl, attendees, note_body)
                                contact_id = None
                                for a in attendees:
                                    if a.get('email') and '@' in a['email']:
                                            results = await loop.run_in_executor(None, ghl_tools.search_contacts, a['email'], 1)
                                            if results:
                                                contact_id = results[0]['id']
                                                break
                                task_id = None
                                if contact_id:
                                    when = (datetime.now() + timedelta(days=2)).replace(hour=9, minute=0, second=0)
                                    iso = when.strftime('%Y-%m-%dT%H:%M:%S-05:00')
                                    task_id = await loop.run_in_executor(None, ghl_tools.add_task, contact_id, f'Follow up: {title}'[:200], raw_text[:500], iso)
                                await update.message.reply_text(f"✅ Done for <b>{title}</b>\n  • Note added to {pushed} contact(s)\n  • Reminder: {('created' if task_id else 'skipped (no contact match)')}", parse_mode='HTML')
            pending = _load_fathom_pending()
            if meeting_id in pending:
                pending[meeting_id]['status'] = 'resolved'
                _save_fathom_pending(pending)
            return True
# ============================================================================
# SMS APPROVAL WORKFLOW (Sprint 17)
# ----------------------------------------------------------------------------
# Lets smart_hot_leads.py propose SMS drafts that appear in this Telegram chat
# with 4 inline buttons: Approve / Reject / Edit / Refine. Callbacks update
# pending_sms_approvals in Supabase; send_approved_sms.py cron dispatches
# anything marked 'approved' every 30 min.
#
# IMPORTANT: the cron (smart_hot_leads.py) sends the INITIAL message via plain
# Telegram Bot API (see telegram_api.post_approval_message in kb_config-sister
# module). This long-running bot process only handles the INBOUND callbacks
# and commands (/edit, /refine) because only one poller can consume updates.
# ============================================================================
try:
    from kb_config import sb_get, sb_patch, sb_upsert
    SMS_APPROVAL_ENABLED = True
except ImportError:
    SMS_APPROVAL_ENABLED = False
    log.warning('SMS approval disabled: kb_config not importable')


def _approval_keyboard(approval_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton('✅ Approve', callback_data=f'approve:{approval_id}'),
            InlineKeyboardButton('❌ Reject', callback_data=f'reject:{approval_id}'),
        ],
        [
            InlineKeyboardButton('✏️ Edit', callback_data=f'edit:{approval_id}'),
            InlineKeyboardButton('🔄 Refine', callback_data=f'refine:{approval_id}'),
        ],
    ])


def _format_approval(approval):
    name = approval.get('contact_name') or 'Inconnu'
    phone = approval.get('phone_number', '')
    display_phone = f'+1{phone}' if len(phone) == 10 else phone
    context = approval.get('context_summary', '')
    priority = approval.get('priority', '')
    sms = approval.get('sms_body', '')
    version = approval.get('version', 1) or 1
    version_tag = f' (v{version})' if version > 1 else ''
    return (
        f'<b>📱 SMS a envoyer{version_tag}</b>\n'
        f'Priorite: <code>{priority}</code>\n\n'
        f'<b>Contact:</b> {name}\n'
        f'<b>Phone:</b> {display_phone}\n'
        f'<b>Contexte:</b> <i>{context}</i>\n\n'
        f'<b>Message:</b>\n'
        f'<pre>{sms}</pre>'
    )


def _now_iso():
    return datetime.now().isoformat()


def _load_approval(approval_id):
    """Fetch one approval row from Supabase. Returns dict or None."""
    if not SMS_APPROVAL_ENABLED:
        return None
    rows = sb_get(f'pending_sms_approvals?id=eq.{approval_id}&limit=1')
    if not rows or isinstance(rows, dict):
        return None
    return rows[0]


async def sms_approval_callback(update, context):
    """Handle button clicks on SMS approval messages: approve/reject/edit/refine."""
    query = update.callback_query
    await query.answer()
    if query.from_user.id != AUTHORIZED_CHAT_ID:
        await query.answer('⛔ Unauthorized', show_alert=True)
        return
    if not SMS_APPROVAL_ENABLED:
        await query.answer('SMS approval module not loaded', show_alert=True)
        return

    data = query.data or ''
    if ':' not in data:
        return
    action, approval_id_str = data.split(':', 1)
    try:
        approval_id = int(approval_id_str)
    except ValueError:
        return

    approval = _load_approval(approval_id)
    if not approval:
        await query.edit_message_text('⚠️ Approval introuvable (expire ou supprime).')
        return

    username = query.from_user.username or query.from_user.first_name or 'unknown'

    if action == 'approve':
        sb_patch(
            'pending_sms_approvals',
            f'id=eq.{approval_id}',
            {'status': 'approved', 'decided_at': _now_iso(), 'decided_by': username},
        )
        await query.edit_message_text(
            _format_approval(approval) + '\n\n✅ <b>APPROUVE</b> — sera envoye au prochain cycle (30 min).',
            parse_mode='HTML',
        )
    elif action == 'reject':
        sb_patch(
            'pending_sms_approvals',
            f'id=eq.{approval_id}',
            {'status': 'rejected', 'decided_at': _now_iso(), 'decided_by': username},
        )
        await query.edit_message_text(
            _format_approval(approval) + '\n\n❌ <b>REJETE</b> — pas envoye.',
            parse_mode='HTML',
        )
    elif action == 'edit':
        sb_patch(
            'pending_sms_approvals',
            f'id=eq.{approval_id}',
            {'status': 'edit_requested', 'decided_by': username},
        )
        await query.edit_message_text(
            _format_approval(approval) +
            f'\n\n✏️ <b>EDIT MODE</b>\nReponds avec: <code>/edit {approval_id} [ton texte]</code>',
            parse_mode='HTML',
        )
    elif action == 'refine':
        sb_patch(
            'pending_sms_approvals',
            f'id=eq.{approval_id}',
            {'status': 'refine_requested', 'decided_by': username},
        )
        await query.edit_message_text(
            _format_approval(approval) +
            f'\n\n🔄 <b>REFINE MODE</b>\nReponds avec: <code>/refine {approval_id} [feedback]</code>\n'
            f'Ex: <code>/refine {approval_id} plus court, moins formel</code>',
            parse_mode='HTML',
        )


@authorized
async def cmd_edit(update, context):
    """/edit <id> <text> — replace an approval's SMS with custom text."""
    if not SMS_APPROVAL_ENABLED:
        await update.message.reply_text('❌ SMS approval module not loaded.')
        return
    text = (update.message.text or '').strip()
    parts = text.split(maxsplit=2)
    if len(parts) < 3:
        await update.message.reply_text('Usage: <code>/edit &lt;id&gt; &lt;texte&gt;</code>', parse_mode='HTML')
        return
    try:
        approval_id = int(parts[1])
    except ValueError:
        await update.message.reply_text('❌ ID invalide.')
        return
    new_text = parts[2]

    # Validate via sms_validator
    try:
        from sms_validator import validate_sms
        ok, reason = validate_sms(new_text)
        if not ok:
            await update.message.reply_text(
                f'❌ Le texte propose ne passe pas la validation: <b>{reason}</b>\n\n'
                f'Re-envoie avec <code>/edit {approval_id} [texte corrige]</code>',
                parse_mode='HTML',
            )
            return
    except ImportError:
        log.warning('sms_validator not available — accepting edit without validation')

    username = update.effective_user.username or update.effective_user.first_name or 'unknown'
    sb_patch(
        'pending_sms_approvals',
        f'id=eq.{approval_id}',
        {
            'sms_body': new_text,
            'status': 'approved',
            'decided_at': _now_iso(),
            'decided_by': username,
            'user_feedback': f'EDITED by {username}',
        },
    )
    await update.message.reply_text(
        f'✅ <b>Edit accepte, SMS approuve.</b>\n\n<pre>{new_text}</pre>\n\nSera envoye au prochain cycle (30 min).',
        parse_mode='HTML',
    )


@authorized
async def cmd_refine(update, context):
    """/refine <id> <feedback> — regenerate SMS via Claude Haiku with user feedback."""
    if not SMS_APPROVAL_ENABLED:
        await update.message.reply_text('❌ SMS approval module not loaded.')
        return
    text = (update.message.text or '').strip()
    parts = text.split(maxsplit=2)
    if len(parts) < 3:
        await update.message.reply_text('Usage: <code>/refine &lt;id&gt; &lt;feedback&gt;</code>', parse_mode='HTML')
        return
    try:
        approval_id = int(parts[1])
    except ValueError:
        await update.message.reply_text('❌ ID invalide.')
        return
    feedback = parts[2]

    approval = _load_approval(approval_id)
    if not approval:
        await update.message.reply_text(f'❌ Approval {approval_id} introuvable.')
        return

    await update.message.reply_text('🔄 Regeneration en cours via Haiku...')
    prompt = (
        f"Tu as propose ce SMS:\n<SMS>\n{approval['sms_body']}\n</SMS>\n\n"
        f"L'utilisateur a demande une amelioration avec ce feedback:\n"
        f"<FEEDBACK>\n{feedback}\n</FEEDBACK>\n\n"
        "Re-ecris le SMS en appliquant le feedback. Garde ces regles:\n"
        "- Angle service (pas de vente pushy)\n"
        "- Tutoiement Quebec naturel\n"
        "- Max 320 caracteres\n"
        "- Pas d'emojis, pas de markdown, pas de guillemets\n"
        "- Contient \"(438) 802-0475\"\n"
        "- Commence par \"Bonjour\"\n\n"
        "Retourne UNIQUEMENT le nouveau texte du SMS."
    )

    loop = asyncio.get_event_loop()
    new_sms = await loop.run_in_executor(None, call_claude_cli, prompt, None)
    if not new_sms:
        await update.message.reply_text('❌ Haiku n\'a pas repondu. Reessaie ou utilise /edit.')
        return
    new_sms = new_sms.strip().strip('"').strip("'")

    try:
        from sms_validator import validate_sms
        ok, reason = validate_sms(new_sms)
        if not ok:
            await update.message.reply_text(
                f'❌ Le SMS refine ne passe pas la validation: <b>{reason}</b>\n\n<pre>{new_sms}</pre>\n\n'
                'Reessaie avec un feedback different.',
                parse_mode='HTML',
            )
            return
    except ImportError:
        pass

    # Create a new approval (version+1), keep original for audit
    username = update.effective_user.username or update.effective_user.first_name or 'unknown'
    new_row = {
        'phone_number': approval['phone_number'],
        'contact_name': approval.get('contact_name'),
        'ghl_contact_id': approval.get('ghl_contact_id'),
        'prospect_id': approval.get('prospect_id'),
        'sms_body': new_sms,
        'context_summary': approval.get('context_summary'),
        'priority': approval.get('priority'),
        'status': 'pending',
        'version': (approval.get('version', 1) or 1) + 1,
        'parent_approval_id': approval_id,
        'user_feedback': f'[refine by {username}] {feedback}',
        'run_date': approval.get('run_date'),
    }
    sb_upsert('pending_sms_approvals', new_row)

    # Find the new id + send a new approval message (inline, not via cron)
    latest = sb_get(
        f'pending_sms_approvals?parent_approval_id=eq.{approval_id}'
        f'&order=id.desc&limit=1'
    )
    if latest and not isinstance(latest, dict):
        new_id = latest[0]['id']
        new_approval = latest[0]
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=_format_approval(new_approval),
            parse_mode='HTML',
            reply_markup=_approval_keyboard(new_id),
        )
        sb_patch(
            'pending_sms_approvals',
            f'id=eq.{new_id}',
            {'telegram_chat_id': update.effective_chat.id},
        )
    else:
        await update.message.reply_text('⚠️ SMS refine mais erreur de tracking. Check Supabase.')


# ============================================================================
# END SMS APPROVAL WORKFLOW
# ============================================================================


async def global_error_handler(update, context):
    """Catch any uncaught exception in a handler and notify the user + log it."""
    log.error('Unhandled exception: %s', context.error, exc_info=context.error)
    if update and hasattr(update, 'message') and update.message:
        try:
            err_str = str(context.error)[:200]
            await update.message.reply_text(f'⚠️ Something broke while processing your message:\n<code>{err_str}</code>\n\nThe bot is still alive. Try again or check logs.', parse_mode='HTML')
        except Exception:
            return None
def main():
    log.info('Starting XGuard Telegram Bot...')
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_error_handler(global_error_handler)
    app.add_handler(CommandHandler('start', cmd_start))
    app.add_handler(CommandHandler('help', cmd_help))
    app.add_handler(CommandHandler('status', cmd_status))
    app.add_handler(CommandHandler('short', cmd_short))
    app.add_handler(CommandHandler('failures', cmd_failures))
    app.add_handler(CommandHandler('running', cmd_running))
    app.add_handler(CommandHandler('stale', cmd_stale))
    app.add_handler(CommandHandler('wsl', cmd_wsl))
    app.add_handler(CommandHandler('clear', cmd_clear))
    app.add_handler(CommandHandler('recall', cmd_recall))
    app.add_handler(CommandHandler('search', cmd_search))
    # --- Sprint 17: SMS approval workflow -----------------------------------
    app.add_handler(CommandHandler('edit', cmd_edit))
    app.add_handler(CommandHandler('refine', cmd_refine))
    app.add_handler(CallbackQueryHandler(
        sms_approval_callback,
        pattern=r'^(approve|reject|edit|refine):\d+$',
    ))
    # -------------------------------------------------------------------------
    app.add_handler(CallbackQueryHandler(handle_fathom_callback, pattern='^fm:'))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    log.info('Warming up Claude CLI...')
    warmup = _single_claude_call('ok', None, model='haiku', timeout=30)
    if warmup[0]:
        log.info('Warmup succeeded: %s', warmup[0][:50])
    else:
        log.warning('Warmup failed: %s — first real call may retry', warmup[1])
    log.info('Bot is live! Listening for messages...')
    app.run_polling(drop_pending_updates=True)
if __name__ == '__main__':
    main()