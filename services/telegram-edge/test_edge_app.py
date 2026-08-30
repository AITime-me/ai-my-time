import json
import unittest

from edge_app import EdgeConfig, EdgeService


def config() -> EdgeConfig:
    return EdgeConfig(
        "token",
        "telegram-secret",
        "core-secret",
        "edge-secret",
        "https://core.example/webhooks/telegram/lead",
        "https://edge.example/webhooks/telegram/lead",
    )


class EdgeServiceTests(unittest.TestCase):
    def test_rejects_invalid_webhook_secret_without_forwarding(self) -> None:
        service = EdgeService(config(), requester=lambda *_: self.fail("must not forward"))
        self.assertEqual(service.accept_webhook(b"{}", "wrong"), 401)

    def test_returns_502_when_core_does_not_accept_update(self) -> None:
        service = EdgeService(config(), requester=lambda *_: (503, b"{}"))
        self.assertEqual(service.accept_webhook(b'{"update_id":1}', "telegram-secret"), 502)

    def test_forwards_webhook_with_edge_auth_and_preserves_success_semantics(self) -> None:
        seen = {}
        def requester(url, body, headers):
            seen.update(url=url, body=body, headers=headers)
            return 204, b""
        service = EdgeService(config(), requester=requester)
        self.assertEqual(service.accept_webhook(b'{"update_id":1}', "telegram-secret"), 204)
        self.assertEqual(seen["url"], "https://core.example/webhooks/telegram/lead")
        self.assertEqual(seen["headers"]["X-Aimytime-Edge-Auth"], "edge-secret")

    def test_outbound_allowlist_and_normalized_success(self) -> None:
        service = EdgeService(config(), requester=lambda *_: (200, json.dumps({"ok": True, "result": {"id": 1}}).encode()))
        self.assertEqual(service.invoke_telegram("getUpdates", b"{}", "core-secret")[0], 404)
        status, result = service.invoke_telegram("sendChatAction", b'{"chat_id":"1","action":"typing"}', "core-secret")
        self.assertEqual(status, 200)
        self.assertEqual(result, {"ok": True})

    def test_configure_webhook_keeps_url_and_secret_edge_local(self) -> None:
        calls = []

        def requester(url, body, headers):
            calls.append((url, body, headers))
            return 200, json.dumps({"ok": True, "result": True}).encode()

        status, result = EdgeService(config(), requester=requester).invoke_telegram(
            "configureWebhook", b"{}", "core-secret"
        )
        self.assertEqual((status, result), (200, {"ok": True}))
        self.assertEqual(calls[0][0], "https://api.telegram.org/bottoken/setWebhook")
        self.assertEqual(
            json.loads(calls[0][1]),
            {
                "url": "https://edge.example/webhooks/telegram/lead",
                "secret_token": "telegram-secret",
                "allowed_updates": ["message", "callback_query"],
                "drop_pending_updates": False,
            },
        )

    def test_outbound_rejects_wrong_core_secret_without_provider_call(self) -> None:
        service = EdgeService(config(), requester=lambda *_: self.fail("must not call provider"))
        self.assertEqual(service.invoke_telegram("getMe", b"{}", "wrong")[0], 401)


if __name__ == "__main__":
    unittest.main()
