"""Read-only smoke check for a running AI Surveillance backend."""

import argparse
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


READ_ONLY_ENDPOINTS = (
    "/health",
    "/health/readiness",
    "/members",
    "/cameras",
    "/surveillance/status",
    "/logs?limit=1",
    "/alerts?limit=1",
)


def request_json(base_url: str, path: str) -> object:
    request = Request(
        f"{base_url.rstrip('/')}{path}",
        headers={"Accept": "application/json"},
    )
    with urlopen(request, timeout=10) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status}")
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Running FastAPI base URL",
    )
    arguments = parser.parse_args()

    failures: list[str] = []
    for endpoint in READ_ONLY_ENDPOINTS:
        try:
            payload = request_json(arguments.base_url, endpoint)
            if endpoint == "/health/readiness":
                readiness = payload
                if not isinstance(readiness, dict):
                    raise RuntimeError("readiness response is not an object")
                if readiness.get("status") != "ready":
                    raise RuntimeError(
                        f"backend is {readiness.get('status', 'unknown')}"
                    )
            print(f"PASS {endpoint}")
        except (HTTPError, URLError, RuntimeError, ValueError) as exc:
            failures.append(f"{endpoint}: {exc}")
            print(f"FAIL {endpoint}: {exc}")

    if failures:
        print(f"\nSmoke test failed ({len(failures)} endpoint(s)).")
        return 1
    print("\nSmoke test passed. Backend is ready for Flutter.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
