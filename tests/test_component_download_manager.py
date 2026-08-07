from __future__ import annotations

import hashlib
import threading
import tempfile
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from creator_intelligence_studio.application.services.download_manager_service import (
    ComponentDownloadManagerService,
    DownloadSourcePolicy,
)
from creator_intelligence_studio.domain.components.downloads import (
    ALLOWED_DOWNLOAD_STATUS_TRANSITIONS,
    ComponentDownloadOverwritePolicy,
    ComponentDownloadPriority,
    ComponentDownloadProgress,
    ComponentDownloadRequest,
    ComponentDownloadRetryPolicy,
    ComponentDownloadRecord,
    ComponentDownloadStatus,
    validate_download_transition,
)
from creator_intelligence_studio.infrastructure.downloads.repository import FileSystemComponentDownloadRepository
from creator_intelligence_studio.shared.paths import ProjectPaths


def _build_paths(root: Path) -> ProjectPaths:
    return ProjectPaths(
        project_root=root,
        config_directory=root / "config",
        data_directory=root / "data",
        components_directory=root / "data" / "components",
        downloads_directory=root / "data" / "downloads",
        database_path=root / "data" / "app.db",
        logs_directory=root / "logs",
        models_directory=root / "models",
        artifacts_directory=root / "artifacts",
    )


