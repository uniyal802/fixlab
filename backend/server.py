import json
import mimetypes
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from core import analyze, get, history, run_code, save, health, edit, delete

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
                return self.respond(analyze(data.get('code'), data.get('error', '')))
            if path == '/api/edit':
                if not RUN_LOCK.acquire(blocking=False):
                    return self.respond({'error': 'A test run or edit is active; try again when it finishes'}, 409)
                try:
                    return self.respond(edit(data.get('id', ''), data.get('fixed_code'), data.get('tests')))
                finally:
                    RUN_LOCK.release()
            if path == '/api/delete':
                if not RUN_LOCK.acquire(blocking=False):
                    return self.respond({'error': 'A test run or edit is active; try again when it finishes'}, 409)
                try:
                    delete(data.get('id', ''))
                    return self.respond({'deleted': True})
                finally:
                    RUN_LOCK.release()
            if path in ('/api/run', '/api/review'):
                if not RUN_LOCK.acquire(blocking=False):
                    return self.respond({'error': 'Another session operation is active'}, 409)
                try:
                    session = get(data.get('id', ''))
                    if path == '/api/review':
                        if data.get('review') not in ('accepted', 'rejected'):
                            raise ValueError('Invalid review status')
                        session['review'] = data['review']
                    else:
                        session['results'] = {'original': run_code(session['original_code'], session['analysis']['tests']), 'fixed': run_code(session['analysis']['fixed_code'], session['analysis']['tests'])}
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
