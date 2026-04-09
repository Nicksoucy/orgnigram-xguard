#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
nitro_service.py — Windows Service wrapper for the Nitro Watchdog.

Registers the watchdog as a Windows Service that:
- Auto-starts on boot
- Auto-restarts on crash (via Windows recovery options)
- Survives user logoff
- Can be managed via services.msc or sc commands

Installation:
    python nitro_service.py install
    python nitro_service.py start

Configure auto-restart on crash:
    sc failure NitroWatchdog reset= 86400 actions= restart/60000/restart/60000/restart/120000

Other commands:
    python nitro_service.py stop
    python nitro_service.py remove
    python nitro_service.py status
    sc query NitroWatchdog

Alternative (no pywin32): Use nitro_watchdog.bat in Windows Startup folder.

Requires: pip install pywin32
"""

import os
import sys

# Ensure crons directory is on path
_crons_dir = os.path.dirname(os.path.abspath(__file__))
if _crons_dir not in sys.path:
    sys.path.insert(0, _crons_dir)


def run_as_service():
    """Run as a Windows Service using pywin32."""
    try:
        import win32serviceutil
        import win32service
        import win32event
        import servicemanager
    except ImportError:
        print(
            "ERROR: pywin32 not installed.\n"
            "Install with: pip install pywin32\n"
            "Then run: python Scripts/pywin32_postinstall.py -install\n\n"
            "Alternative: use nitro_watchdog.bat in Windows Startup folder."
        )
        sys.exit(1)

    class NitroWatchdogService(win32serviceutil.ServiceFramework):
        _svc_name_ = "NitroWatchdog"
        _svc_display_name_ = "Nitro GPU Transcription Watchdog"
        _svc_description_ = (
            "Schedules and monitors GPU transcription cron jobs for XGuard. "
            "Runs Heidys, Domingos, and SAC daily syncs + weekly coaching reports. "
            "Sends heartbeat to Supabase every 5 minutes."
        )

        def __init__(self, args):
            win32serviceutil.ServiceFramework.__init__(self, args)
            self.stop_event = win32event.CreateEvent(None, 0, 0, None)
            self._scheduler = None

        def SvcStop(self):
            """Handle service stop request."""
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            win32event.SetEvent(self.stop_event)
            if self._scheduler:
                try:
                    self._scheduler.shutdown(wait=False)
                except Exception:
                    pass

        def SvcDoRun(self):
            """Main service entry point."""
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, ""),
            )

            import threading
            from nitro_watchdog import main as watchdog_main

            # Run the watchdog in a thread so we can listen for stop events
            t = threading.Thread(target=watchdog_main, daemon=True)
            t.start()

            # Block until stop signal
            win32event.WaitForSingleObject(self.stop_event, win32event.INFINITE)

            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STOPPED,
                (self._svc_name_, ""),
            )

    # Handle command line (install, start, stop, remove, etc.)
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(NitroWatchdogService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(NitroWatchdogService)


def generate_bat():
    """Generate a .bat fallback script for auto-start without pywin32."""
    bat_content = f'''@echo off
:: Nitro Watchdog — auto-restart loop
:: Place this file in shell:startup or schedule via Task Scheduler
:: (as a "run once at boot" task, NOT the old per-job scheduling)

title Nitro Watchdog
cd /d "{_crons_dir}"

:loop
echo [%date% %time%] Starting Nitro Watchdog...
python nitro_watchdog.py
echo [%date% %time%] Watchdog exited. Restarting in 30 seconds...
timeout /t 30 /nobreak
goto loop
'''
    bat_path = os.path.join(_crons_dir, "nitro_watchdog.bat")
    with open(bat_path, "w") as f:
        f.write(bat_content)
    print(f"Generated: {bat_path}")
    print("Place this file in your Windows Startup folder (shell:startup)")
    print("or create a single Task Scheduler task that runs it at boot.")


if __name__ == "__main__":
    if "--bat" in sys.argv:
        generate_bat()
    else:
        run_as_service()