class _DownloadHandler(BaseHTTPRequestHandler):
    payload = b""
    etag = '"etag-1"'
    last_modified = "Wed, 01 Jan 2025 00:00:00 GMT"
    support_range = True
    disconnect_first = False
    request_count = 0

    def do_GET(self):
        type(self).request_count += 1
        payload = type(self).payload
        start = 0
        if self.headers.get("Range") and type(self).support_range:
            range_text = self.headers["Range"].strip()
            if range_text.startswith("bytes="):
                start = int(range_text.split("=", 1)[1].split("-", 1)[0])
        if type(self).disconnect_first and type(self).request_count == 1:
            self.send_response(200)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload[: max(1, len(payload) // 2)])
            self.wfile.flush()
            self.connection.shutdown(1)
            self.connection.close()
            return
        if start > 0 and type(self).support_range:
            body = payload[start:]
            self.send_response(206)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Content-Range", f"bytes {start}-{len(payload) - 1}/{len(payload)}")
        else:
            body = payload
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
        self.send_header("ETag", type(self).etag)
        self.send_header("Last-Modified", type(self).last_modified)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):  # noqa: A003
        pass


def _start_server(payload: bytes, *, support_range: bool = True, disconnect_first: bool = False):
    handler = type(
        "Handler",
        (_DownloadHandler,),
        {
            "payload": payload,
            "support_range": support_range,
            "disconnect_first": disconnect_first,
            "request_count": 0,
        },
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


class DownloadManagerTests(unittest.TestCase):
    def test_state_machine_rejects_invalid_transition(self) -> None:
        with self.assertRaises(ValueError):
            validate_download_transition(ComponentDownloadStatus.COMPLETED, ComponentDownloadStatus.DOWNLOADING)

    def test_duplicate_active_download_reuses_existing_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = _build_paths(root)
            paths.ensure_runtime_directories()
            repo = FileSystemComponentDownloadRepository(paths.downloads_directory)
            service = ComponentDownloadManagerService(paths=paths, repository=repo, recover_on_startup=False)
            request = ComponentDownloadRequest(
                component_id="component.dup",
                catalog_version=1,
                source_url="http://127.0.0.1:1234/artifact.bin",
                expected_sha256=None,
                expected_download_bytes=10,
                destination_logical_location="test",
                priority=ComponentDownloadPriority.NORMAL,
                user_initiated=True,
                retry_policy=ComponentDownloadRetryPolicy(max_attempts=1),
                overwrite_policy=ComponentDownloadOverwritePolicy.REJECT,
                allow_localhost=True,
                test_mode=True,
            )
            record = ComponentDownloadRecord(
                download_id="dup-1",
                identity_key=request.identity_key(),
                component_id=request.component_id,
                catalog_version=request.catalog_version,
                source_url=request.source_url,
                expected_sha256=request.expected_sha256,
                expected_download_bytes=request.expected_download_bytes,
                destination_logical_location=request.destination_logical_location,
                priority=request.priority,
                user_initiated=request.user_initiated,
                retry_policy=request.retry_policy,
                overwrite_policy=request.overwrite_policy,
                allowed_domains=request.allowed_domains,
                allow_localhost=request.allow_localhost,
                test_mode=request.test_mode,
                max_redirects=request.max_redirects,
                connect_timeout_seconds=request.connect_timeout_seconds,
                read_timeout_seconds=request.read_timeout_seconds,
                stalled_timeout_seconds=request.stalled_timeout_seconds,
                chunk_size_bytes=request.chunk_size_bytes,
                safety_margin_bytes=request.safety_margin_bytes,
                status=ComponentDownloadStatus.QUEUED,
                progress=ComponentDownloadProgress(),
                partial_path=str(paths.downloads_directory / "component.dup" / "dup-1.partial"),
                verified_artifact_path=str(paths.downloads_directory / "component.dup" / "dup-1.verified"),
            )
            repo.save_record(record)
            reused = service.start_download(request)
            self.assertEqual(reused.download_id, record.download_id)
            self.assertEqual(reused.status, ComponentDownloadStatus.QUEUED)

    def test_source_policy_blocks_public_http_without_test_mode(self) -> None:
        policy = DownloadSourcePolicy(allow_localhost=False, test_mode=False)
        with self.assertRaises(ValueError):
            policy.validate("http://example.com/file.bin", allowed_domains=())

    def test_source_policy_allows_localhost_in_test_mode(self) -> None:
        policy = DownloadSourcePolicy(allow_localhost=True, test_mode=True)
        policy.validate("http://127.0.0.1:1234/file.bin", allowed_domains=())

    def test_simple_download_completes_and_verifies(self) -> None:
        payload = b"simple download payload"
        server, _ = _start_server(payload)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                paths = _build_paths(root)
                paths.ensure_runtime_directories()
                repo = FileSystemComponentDownloadRepository(paths.downloads_directory)
                service = ComponentDownloadManagerService(paths=paths, repository=repo, recover_on_startup=False)
                request = ComponentDownloadRequest(
                    component_id="component.simple",
                    catalog_version=1,
                    source_url=f"http://127.0.0.1:{server.server_address[1]}/artifact.bin",
                    expected_sha256=hashlib.sha256(payload).hexdigest(),
                    expected_download_bytes=len(payload),
                    destination_logical_location="test",
                    priority=ComponentDownloadPriority.NORMAL,
                    user_initiated=True,
                    retry_policy=ComponentDownloadRetryPolicy(max_attempts=1),
                    overwrite_policy=ComponentDownloadOverwritePolicy.REJECT,
                    allow_localhost=True,
                    test_mode=True,
                )
                record = service.start_download(request)
                terminal = service.wait_for_terminal(record.download_id, timeout_seconds=10)
                self.assertIsNotNone(terminal)
                self.assertEqual(terminal.status, ComponentDownloadStatus.COMPLETED)
                self.assertTrue(Path(terminal.verified_artifact_path).exists())
                self.assertEqual(terminal.verified_sha256, hashlib.sha256(payload).hexdigest())
        finally:
            server.shutdown()
            server.server_close()

    def test_resume_after_disconnect_uses_range(self) -> None:
        payload = b"abcdefghij" * 1024
        server, _ = _start_server(payload, disconnect_first=True)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                paths = _build_paths(root)
                paths.ensure_runtime_directories()
                repo = FileSystemComponentDownloadRepository(paths.downloads_directory)
                service = ComponentDownloadManagerService(paths=paths, repository=repo, recover_on_startup=False)
                request = ComponentDownloadRequest(
                    component_id="component.resume",
                    catalog_version=1,
                    source_url=f"http://127.0.0.1:{server.server_address[1]}/artifact.bin",
                    expected_sha256=hashlib.sha256(payload).hexdigest(),
                    expected_download_bytes=len(payload),
                    destination_logical_location="test",
                    priority=ComponentDownloadPriority.NORMAL,
                    user_initiated=True,
                    retry_policy=ComponentDownloadRetryPolicy(max_attempts=2, backoff_seconds=0.01),
                    overwrite_policy=ComponentDownloadOverwritePolicy.REJECT,
                    allow_localhost=True,
                    test_mode=True,
                )
                record = service.start_download(request)
                terminal = service.wait_for_terminal(record.download_id, timeout_seconds=10)
                self.assertEqual(terminal.status, ComponentDownloadStatus.COMPLETED)
                self.assertEqual(terminal.verified_size_bytes, len(payload))
                self.assertGreaterEqual(server.RequestHandlerClass.request_count, 2)
        finally:
            server.shutdown()
            server.server_close()

    def test_hash_mismatch_fails(self) -> None:
        payload = b"hash mismatch payload"
        server, _ = _start_server(payload)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                paths = _build_paths(root)
                paths.ensure_runtime_directories()
                repo = FileSystemComponentDownloadRepository(paths.downloads_directory)
                service = ComponentDownloadManagerService(paths=paths, repository=repo, recover_on_startup=False)
                request = ComponentDownloadRequest(
                    component_id="component.hash",
                    catalog_version=1,
                    source_url=f"http://127.0.0.1:{server.server_address[1]}/artifact.bin",
                    expected_sha256="0" * 64,
                    expected_download_bytes=len(payload),
                    destination_logical_location="test",
                    priority=ComponentDownloadPriority.NORMAL,
                    user_initiated=True,
                    retry_policy=ComponentDownloadRetryPolicy(max_attempts=1),
                    overwrite_policy=ComponentDownloadOverwritePolicy.REJECT,
                    allow_localhost=True,
                    test_mode=True,
                )
                record = service.start_download(request)
                terminal = service.wait_for_terminal(record.download_id, timeout_seconds=10)
                self.assertEqual(terminal.status, ComponentDownloadStatus.FAILED)
                self.assertIsNotNone(terminal.error)
                self.assertEqual(terminal.error.category.value, "sha256_mismatch")
        finally:
            server.shutdown()
            server.server_close()

    def test_restart_recovery_marks_running_download_interrupted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = _build_paths(root)
            paths.ensure_runtime_directories()
            repo = FileSystemComponentDownloadRepository(paths.downloads_directory)
            service = ComponentDownloadManagerService(paths=paths, repository=repo, recover_on_startup=False)
            request = ComponentDownloadRequest(
                component_id="component.recovery",
                catalog_version=1,
                source_url="http://127.0.0.1:1234/artifact.bin",
                expected_sha256=None,
                expected_download_bytes=10,
                destination_logical_location="test",
                priority=ComponentDownloadPriority.NORMAL,
                user_initiated=True,
                retry_policy=ComponentDownloadRetryPolicy(max_attempts=1),
                overwrite_policy=ComponentDownloadOverwritePolicy.REJECT,
                allow_localhost=True,
                test_mode=True,
            )
            record = ComponentDownloadRecord(
                download_id="rec-1",
                identity_key=request.identity_key(),
                component_id=request.component_id,
                catalog_version=request.catalog_version,
                source_url=request.source_url,
                expected_sha256=request.expected_sha256,
                expected_download_bytes=request.expected_download_bytes,
                destination_logical_location=request.destination_logical_location,
                priority=request.priority,
                user_initiated=request.user_initiated,
                retry_policy=request.retry_policy,
                overwrite_policy=request.overwrite_policy,
                allowed_domains=request.allowed_domains,
                allow_localhost=request.allow_localhost,
                test_mode=request.test_mode,
                max_redirects=request.max_redirects,
                connect_timeout_seconds=request.connect_timeout_seconds,
                read_timeout_seconds=request.read_timeout_seconds,
                stalled_timeout_seconds=request.stalled_timeout_seconds,
                chunk_size_bytes=request.chunk_size_bytes,
                safety_margin_bytes=request.safety_margin_bytes,
                status=ComponentDownloadStatus.DOWNLOADING,
                progress=ComponentDownloadProgress(),
                partial_path=str(paths.downloads_directory / "component.recovery" / "rec-1.partial"),
                verified_artifact_path=str(paths.downloads_directory / "component.recovery" / "rec-1.verified"),
            )
            repo.save_record(record)
            recovered = service.recover_interrupted_downloads()
            self.assertEqual(len(recovered), 1)
            self.assertEqual(recovered[0].status, ComponentDownloadStatus.INTERRUPTED)


if __name__ == "__main__":
    unittest.main()
