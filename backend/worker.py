"""Local SQLite-backed job dispatcher. Run separately from the HTTP API."""
import os
import signal
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from auth import validate_configuration
from core import claim_job, connection, get_job, finish_job, cleanup_expired, validate_runtime_configuration

ROOT = Path(__file__).resolve().parents[1]
RUNNER = Path(__file__).with_name('job_runner.py')
DEADLINES = {'analysis': 190, 'test_run': 55}


def remove_container(job_id):
    try:
        subprocess.run(['docker', 'rm', '-f', 'fixlab-job-' + job_id], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        pass


def recover_after_restart():
    """A local worker is single-owner; recover leases left by a crashed process."""
    now = time.time()
    with connection() as db:
        db.execute("UPDATE jobs SET state='cancelled',finished=?,updated=? WHERE state='running' AND cancel_requested=1", (now, now))
        db.execute("UPDATE jobs SET state='queued',updated=? WHERE state='running' AND attempts < 2", (now,))
        db.execute("UPDATE jobs SET state='failed',error='Worker stopped before job completed',finished=?,updated=? WHERE state='running'", (now, now))


def dispatch_once(active, limit):
    while len(active) < limit:
        job_id = claim_job()
        if not job_id:
            break
        job = get_job(job_id)
        job_tmp = Path(tempfile.gettempdir()) / ('fixlab-job-' + job_id)
        job_tmp.mkdir(mode=0o700, parents=True, exist_ok=True)
        output = open(os.devnull, 'wb')
        env = {**os.environ, 'FIXLAB_JOB_TMPDIR': str(job_tmp)}
        process = subprocess.Popen([sys.executable, str(RUNNER), job_id], cwd=ROOT, stdout=output, stderr=output, env=env)
        active[job_id] = (process, time.monotonic(), output, job['kind'], job_tmp)


def poll_active(active):
    for job_id, (process, started, output, kind, job_tmp) in list(active.items()):
        job = get_job(job_id)
        if job['cancellation_requested']:
            process.terminate()
            try: process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait()
            remove_container(job_id)
            finish_job(job_id, 'cancelled', error='Cancelled by user')
        elif time.monotonic() - started > DEADLINES[kind]:
            process.kill(); process.wait()
            remove_container(job_id)
            finish_job(job_id, 'failed', error='Job exceeded its hard deadline')
        elif process.poll() is not None:
            refreshed = get_job(job_id)
            if refreshed['state'] == 'running':
                if process.returncode and refreshed['attempts'] < 2:
                    with connection() as db:
                        db.execute("UPDATE jobs SET state='queued',updated=? WHERE id=? AND state='running'", (time.time(), job_id))
                else:
                    finish_job(job_id, 'failed', error='Worker exited without recording a result')
            elif refreshed['state'] == 'failed' and refreshed['attempts'] < 2:
                with connection() as db:
                    db.execute("UPDATE jobs SET state='queued',error=NULL,updated=? WHERE id=? AND state='failed'", (time.time(), job_id))
        else:
            continue
        output.close()
        shutil.rmtree(job_tmp, ignore_errors=True)
        del active[job_id]


def run_forever():
    validate_configuration()
    validate_runtime_configuration()
    recover_after_restart()
    cleanup_expired()
    limit = max(1, min(4, int(os.getenv('FIXLAB_WORKERS', '1'))))
    active = {}
    last_cleanup = time.monotonic()
    stopping = False
    def request_stop(_signum, _frame):
        nonlocal stopping
        stopping = True
    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    print(f'FixLab worker ready (concurrency={limit})', flush=True)
    try:
        while not stopping:
            dispatch_once(active, limit)
            poll_active(active)
            if time.monotonic() - last_cleanup >= 3600:
                cleanup_expired()
                last_cleanup = time.monotonic()
            time.sleep(0.2 if active else 0.75)
    finally:
        for job_id, (process, _started, output, _kind, job_tmp) in active.items():
            if process.poll() is None:
                process.terminate()
                try: process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill(); process.wait()
            remove_container(job_id)
            output.close()
            shutil.rmtree(job_tmp, ignore_errors=True)


if __name__ == '__main__':
    run_forever()
