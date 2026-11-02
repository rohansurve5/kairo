"""Shared paths and helpers for Kairo tests (fake user only)."""
import copy
import json
import os
import sys

TESTS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TESTS)
SKILL = os.path.join(ROOT, "skill", "kairo")
SCRIPTS = os.path.join(SKILL, "scripts")
PRIYA = os.path.join(TESTS, "fixtures", "priya")
OUTPUT = os.path.join(TESTS, "output")
FACTS = os.path.join(PRIYA, "my-facts.md")

sys.dont_write_bytecode = True  # keep __pycache__ out of the skill folder
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"  # same for scripts run as subprocesses
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)


def fixture(name):
    return os.path.join(PRIYA, name)


def load(name):
    with open(fixture(name), encoding="utf-8") as fh:
        return json.load(fh)


def write_tmp(obj, name, folder=None):
    folder = folder or os.path.join(OUTPUT, "tmp")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, name)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2)
    return path


def mutated(name, fn):
    obj = copy.deepcopy(load(name))
    fn(obj)
    return obj
