"""Entrypoint wrapper for running from repository root."""
import os
import sys

# Ensure frontend and backend are in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
if FRONTEND_DIR not in sys.path:
    sys.path.insert(0, FRONTEND_DIR)

# Execute frontend app
with open(os.path.join(FRONTEND_DIR, "app.py"), "r", encoding="utf-8") as f:
    code = compile(f.read(), os.path.join(FRONTEND_DIR, "app.py"), "exec")
    exec(code, globals())
