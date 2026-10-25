"""Safely reassign legacy single-user SQLite data to a configured account.

Run with the API and worker stopped. First run without --apply to inspect the
row counts. Applying requires a new backup file and an explicit owner id.
"""
import argparse
import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch
from auth import OWNER_PATTERN
import core


def migrate_owner(database, owner_id, backup=None, apply=False):
    database = Path(database).resolve()
    if not OWNER_PATTERN.fullmatch(owner_id) or owner_id == core.LOCAL_OWNER:
        raise ValueError('Choose a valid, non-local owner id')
    with patch.object(core, 'DB', database):
        with core.connection() as schema_db:
            pass
    db = sqlite3.connect(database, timeout=10)
    try:
        if apply:
            if not backup:
                raise ValueError('A new --backup path is required with --apply')
            backup_path = Path(backup).resolve()
            if backup_path == database or backup_path.exists():
                raise ValueError('Backup path must be different from the database and must not exist')
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            file_descriptor, temporary_name = tempfile.mkstemp(prefix=backup_path.name + '.', suffix='.tmp', dir=backup_path.parent)
            os.close(file_descriptor)
            temporary_backup = Path(temporary_name)
            backup_db = sqlite3.connect(temporary_backup)
            try:
                try:
                    db.backup(backup_db)
                except Exception:
                    temporary_backup.unlink(missing_ok=True)
                    raise
            finally:
                backup_db.close()
            os.replace(temporary_backup, backup_path)
        db.execute('BEGIN EXCLUSIVE')
        session_count = db.execute("SELECT COUNT(*) FROM sessions WHERE owner_id='local'").fetchone()[0]
        job_count = db.execute("SELECT COUNT(*) FROM jobs WHERE owner_id='local'").fetchone()[0]
        if not apply:
            db.rollback()
            return {'sessions': session_count, 'jobs': job_count, 'applied': False}
        db.execute("UPDATE sessions SET owner_id=? WHERE owner_id='local'", (owner_id,))
        db.execute("UPDATE jobs SET owner_id=? WHERE owner_id='local'", (owner_id,))
        db.commit()
        return {'sessions': session_count, 'jobs': job_count, 'applied': True, 'backup': str(backup_path)}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', default=str(core.DB))
    parser.add_argument('--owner-id', required=True)
    parser.add_argument('--backup', help='new SQLite backup file, required with --apply')
    parser.add_argument('--apply', action='store_true', help='reassign local records after creating the backup')
    args = parser.parse_args()
    print(migrate_owner(args.database, args.owner_id, args.backup, args.apply))


if __name__ == '__main__':
    main()
