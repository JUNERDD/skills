"""Shared helpers for YouTube Data API v3: API key discovery, request wrapper, URL parsing.

Standard library only and Python 3.8+ compatible, so it runs unchanged in Claude Code, Codex,
Cursor or any sandbox that has Python.
"""
from __future__ import annotations

import json
import os
import platform
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request

API = "https://www.googleapis.com/youtube/v3/"
ENV_NAME = "YOUTUBE_API_KEY"
CONFIG_ENV_FILE = os.path.expanduser("~/.config/youtube-analysis/.env")

# Quota cost per call, used to estimate daily usage; the default is 10,000 units per project per day
QUOTA_COST = {"channels": 1, "videos": 1, "playlistItems": 1, "commentThreads": 1,
              "comments": 1, "search": 100}


def _read_env_file(path: str) -> str | None:
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("export "):
                    line = line[len("export "):]
                if line.startswith(ENV_NAME + "="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'") or None
    except OSError:
        return None
    return None


def find_api_key(env_file: str | None = None) -> tuple[str | None, str | None]:
    """Look up the key in priority order and return (key, source description).

    Processes launched by GUI apps (Claude Desktop, Cursor, ...) do not inherit variables
    exported in a terminal, so .env files and macOS launchctl are checked as well.
    """
    key = os.environ.get(ENV_NAME)
    if key:
        return key.strip(), f"environment variable {ENV_NAME}"
    candidates = [p for p in (env_file, os.path.join(os.getcwd(), ".env"), CONFIG_ENV_FILE) if p]
    for path in candidates:
        key = _read_env_file(path)
        if key:
            return key, f"file {path}"
    if platform.system() == "Darwin":
        try:
            key = subprocess.run(["launchctl", "getenv", ENV_NAME], capture_output=True,
                                 text=True, timeout=5).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            key = ""
        if key:
            return key, f"launchctl getenv {ENV_NAME}"
    return None, None


def mask(key: str) -> str:
    return f"…{key[-4:]}" if key and len(key) > 8 else "****"


class ApiError(Exception):
    def __init__(self, status: int, reason: str, message: str):
        super().__init__(f"{status} {reason}: {message}")
        self.status, self.reason, self.message = status, reason, message


class Client:
    def __init__(self, key: str, timeout: int = 30):
        self.key, self.timeout, self.quota_used = key, timeout, 0

    def get(self, endpoint: str, **params) -> dict:
        params["key"] = self.key
        url = API + endpoint + "?" + urllib.parse.urlencode(params)
        self.quota_used += QUOTA_COST.get(endpoint, 1)
        try:
            with urllib.request.urlopen(url, timeout=self.timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            try:
                body = json.load(e)
            except ValueError:
                body = {}
            err = body.get("error", {})
            reason = (err.get("errors") or [{}])[0].get("reason") or err.get("status") or str(e.code)
            # The newer error format puts the reason in details[].reason (e.g. API_KEY_INVALID, SERVICE_DISABLED)
            for d in err.get("details", []) or []:
                if d.get("reason"):
                    reason = d["reason"]
                    break
            raise ApiError(e.code, reason, err.get("message", "")) from None


VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def parse_video_id(s: str) -> str:
    s = s.strip()
    if VIDEO_ID_RE.match(s):
        return s
    u = urllib.parse.urlparse(s if "://" in s else "https://" + s)
    if u.netloc.endswith("youtu.be"):
        return u.path.strip("/").split("/")[0]
    q = urllib.parse.parse_qs(u.query)
    if "v" in q:
        return q["v"][0]
    m = re.search(r"/(?:shorts|live|embed|v)/([A-Za-z0-9_-]{11})", u.path)
    if m:
        return m.group(1)
    raise ValueError(f"Cannot parse a video ID from {s!r}")


def parse_channel(s: str) -> tuple[str, str]:
    """Return (kind, value), where kind is id / handle / username / custom."""
    s = s.strip()
    if re.match(r"^UC[A-Za-z0-9_-]{22}$", s):
        return "id", s
    if s.startswith("@"):
        return "handle", s[1:]
    u = urllib.parse.urlparse(s if "://" in s else "https://" + s)
    parts = [p for p in u.path.split("/") if p]
    if parts:
        if parts[0].startswith("@"):
            return "handle", urllib.parse.unquote(parts[0][1:])
        if parts[0] == "channel" and len(parts) > 1:
            return "id", parts[1]
        if parts[0] == "user" and len(parts) > 1:
            return "username", parts[1]
        if parts[0] == "c" and len(parts) > 1:
            return "custom", parts[1]
    return "handle", s  # treat a bare string as a handle


def iso_duration_seconds(d: str) -> int:
    m = re.match(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", d or "")
    if not m:
        return 0
    days, h, mi, s = (int(x or 0) for x in m.groups())
    return days * 86400 + h * 3600 + mi * 60 + s
