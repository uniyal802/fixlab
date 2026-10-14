#!/bin/sh
set -eu
cd "$(dirname "$0")"
exec python3 backend/server.py
