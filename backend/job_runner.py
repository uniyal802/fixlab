"""Execute one persisted job in a disposable child process."""
import sys
from core import get, job_payload, save, analyze, run_code, finish_job


def execute(job_id):
    job = job_payload(job_id)
    owner_id = job['_owner_id']
    quotas = job['_quotas']
    try:
        if job['kind'] == 'analysis':
            result = analyze(job['code'], job.get('error', ''), owner_id, quotas)
        elif job['kind'] == 'test_run':
            session = get(job['id'], owner_id)
            session['results'] = {
                'original': run_code(session['original_code'], session['analysis']['tests'], job_id),
                'fixed': run_code(session['analysis']['fixed_code'], session['analysis']['tests'], job_id),
            }
            save(session, session['id'], owner_id, quotas)
            result = session
        else:
            raise ValueError('Unknown job type')
        finish_job(job_id, 'succeeded', result=result)
    except Exception as exc:
        finish_job(job_id, 'failed', error=str(exc))


if __name__ == '__main__':
    execute(sys.argv[1])
