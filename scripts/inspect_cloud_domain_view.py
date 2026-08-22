"""Print the DOMAIN_VIEW the live Cloud Run revision actually loaded."""

from __future__ import annotations

import json
import time

from scripts.smoke_cloud_run import (
    EXPECTED_APP,
    PROBE_PROMPT,
    _extract_probe,
    _identity_token,
    _json_request,
    _run_prompt,
    _service_url,
)


def main() -> int:
    app_url = _service_url().rstrip("/")
    token = _identity_token(app_url)
    session_id = f"domain_view_probe_{int(time.time())}"
    session = _json_request(
        "POST",
        f"{app_url}/apps/{EXPECTED_APP}/users/cloud_test_user/sessions/{session_id}",
        token,
        body={},
    )
    if not isinstance(session, dict) or session.get("id") != session_id:
        raise SystemExit(f"session failed: {session}")
    text, events = _run_prompt(app_url, token, PROBE_PROMPT, session_id)
    probe = _extract_probe(events, text)
    details = (probe or {}).get("details") or {}
    payload = {
        "revision": ((probe or {}).get("runtime") or {}).get("revision"),
        "domain_view": details.get("domain_view"),
        "checks": (probe or {}).get("checks"),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
