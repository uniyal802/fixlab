import json
import mimetypes
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from core import (get, history, save, health, edit, delete, submit_job,
                  get_job, cancel_job, session_has_active_job, validate_analysis_input)

FRONTEND = Path(__file__).resolve().parents[1] / 'frontend'
RUN_LOCK = threading.Lock()

class Handler(BaseHTTPRequestHandler):
    def respond(self, value, status=200):
        body = json.dumps(value).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        try:
            if path == '/api/health':
                return self.respond(health())
            if path == '/api/sessions':
                return self.respond(history())
            if path.startswith('/api/jobs/'):
                return self.respond(get_job(path.rsplit('/', 1)[1]))
            if path.startswith('/api/sessions/'):
                return self.respond(get(path.rsplit('/', 1)[1]))
            files = {'/': 'index.html', '/app.js': 'app.js', '/style.css': 'style.css'}
            if path not in files:
                return self.respond({'error': 'Not found'}, 404)
            target = FRONTEND / files[path]
            body = target.read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', mimetypes.guess_type(str(target))[0] or 'text/plain')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except ValueError as exc:
            self.respond({'error': str(exc)}, 404)

    def do_POST(self):
        try:
            # Reject cross-origin writes; this service is a local development app.
            origin = self.headers.get('Origin')
            if origin and origin not in ('http://127.0.0.1:8000', 'http://localhost:8000'):
                return self.respond({'error': 'Origin rejected'}, 403)
            if 'application/json' not in self.headers.get('Content-Type', ''):
                return self.respond({'error': 'JSON required'}, 415)
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 100000:
                return self.respond({'error': 'Invalid request size'}, 413)
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError('Expected JSON object')
            path = urlparse(self.path).path
            if path == '/api/analyze':
                validate_analysis_input(data.get('code'), data.get('error', ''))
                return self.respond(submit_job('analysis', {'code': data['code'], 'error': data.get('error', '')}), 202)
            if path.startswith('/api/jobs/') and path.endswith('/cancel'):
                return self.respond(cancel_job(path.split('/')[-2]))
            if path == '/api/edit':
                if not RUN_LOCK.acquire(blocking=False):
                    return self.respond({'error': 'A test run or edit is active; try again when it finishes'}, 409)
                try:
                    if session_has_active_job(data.get('id', '')):
                        return self.respond({'error': 'A test job is active for this session'}, 409)
                    return self.respond(edit(data.get('id', ''), data.get('fixed_code'), data.get('tests')))
                finally:
                    RUN_LOCK.release()
            if path == '/api/delete':
                if not RUN_LOCK.acquire(blocking=False):
                    return self.respond({'error': 'A test run or edit is active; try again when it finishes'}, 409)
                try:
                    if session_has_active_job(data.get('id', '')):
                        return self.respond({'error': 'A test job is active for this session'}, 409)
                    delete(data.get('id', ''))
                    return self.respond({'deleted': True})
                finally:
                    RUN_LOCK.release()
            if path in ('/api/run', '/api/review'):
                if path == '/api/run':
                    if not RUN_LOCK.acquire(blocking=False):
                        return self.respond({'error': 'Another session operation is active'}, 409)
                    try:
                        session = get(data.get('id', ''))
                        if session_has_active_job(session['id']):
                            return self.respond({'error': 'A test job is already active for this session'}, 409)
                        return self.respond(submit_job('test_run', {'id': session['id']}), 202)
                    finally:
                        RUN_LOCK.release()
                if not RUN_LOCK.acquire(blocking=False):
                    return self.respond({'error': 'Another session operation is active'}, 409)
                try:
                    if session_has_active_job(data.get('id', '')):
                        return self.respond({'error': 'A test job is active for this session'}, 409)
                    session = get(data.get('id', ''))
                    if path == '/api/review':
                        if data.get('review') not in ('accepted', 'rejected'):
                            raise ValueError('Invalid review status')
                        session['review'] = data['review']
                    save(session, session['id'])
                    return self.respond(session)
                finally:
                    RUN_LOCK.release()
            return self.respond({'error': 'Not found'}, 404)
        except (ValueError, SyntaxError) as exc:
            self.respond({'error': str(exc)}, 400)
        except Exception:
            self.respond({'error': 'Unexpected backend error. Check local server logs.'}, 500)
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    print('FixLab: http://127.0.0.1:8000', flush=True)
    ThreadingHTTPServer(('127.0.0.1', 8000), Handler).serve_forever()
