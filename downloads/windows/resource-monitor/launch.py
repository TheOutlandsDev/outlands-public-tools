"""Portable Windows entry point around unchanged Resource Monitor core/server."""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path
import signal
import sys
import threading
import webbrowser

ROOT=Path(__file__).resolve().parent

def check_package():
    manifest=json.loads((ROOT/'PACKAGE-MANIFEST.json').read_text(encoding='utf-8'));seen=set()
    for row in manifest['files']:
        name=row['path']
        if name.startswith('/') or ':' in name or '\\' in name or any(x in ('','.','..') for x in name.split('/')) or name.casefold() in seen:raise ValueError('Invalid package inventory.')
        seen.add(name.casefold());p=ROOT/name
        if not p.is_file() or p.is_symlink() or any(x.is_symlink() or getattr(x,'is_junction',lambda:False)() for x in (p,*p.parents)) or p.stat().st_size!=row['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=row['sha256']:raise ValueError('Package changed or incomplete. Extract a new verified ZIP.')
    if sys.platform!='win32' or sys.version_info[:3]!=(3,14,10) or Path(sys.executable).resolve()!=(ROOT/'runtime/python.exe').resolve() or not sys.flags.isolated:raise ValueError('Use the supplied Windows CMD launcher and bundled isolated runtime.')
    return manifest

def open_browser(url):
    from urllib.parse import urlsplit,parse_qs
    p=urlsplit(url)
    if p.scheme!='http' or p.hostname!='127.0.0.1' or not p.port or p.path!='/' or p.query or p.netloc!='127.0.0.1:'+str(p.port) or not re.fullmatch(r'token=[A-Za-z0-9_-]{32,128}',p.fragment):raise ValueError('Only the generated local capability URL may be opened.')
    return webbrowser.open(url)

def main():
    p=argparse.ArgumentParser(description='Resource Monitor portable Windows',allow_abbrev=False)
    modes=p.add_mutually_exclusive_group();modes.add_argument('--demo',action='store_true');modes.add_argument('--live',action='store_true')
    p.add_argument('--check',action='store_true');p.add_argument('--no-browser',action='store_true');p.add_argument('--stop-stdin',action='store_true')
    p.add_argument('--port',type=int,default=0);p.add_argument('--interval',type=float,default=1);p.add_argument('--history',type=int,default=120);p.add_argument('--duration',type=float)
    a=p.parse_args()
    try:
        manifest=check_package()
        from resource_monitor.core import DemoProvider,LiveProvider,integer,interval_seconds
        from resource_monitor.server import MonitorApp
        integer(a.port,0,65535,'Port');integer(a.history,1,600,'History');interval_seconds(a.interval)
        if a.duration is not None and (not math.isfinite(a.duration) or not .2<=a.duration<=3600):raise ValueError('Duration must be 0.2 to 3600 seconds.')
        if a.check:
            version=None
            if a.live:
                import psutil
                if psutil.__version__!='7.2.1' or not Path(psutil.__file__).resolve().is_relative_to(ROOT/'dependencies'):raise ValueError('Use the bundled live dependency.')
                version=psutil.__version__
            print(json.dumps(dict(status='PASS',runtime=sys.version.split()[0],package=manifest['package_version'],isolated=True,bundled_runtime=True,mode='live' if a.live else 'demo',psutil_loaded='psutil' in sys.modules,live_dependency=version)))
            return 0
        provider=LiveProvider() if a.live else DemoProvider()
        if not a.live and 'psutil' in sys.modules:raise ValueError('Demo unexpectedly loaded the live dependency.')
        with MonitorApp(provider,a.port,a.interval,a.history) as app:
            print('Resource Monitor | '+('LIVE METRICS - private aggregate readings' if a.live else 'FICTIONAL DEMO - no machine metrics'),flush=True)
            print(json.dumps(dict(mode=provider.mode,psutil_loaded='psutil' in sys.modules)),flush=True)
            print(app.url,flush=True)
            print('Keep the complete token URL private. Ctrl+C stops sampling. History is memory-only; export deliberately.',flush=True)
            signal.signal(signal.SIGINT,lambda *_:app.stop_event.set());signal.signal(signal.SIGTERM,lambda *_:app.stop_event.set())
            if a.stop_stdin:
                def stop_input():
                    for line in sys.stdin:
                        if line.strip()=='stop':app.stop_event.set();break
                threading.Thread(target=stop_input,daemon=True).start()
            if not a.no_browser:
                try:
                    if not open_browser(app.url):print('Open the complete address above in your browser.',flush=True)
                except (OSError,webbrowser.Error):print('Open the complete address above in your browser.',flush=True)
            app.stop_event.wait(a.duration)
        print('Stopped. Unsaved history was discarded; existing explicit exports remain.',flush=True)
        return 0
    except Exception:
        print('Resource Monitor could not start. Check the package, supported runtime, bounds or port. Existing files were not reset.',file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())
