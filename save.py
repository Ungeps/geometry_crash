"""Persistent meta: top-10 records and the Book of Links. Nothing else carries between runs."""
import json
import os

import config as C

KEYS = ("time", "kills", "level", "result")


def load():
    """First run (no file) and broken file both give a clean empty state, never a crash."""
    data = {"records": [], "fusions": []}
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), C.RECORDS_FILE)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        recs = raw.get("records", [])
        data["records"] = [r for r in recs if isinstance(r, dict) and "time" in r]
        fusions = raw.get("fusions", [])
        data["fusions"] = [f for f in fusions if isinstance(f, str)]
    except (OSError, ValueError):
        pass
    return data


def add_record(data, entry):
    data["records"].append(entry)
    data["records"].sort(key=lambda r: (r.get("time", 0), r.get("kills", 0)), reverse=True)
    data["records"] = data["records"][:C.TOP_RECORDS]
    return data


def add_fusions(data, ids):
    known = set(data["fusions"])
    for fid in ids:
        known.add(fid)
    data["fusions"] = sorted(known)
    return data


def write(data):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), C.RECORDS_FILE)
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        return True
    except OSError:
        return False


def load_settings():
    """Menu settings (language, fullscreen). Missing/broken file -> clean defaults, no crash."""
    s = {"lang": C.DEFAULT_LANG, "fullscreen": False}
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), C.SETTINGS_FILE)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        if raw.get("lang") in C.LANGS:
            s["lang"] = raw["lang"]
        s["fullscreen"] = bool(raw.get("fullscreen", False))
    except (OSError, ValueError):
        pass
    return s


def write_settings(s):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), C.SETTINGS_FILE)
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"lang": s.get("lang", C.DEFAULT_LANG), "fullscreen": bool(s.get("fullscreen"))},
                      fh, indent=2)
        return True
    except OSError:
        return False
