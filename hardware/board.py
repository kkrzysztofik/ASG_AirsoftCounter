"""Pick the board module the generators work on: BOARD=carrier (default, design.py) or BOARD=pack (pack.py).

Every generator imports the board as `from board import design`, so the same code
builds either board from its own data module.
"""
import importlib
import os

NAME = os.environ.get("BOARD", "carrier")
design = importlib.import_module({"carrier": "design", "pack": "pack"}[NAME])
