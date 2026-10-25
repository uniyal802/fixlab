# Identity, quotas, and data retention

FixLab keeps its local single-user workflow by default. This change adds an API identity adapter and owner-scoped SQLite records for deployments that already have a secure way to issue bearer credentials. It does not provide sign-up, OAuth, password handling, a hosted deployment, or a hardened code-execution service.

## Local mode

`FIXLAB_AUTH_MODE` defaults to `local`. The Python API binds to `127.0.0.1:8000` and treats the local database owner as `local`. Existing sessions and jobs are assigned to this owner by an additive SQLite schema migration. Local retention is disabled unless `FIXLAB_RETENTION_DAYS` is set to a positive value.

## Required-auth API mode

Set `FIXLAB_AUTH_MODE=required` and provide a JSON array in `FIXLAB_AUTH_TOKENS` through a deployment secret manager. Each configured bearer token maps to an opaque owner ID. Do not commit real credentials or place tokens in logs, prompts, local storage, or source files.

Example shape (replace the placeholder with a randomly generated secret of at least 24 characters):

```json
[
  {
    "token": "replace-with-a-random-secret-at-least-24-chars",
    "owner_id": "account-123",
    "quotas": {
      "active_jobs": 20,
      "request_bytes": 100000,
      "storage_bytes": 104857600
    }
  }
]
```

All `/api/*` routes require `Authorization: Bearer <token>` in required-auth mode. Unknown IDs return not-found responses for session and job reads, preventing cross-owner existence checks. Session list, read, edit, review, delete, test-run submission, job status, and cancellation all apply the authenticated owner. Static frontend assets are not an authentication flow; a hosted UI needs a separate secure credential integration and must not persist bearer credentials in browser storage.

Each quota may be omitted to use its global default:

| Quota | Default | Maximum accepted value |
| --- | ---: | ---: |
| `active_jobs` | 20 per owner | 1,000 |
| `request_bytes` | 100,000 bytes | 10,000,000 bytes |
| `storage_bytes` | 104,857,600 bytes | 1,000,000,000,000 bytes |

Global defaults can be changed with `FIXLAB_OWNER_MAX_ACTIVE_JOBS`, `FIXLAB_MAX_REQUEST_BYTES`, and `FIXLAB_OWNER_STORAGE_BYTES`. Storage accounting includes session payloads and job inputs, results, and errors. Jobs retain the quota snapshot taken at submission so queued work cannot evade a later lower limit.

Required-auth mode also requires `FIXLAB_RETENTION_DAYS` to be a positive integer (maximum 36,500). The worker removes sessions older than the retention window and terminal job records whose finish time has expired, at startup and hourly. Active jobs are not removed. Deleting a session also deletes its terminal test-run job records. A session referenced by an active test job is protected from expiry until that job finishes. Local mode leaves data indefinitely by default; users can delete sessions in the UI.

This is an API credential adapter, not a full account system. Configure it only behind a deployment boundary that protects and rotates bearer credentials. Do not expose the local service directly to the public internet. Public execution still requires a separate isolation, abuse prevention, and operations review.

## Existing SQLite data migration

The schema migration adds an `owner_id` to older local sessions/jobs and assigns them to `local`. This preserves existing local use. To transfer those records to a configured account, stop the API and worker first. Run a dry-run to see row counts:

```bash
python3 backend/migrate_owner.py --database data/sessions.db --owner-id account-123
```

Then apply only after choosing a new backup path. The command refuses to overwrite an existing backup file:

```bash
python3 backend/migrate_owner.py \
  --database data/sessions.db \
  --owner-id account-123 \
  --backup data/sessions.pre-owner-migration.db \
  --apply
```

The tool takes an SQLite backup before changing ownership and moves only rows currently owned by `local`. Keep the backup protected like the database: both contain submitted source and generated output in plaintext. If the migration needs to be rolled back, stop the services and restore that backup before restarting them.
