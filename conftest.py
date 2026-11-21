"""
conftest.py — pytest configuration at the project root.

WHAT: An empty file in the project root.
WHY:  When pytest finds a conftest.py here, it adds this folder to Python's import path.
      That lets tests write `from app.main import app` without installing the project.
"""
