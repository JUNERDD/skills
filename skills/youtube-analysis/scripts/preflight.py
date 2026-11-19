#!/usr/bin/env python3
"""Check whether the YouTube Data API side is ready and say what to do next.

Checks, in order: Python version -> API key can be found -> googleapis.com is reachable ->
the key is valid and the API is enabled.
vidIQ is an MCP connector that a script cannot see; the agent checks it by calling
vidiq_balance (see SKILL.md).

Usage:
    python3 scripts/preflight.py            # human-readable table
    python3 scripts/preflight.py --json     # machine-readable
    python3 scripts/preflight.py --env-file path/to/.env

Exit code: 0 = ready, 1 = not ready. Only the last 4 characters of the key are printed.
"""
from __future__ import annotations

import argparse
import json
import socket
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ytapi import ENV_NAME, CONFIG_ENV_FILE, ApiError, Client, find_api_key, mask  # noqa: E402

SETUP = "references/setup.md"

# Error reason returned by Google -> plain explanation and fix
REASON_HINTS = {
    "API_KEY_INVALID": ("The key is invalid (copied incompletely or deleted)",
                        f"Copy the key again or create a new one in Google Cloud. See 'YouTube Data API key' in {SETUP}"),
    "keyInvalid": ("The key is invalid", f"Copy the key again. See {SETUP}"),
    "badRequest": ("The key is invalid", f"Copy the key again. See {SETUP}"),
    "SERVICE_DISABLED": ("YouTube Data API v3 is not enabled for this Google Cloud project",
                         "Google Cloud Console -> APIs & Services -> Library -> search YouTube Data API v3 -> Enable, "
                         "then wait 1-2 minutes and retry"),
    "accessNotConfigured": ("YouTube Data API v3 is not enabled for the project",
                            "Enable YouTube Data API v3 in Google Cloud Console"),
    "API_KEY_SERVICE_BLOCKED": ("The key's API restrictions do not include YouTube Data API v3",
                                "Credentials -> edit the key -> add YouTube Data API v3 under API restrictions"),
    "API_KEY_HTTP_REFERRER_BLOCKED": ("The key has a website (referrer) restriction, which blocks script calls",
                                      "Set Application restrictions to None or to IP addresses"),
    "API_KEY_IP_ADDRESS_BLOCKED": ("The key has an IP restriction and the current IP is not allowed",
                                   "Add the current egress IP to the key's IP restriction, or set it to None"),
    "ipRefererBlocked": ("The key's application restriction blocked the request",
                         "Check the key's Application restrictions"),
    "quotaExceeded": ("Today's quota is used up (default 10,000 units per day)",
                      "Wait for the reset at midnight Pacific Time, or request a quota increase in Cloud Console"),
    "RATE_LIMIT_EXCEEDED": ("Rate limited for sending requests too fast", "Wait a minute and retry"),
    "forbidden": ("The request was refused", "Check whether the key's project is disabled or has a billing problem"),
}


def check(env_file: str | None) -> dict:
    checks = []

    def add(name, ok, detail, fix=None):
        checks.append({"name": name, "ok": ok, "detail": detail, "fix": fix})
        return ok

    add("python", sys.version_info >= (3, 8), f"Python {sys.version.split()[0]}",
        None if sys.version_info >= (3, 8) else "Python 3.8 or newer is required")

    key, source = find_api_key(env_file)
    if not add("api_key", bool(key),
               f"found ({source}, {mask(key)})" if key else f"{ENV_NAME} not found",
               None if key else f"Create a key as described under 'YouTube Data API key' in {SETUP}, then save it to "
                                f"{CONFIG_ENV_FILE} (one line: {ENV_NAME}=your-key) or set it as an environment "
                                f"variable. Do not paste the key into the chat."):
        return {"ready": False, "checks": checks}

    try:
        socket.create_connection(("www.googleapis.com", 443), timeout=8).close()
        net_ok = True
    except OSError as e:
        net_ok = False
        add("network", False, f"cannot reach www.googleapis.com:443 ({e})",
            "Check the network or proxy; in a cloud sandbox, googleapis.com may need to be added to the network "
            "allowlist. If it stays unreachable, fall back to vidIQ-only mode (costs more credits)")
    if net_ok:
        add("network", True, "www.googleapis.com is reachable")
    else:
        return {"ready": False, "checks": checks}

    client = Client(key, timeout=15)
    try:
        r = client.get("videos", part="id", id="dQw4w9WgXcQ")  # 1 quota unit
        ok = "items" in r
        add("api_access", ok, "key is valid and YouTube Data API v3 is available (this check used 1 quota unit)" if ok
            else f"unexpected response: {json.dumps(r)[:200]}")
    except ApiError as e:
        what, fix = REASON_HINTS.get(e.reason, (f"{e.status} {e.reason}", e.message))
        add("api_access", False, what, fix)
    except OSError as e:
        add("api_access", False, f"request failed: {e}", "Check the network or proxy and retry")

    return {"ready": all(c["ok"] for c in checks), "checks": checks, "key_source": source}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--env-file")
    args = ap.parse_args()
    res = check(args.env_file)
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print("YouTube Data API dependency check")
        for c in res["checks"]:
            print(f"  [{'OK' if c['ok'] else 'MISSING'}] {c['name']}: {c['detail']}")
            if c["fix"]:
                print(f"        -> {c['fix']}")
        print("Result: " + ("ready" if res["ready"] else "not ready"))
    sys.exit(0 if res["ready"] else 1)


if __name__ == "__main__":
    main()
