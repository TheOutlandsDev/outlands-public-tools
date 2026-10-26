"""Original MIT process isolation for optional capture and explicit OTX requests."""
from __future__ import annotations
import multiprocessing as mp
import queue
import time
from monitor_core import Model, MonitorError, capture, lookup_otx


def publish(channel, value):
    try:channel.put_nowait(value)
    except queue.Full:pass


def capture_child(channel, stopped, interface, seconds):
    model = Model('live')
    try:
        result = capture(model, interface, seconds, stopped,
                         on_update=lambda report:publish(channel, {'kind': 'progress', 'report': report}))
        channel.put({'kind': 'result', 'report': result}, timeout=1)
    except MonitorError as error:
        channel.put({'kind': 'error', 'code': str(error)}, timeout=1)
    except Exception:
        channel.put({'kind': 'error', 'code': 'CAPTURE_FAILED'}, timeout=1)


def lookup_child(channel, value):
    try:channel.put({'kind': 'result', 'report': lookup_otx(value, allow_online=True)}, timeout=1)
    except MonitorError as error:channel.put({'kind': 'error', 'code': str(error)}, timeout=1)
    except Exception:channel.put({'kind': 'error', 'code': 'OTX_LOOKUP_FAILED'}, timeout=1)


def run_isolated(action, arguments, stopped, on_update=None):
    """Terminate only the child created here; never an existing application."""
    context = mp.get_context('spawn')
    channel = context.Queue(maxsize=4)
    child_stop = context.Event()
    target = capture_child if action == 'capture' else lookup_child if action == 'lookup' else None
    if target is None:raise MonitorError('WORKER_ACTION_INVALID')
    args = (channel, child_stop, *arguments) if action == 'capture' else (channel, *arguments)
    child = context.Process(target=target, args=args, daemon=True)
    latest = None
    final = None
    terminated = False
    cancelled_at = None
    deadline = time.monotonic() + (arguments[1] + 8 if action == 'capture' else 12)
    try:
        child.start()
        while True:
            if stopped.is_set():
                child_stop.set()
                if cancelled_at is None:cancelled_at = time.monotonic()
            if time.monotonic() >= deadline or cancelled_at is not None and time.monotonic()-cancelled_at >= 2:
                break
            try:
                message = channel.get(timeout=.05)
                if message['kind'] == 'progress':
                    latest = message['report']
                    if on_update:on_update(latest)
                else:final = message
            except queue.Empty:pass
            if not child.is_alive():
                # Queue data can finish arriving just after process exit.
                try:
                    while True:
                        message = channel.get(timeout=.1)
                        if message['kind'] == 'progress':latest = message['report']
                        else:final = message
                except queue.Empty:pass
                break
        child_stop.set()
        if child.is_alive():terminated = True;child.terminate()
        child.join(timeout=1)
        if child.is_alive():child.kill();child.join(timeout=1)
        if child.is_alive():raise MonitorError('WORKER_CLEANUP_UNCONFIRMED')
        if stopped.is_set():
            if action == 'capture':
                complete = final is not None and final['kind'] == 'result' and not terminated
                result = dict(final['report'] if complete else latest or Model('live').report(), outcome='cancelled')
                if not complete:result.update(capture_incomplete=True,status='REVIEW_REQUIRED')
                return result
            raise MonitorError('CANCELLED')
        if final is None:
            if action == 'capture' and latest:return dict(latest,outcome='failed',capture_incomplete=True,status='REVIEW_REQUIRED')
            raise MonitorError('WORKER_TIMEOUT_OR_EXIT')
        if final['kind'] == 'error':raise MonitorError(final['code'])
        return final['report']
    finally:
        child_stop.set()
        if child.pid is not None:
            if child.is_alive():child.terminate();child.join(timeout=1)
            if child.is_alive():child.kill();child.join(timeout=1)
            if not child.is_alive():child.close()
        channel.close()
        channel.cancel_join_thread()


def system_snapshot():
    try:import psutil
    except ImportError:raise MonitorError('PSUTIL_UNAVAILABLE') from None
    psutil.cpu_percent(interval=None)
    started = time.monotonic()
    time.sleep(.2)
    cpu = psutil.cpu_percent(interval=None)
    memory = psutil.virtual_memory().percent
    counters = psutil.net_io_counters()
    return {'cpu_percent': cpu, 'memory_percent': memory,
            'cpu_sample_seconds': round(time.monotonic()-started, 3),
            'network_bytes_received_total': counters.bytes_recv if counters else None,
            'network_bytes_sent_total': counters.bytes_sent if counters else None}
