import io
import json
import time
import unittest
from unittest import mock
from dataclasses import replace

import edge_app
from test_edge_app import config


def success(value):
    return 200, json.dumps({"ok": True, "result": value}).encode()


class PollingTests(unittest.TestCase):
    def test_switch_keeps_pending_queue_and_does_not_change_foreign_webhook(self):
        for url, allowed in [(config().public_webhook_url, True), ("https://foreign.example/", False), ("", True)]:
            calls = []
            def request(endpoint, raw, headers):
                method = endpoint.rsplit("/", 1)[-1]
                calls.append((method, json.loads(raw)))
                return success({"url": url} if method == "getWebhookInfo" else True)
            ingress = edge_app.PollingIngress(edge_app.EdgeService(config(), request))
            if allowed:
                ingress.initialize()
                self.assertTrue(ingress.initialized)
            else:
                with self.assertRaises(ConnectionError): ingress.initialize()
            deletes = [p for method, p in calls if method == "deleteWebhook"]
            self.assertEqual(deletes, [{"drop_pending_updates": False}] if url == config().public_webhook_url else [])

    def test_failed_core_blocks_offset_and_suffix_then_retries_without_loss(self):
        seen_offsets, delivered = [], []
        failed = False
        def request(url, raw, headers):
            nonlocal failed
            data = json.loads(raw)
            if url.endswith("getUpdates"):
                seen_offsets.append(data["offset"])
                self.assertGreater(data["timeout"], 0)
                return success([{"update_id": n} for n in ([10, 11] if len(seen_offsets) == 1 else [11, 12])])
            self.assertEqual(headers["X-Aimytime-Edge-Auth"], "edge-secret")
            delivered.append(data["update_id"])
            if data["update_id"] == 11 and not failed:
                failed = True
                return 503, b""
            return 204, b""
        ingress = edge_app.PollingIngress(edge_app.EdgeService(config(), request))
        ingress.initialized = True
        with self.assertRaises(ConnectionError): ingress.poll_once()
        self.assertEqual(ingress.offset, 11)
        self.assertFalse(ingress.healthy())
        ingress.poll_once()
        self.assertEqual(seen_offsets, [0, 11])
        self.assertEqual(delivered, [10, 11, 11, 12])
        self.assertEqual(ingress.offset, 13)
        self.assertTrue(ingress.healthy())

    def test_restart_replays_unconfirmed_tail_instead_of_assuming_ack(self):
        calls = []
        def request(url, raw, headers):
            data = json.loads(raw)
            calls.append((url.rsplit("/", 1)[-1], data))
            return success([{"update_id": 42}]) if url.endswith("getUpdates") else (204, b"")
        service = edge_app.EdgeService(config(), request)
        for _ in range(2):
            ingress = edge_app.PollingIngress(service)
            ingress.poll_once()
            self.assertEqual(ingress.offset, 43)
        self.assertEqual([payload["offset"] for method, payload in calls if method == "getUpdates"], [0, 0])
        self.assertEqual([method for method, _ in calls], ["getUpdates", "lead", "getUpdates", "lead"])

    def test_invalid_batch_never_confirms_or_forwards_a_prefix(self):
        for batch in ([{"update_id": 10}, {"update_id": 9}], [{"update_id": True}], {"update_id": 10}, [{"update_id": 1}, {}]):
            calls = []
            def request(url, raw, headers):
                calls.append(url)
                return success(batch)
            ingress = edge_app.PollingIngress(edge_app.EdgeService(config(), request))
            with self.assertRaises(ConnectionError): ingress.poll_once()
            self.assertEqual(ingress.offset, 0)
            self.assertEqual(len(calls), 1)

    def test_telegram_errors_never_ack_or_forward(self):
        for status, body in [(409, b'{}'), (200, b'{"ok":false}'), (200, b'not-json')]:
            ingress = edge_app.PollingIngress(edge_app.EdgeService(config(), lambda *_: (status, body)))
            with self.assertRaises(ConnectionError): ingress.poll_once()
            self.assertEqual(ingress.offset, 0)

    def test_exception_urls_never_reach_logs(self):
        ingress = edge_app.PollingIngress(edge_app.EdgeService(config()))
        def fail():
            ingress.stop.set()
            raise RuntimeError("https://api.telegram.org/botSECRET/getUpdates")
        with mock.patch.object(ingress, "initialize", side_effect=fail), mock.patch("sys.stderr", new_callable=io.StringIO) as output:
            ingress.run()
        self.assertNotIn("SECRET", output.getvalue())
        self.assertIn("status=retry", output.getvalue())

    def test_health_requires_successful_recent_poll(self):
        ingress = edge_app.PollingIngress(edge_app.EdgeService(config()))
        self.assertFalse(ingress.healthy())
        ingress.initialized, ingress.last_poll = True, time.monotonic()
        self.assertTrue(ingress.healthy())
        ingress.last_poll -= 91
        self.assertFalse(ingress.healthy())


if __name__ == "__main__": unittest.main()
