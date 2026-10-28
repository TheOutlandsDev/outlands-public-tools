"""Original MIT extracted-ZIP acceptance. Fictional samples; private output only."""
import argparse
import csv
import io
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit, parse_qs

ROOT = Path(__file__).resolve().parents[1]

def run(workspace):
    assert workspace.is_absolute() and ROOT not in workspace.resolve().parents
    workspace.mkdir()  # Refuse an existing path, including somebody else's fixture.
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    wrapper = ['cmd.exe', '/d', '/c', 'start-demo.cmd --check'] if os.name == 'nt' else ['sh', 'start-demo.sh', '--check']
    assert subprocess.run(wrapper, cwd=ROOT, env=env, capture_output=True).returncode == 0
    def start():
        child = subprocess.Popen([sys.executable, '-B', 'launch.py', '--interval', '.1', '--history', '3', '--duration', '1.5'], cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        lines = queue.Queue()
        def reader():
            for line in child.stdout: lines.put(line)
        reader_thread = threading.Thread(target=reader, daemon=True); reader_thread.start()
        try:
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                line = lines.get(timeout=10).strip()
                if line.startswith('http://127.0.0.1:'):
                    parts = urlsplit(line)
                    return child, reader_thread, parts.scheme + '://' + parts.netloc, parse_qs(parts.fragment)['token'][0]
            raise AssertionError('No startup URL')
        except BaseException:
            child.terminate(); child.communicate(timeout=5); reader_thread.join(timeout=2); raise
    def get(origin, token, route):
        req = urllib.request.Request(origin + route, headers={'X-Outlands-Token': token})
        try:
            with urllib.request.urlopen(req, timeout=2) as response: return response.status, response.read()
        except urllib.error.HTTPError as error:
            with error: return error.code, error.read()
    checks = []
    child, reader_thread, origin, token = start()
    try:
        assert get(origin, token, '/')[0] == 200
        assert get(origin, '', '/api/history')[0] == 403; checks.append('token_required')
        time.sleep(.35)
        status, data = get(origin, token, '/api/history'); report = json.loads(data)
        assert status == 200 and report['mode'] == 'demo' and 2 <= len(report['samples']) <= 3
        checks.append('fictional_bounded_history')
        status, exported = get(origin, token, '/api/export.json'); assert status == 200
        target = workspace / 'fictional-history.json'
        with target.open('xb') as stream: stream.write(exported)
        assert json.loads(target.read_bytes())['mode'] == 'demo'; checks.append('json_export_reopened')
        status, exported = get(origin, token, '/api/export.csv'); assert status == 200
        rows = list(csv.DictReader(io.StringIO(exported.decode('utf-8')))); assert 2 <= len(rows) <= 3
        (workspace / 'fictional-history.csv').write_bytes(exported); checks.append('csv_export_reopened')
        sys.path.insert(0, str(ROOT))
        from resource_monitor.core import save_fresh, MonitorError
        before = target.read_bytes()
        try: save_fresh(str(target), b'replacement'); raise AssertionError('Existing export overwritten')
        except (MonitorError, FileExistsError): pass
        assert target.read_bytes() == before; checks.append('existing_export_preserved')
        assert child.wait(timeout=5) == 0
    finally:
        if child.poll() is None: child.terminate(); child.wait(timeout=5)
        reader_thread.join(timeout=2); child.stdout.close(); child.stderr.close()
    second, reader_thread, origin, fresh = start()
    try:
        assert token != fresh and get(origin, token, '/api/history')[0] == 403
        assert get(origin, fresh, '/api/history')[0] == 200; checks.append('restart_rejects_old_token')
        assert target.read_bytes() == before; checks.append('saved_export_survives_restart')
        assert second.wait(timeout=5) == 0
    finally:
        if second.poll() is None: second.terminate(); second.wait(timeout=5)
        reader_thread.join(timeout=2); second.stdout.close(); second.stderr.close()
    receipt = dict(schema=1, app='resource-monitor', version='0.1.1', mode='fictional HTTP and CLI; no browser or live metrics', checks=checks, status='PASS')
    with (workspace / 'observed-results.json').open('x', encoding='utf-8') as stream: json.dump(receipt, stream, indent=2); stream.write('\n')
    print(json.dumps(receipt))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--workspace', required=True, type=Path)
    try: run(parser.parse_args().workspace)
    except Exception:
        print('Download check failed. Private new files retained; no capability URL or raw output printed.', file=sys.stderr)
        raise SystemExit(1)
