import json
import socket
import unittest
from unittest import mock

import edge_app
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


class _FakeResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, _limit):
        return b'{"ok":true}'


class EdgeTransportTests(unittest.TestCase):
    def test_telegram_api_uses_ipv6_opener_but_core_keeps_default_transport(self) -> None:
        with (
            mock.patch.object(edge_app._TELEGRAM_IPV6_OPENER, "open", return_value=_FakeResponse()) as ipv6_open,
            mock.patch("edge_app.urllib.request.urlopen", return_value=_FakeResponse()) as default_open,
        ):
            self.assertEqual(
                edge_app._request("https://api.telegram.org/bottoken/getMe", b"{}", {}),
                (200, b'{"ok":true}'),
            )
            ipv6_open.assert_called_once()
            default_open.assert_not_called()

            ipv6_open.reset_mock()
            self.assertEqual(
                edge_app._request("https://core.example/webhooks/telegram/lead", b"{}", {}),
                (200, b'{"ok":true}'),
            )
            default_open.assert_called_once()
            ipv6_open.assert_not_called()

    def test_ipv6_connection_resolves_only_ipv6_addresses(self) -> None:
        fake_socket = mock.Mock()
        address = ("2001:db8::1", 443, 0, 0)
        with (
            mock.patch(
                "edge_app.socket.getaddrinfo",
                return_value=[(socket.AF_INET6, socket.SOCK_STREAM, 6, "", address)],
            ) as getaddrinfo,
            mock.patch("edge_app.socket.socket", return_value=fake_socket),
        ):
            result = edge_app._create_ipv6_connection(("api.telegram.org", 443), timeout=5)

        self.assertIs(result, fake_socket)
        getaddrinfo.assert_called_once_with(
            "api.telegram.org",
            443,
            socket.AF_INET6,
            socket.SOCK_STREAM,
        )
        fake_socket.settimeout.assert_called_once_with(5)
        fake_socket.connect.assert_called_once_with(address)


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

    def test_menu_operations_are_fixed_to_one_command_and_commands_button(self) -> None:
        calls = []

        def requester(url, body, headers):
            calls.append((url, json.loads(body)))
            if url.endswith("/getMyCommands"):
                result = [{"command": "menu", "description": "Открыть доступные действия"}]
            elif url.endswith("/getChatMenuButton"):
                result = {"type": "commands"}
            else:
                result = True
            return 200, json.dumps({"ok": True, "result": result}).encode()

        service = EdgeService(config(), requester=requester)
        fixed = [
            ("setMyCommands", {"commands": [{"command": "menu", "description": "Открыть доступные действия"}]}),
            ("setChatMenuButton", {"menu_button": {"type": "commands"}}),
            ("getMyCommands", {}),
            ("getChatMenuButton", {}),
        ]
        for operation, payload in fixed:
            self.assertEqual(service.invoke_telegram(operation, json.dumps(payload).encode(), "core-secret")[0], 200)
        self.assertEqual([call[0].rsplit("/", 1)[1] for call in calls], [row[0] for row in fixed])

    def test_menu_operations_reject_any_other_payload_without_provider_call(self) -> None:
        service = EdgeService(config(), requester=lambda *_: self.fail("must not call provider"))
        status, result = service.invoke_telegram(
            "setMyCommands", b'{"commands":[{"command":"other","description":"other"}]}', "core-secret"
        )
        self.assertEqual((status, result), (400, {"ok": False, "error": "invalid_menu_request"}))


if __name__ == "__main__":
    unittest.main()
