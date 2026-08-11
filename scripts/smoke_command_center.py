from __future__ import annotations

import argparse
import json
import secrets
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from video_intelligence.command_center.server import CommandCenterHTTPServer


def request(
    base_url: str,
    path: str,
    *,
    token: str | None = None,
    method: str = "GET",
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, object] | None]:
    request_headers = dict(headers or {})
    if token is not None:
        request_headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        f"{base_url}{path}",
        method=method,
        data=data,
        headers=request_headers,
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            body = response.read()
            return response.status, json.loads(body) if body else None
    except urllib.error.HTTPError as exc:
        exc.read()
        return exc.code, None


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test the authenticated loopback jobs API.")
    parser.add_argument("--media", type=Path, required=True)
    args = parser.parse_args()
    media = args.media.resolve(strict=True)

    with tempfile.TemporaryDirectory(prefix="mvi-command-center-smoke-") as temporary:
        state_dir = Path(temporary)
        token = secrets.token_urlsafe(32)
        server = CommandCenterHTTPServer(
            ("127.0.0.1", 0),
            token,
            state_dir,
            max(media.stat().st_size, 1),
        )
        service = threading.Thread(target=server.serve_forever, daemon=True)
        service.start()
        base_url = f"http://127.0.0.1:{server.server_port}"
        try:
            unauthorized, _ = request(base_url, "/api/jobs")
            hostile_origin, _ = request(
                base_url,
                "/api/jobs",
                token=token,
                headers={"Origin": "http://hostile.invalid"},
            )
            accepted, job = request(
                base_url,
                "/api/jobs",
                token=token,
                method="POST",
                data=media.read_bytes(),
                headers={
                    "Content-Type": "application/octet-stream",
                    "X-Filename": media.name,
                    "X-MVI-Authorized": "true",
                },
            )
            if accepted != 202 or job is None:
                raise RuntimeError(f"upload was not accepted: HTTP {accepted}")
            job_id = str(job["job_id"])
            deadline = time.monotonic() + 15
            while job["status"] not in {"succeeded", "failed", "cancelled"}:
                if time.monotonic() >= deadline:
                    raise RuntimeError("processing job did not finish in time")
                time.sleep(0.1)
                _status, refreshed = request(base_url, f"/api/jobs/{job_id}", token=token)
                if refreshed is None:
                    raise RuntimeError("processing job disappeared")
                job = refreshed
            retained_media = state_dir / "data" / "media" / job_id
            media_retained_before_delete = retained_media.exists()
            removed, _ = request(
                base_url,
                f"/api/jobs/{job_id}",
                token=token,
                method="DELETE",
            )
            report = job.get("report")
            valid = isinstance(report, dict) and report.get("valid") is True
            service_status = server.public_status()
            result = {
                "service_version": service_status.version,
                "max_active_jobs": service_status.max_active_jobs,
                "unauthorized_status": unauthorized,
                "hostile_origin_status": hostile_origin,
                "upload_status": accepted,
                "job_status": job["status"],
                "media_valid": valid,
                "media_retained_before_delete": media_retained_before_delete,
                "media_removed_after_delete": not retained_media.exists(),
                "result_remove_status": removed,
            }
            print(json.dumps(result, indent=2))
            return (
                0
                if all(
                    (
                        unauthorized == 401,
                        hostile_origin == 403,
                        service_status.max_active_jobs == 2,
                        job["status"] == "succeeded",
                        valid,
                        media_retained_before_delete,
                        not retained_media.exists(),
                        removed == 204,
                    )
                )
                else 1
            )
        finally:
            server.shutdown()
            service.join(timeout=5)
            server.job_manager.shutdown()
            server.server_close()


if __name__ == "__main__":
    raise SystemExit(main())
