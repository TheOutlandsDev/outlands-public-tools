"""Original MIT client tests against disposable loopback HTTP, never a model."""
import json
import os
import unittest
from unittest.mock import patch

from steven import ChatError, OllamaClient, canonical_endpoint, safe_text, validate_model
from http_fixture import chat_reply, http_fixture


class EndpointTests(unittest.TestCase):
    def test_loopback_ipv4(self):
        self.assertEqual(canonical_endpoint("http://127.0.0.1:11434"), "http://127.0.0.1:11434")

    def test_localhost_is_canonicalized_without_dns(self):
        self.assertEqual(canonical_endpoint("http://localhost:12345"), "http://127.0.0.1:12345")

    def test_ipv6_loopback(self):
        self.assertEqual(canonical_endpoint("http://[::1]:11434"), "http://[::1]:11434")

    def test_remote_and_ambiguous_addresses_refused(self):
        for value in ["http://example.invalid:11434", "http://192.168.1.2:11434", "http://0.0.0.0:11434",
                      "http://127.1:11434", "http://2130706433:11434", "http://127.0.0.2:11434",
                      "http://127.0.0.1.example.invalid:11434", "http://[::ffff:127.0.0.1]:11434"]:
            with self.subTest(value=value), self.assertRaises(ChatError):
                canonical_endpoint(value)

    def test_non_http_schemes_refused(self):
        for value in ["https://127.0.0.1:11434", "file:///tmp/server", "ftp://127.0.0.1", "127.0.0.1:11434"]:
            with self.subTest(value=value), self.assertRaises(ChatError):
                canonical_endpoint(value)

    def test_endpoint_authority_and_path_guards(self):
        for value in ["http://user:pass@127.0.0.1:11434", "http://127.0.0.1:11434/api",
                      "http://127.0.0.1:11434?x=1", "http://127.0.0.1:11434#x",
                      "http://127.0.0.1:0", "http://127.0.0.1:65536", "http://127.0.0.1:noport",
                      " http://127.0.0.1:11434", "http://127.0.0.1:11434\n", "http://127.0.0.1:11434\t"]:
            with self.subTest(value=repr(value)), self.assertRaises(ChatError):
                canonical_endpoint(value)

    def test_valid_model_names(self):
        for value in ["fixture:tiny", "fictional/model:1.0", "model-name_v2"]:
            self.assertEqual(validate_model(value), value)

    def test_invalid_and_obvious_cloud_names_refused(self):
        for value in ["", " ", "model\n", "../private", "a" * 300, "model:cloud", "model-cloud", "model\x1b[31m", None]:
            with self.subTest(value=repr(value)), self.assertRaises(ChatError):
                validate_model(value)

    def test_timeout_validation(self):
        for value in [0, -1, 301, float("nan"), float("inf"), True, "1"]:
            with self.subTest(value=repr(value)), self.assertRaises(ChatError):
                OllamaClient(timeout=value)

    def test_output_limit_validation(self):
        for value in [0, -1, 4097, 1.5, True, "4"]:
            with self.subTest(value=repr(value)), self.assertRaises(ChatError):
                OllamaClient(max_output_tokens=value)

    def test_terminal_controls_are_inert(self):
        result = safe_text("hello\x1b[31mred\x1b[0m\rRESET\x00\x08\u202eevil\u2066text\u2069\nnext\titem")
        for control in ["\x1b", "\r", "\x00", "\x08", "\u202e", "\u2066", "\u2069"]:
            self.assertNotIn(control, result)
        self.assertIn("hello", result)
        self.assertIn("next", result)


class HttpTests(unittest.TestCase):
    def test_chat_request_uses_non_streaming_api_and_explicit_limit(self):
        messages = [{"role": "user", "content": "Fictional question"}]
        with http_fixture([chat_reply("Fictional answer")]) as (endpoint, requests):
            answer = OllamaClient(endpoint, max_output_tokens=37).chat("fixture:tiny", messages)
        self.assertEqual(answer, "Fictional answer")
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0]["method"], "POST")
        self.assertEqual(requests[0]["path"], "/api/chat")
        body = json.loads(requests[0]["body"])
        self.assertEqual(body["model"], "fixture:tiny")
        self.assertEqual(body["messages"], messages)
        self.assertIs(body["stream"], False)
        self.assertEqual(body["options"]["num_predict"], 37)
        self.assertNotIn("tools", body)
        self.assertNotIn("Authorization", requests[0]["headers"])

    def test_unicode_round_trip(self):
        with http_fixture([chat_reply("Fictional café 🧪")]) as (endpoint, requests):
            self.assertEqual(OllamaClient(endpoint).chat("fixture:tiny", [{"role": "user", "content": "café"}]), "Fictional café 🧪")
        self.assertEqual(json.loads(requests[0]["body"])["messages"][0]["content"], "café")

    def test_models_uses_tags_get(self):
        with http_fixture([{"body": {"models": [{"name": "fixture:tiny", "size": 123}, {"name": "other:small"}]}}]) as (endpoint, requests):
            result = OllamaClient(endpoint).models()
        self.assertEqual(result, ["fixture:tiny", "other:small"])
        self.assertEqual((requests[0]["method"], requests[0]["path"], requests[0]["body"]), ("GET", "/api/tags", b""))

    def test_model_list_shape_guard(self):
        for body in [[], {}, {"models": None}, {"models": ["plain-name"]}, {"models": [{"name": 4}]},
                     {"models": [{"name": "fixture:tiny"}] * 129}]:
            with self.subTest(body=repr(body)[:80]), http_fixture([{"body": body}]) as (endpoint, _), self.assertRaises(ChatError):
                OllamaClient(endpoint).models()

    def test_empty_model_list_is_valid(self):
        with http_fixture([{"body": {"models": []}}]) as (endpoint, _):
            self.assertEqual(OllamaClient(endpoint).models(), [])

    def test_cloud_labelled_models_are_filtered_from_mixed_list(self):
        body = {"models": [{"name": "fixture:tiny"}, {"name": "remote:cloud"}, {"name": "other-cloud"}]}
        with http_fixture([{"body": body}]) as (endpoint, _):
            self.assertEqual(OllamaClient(endpoint).models(), ["fixture:tiny"])

    def test_proxy_environment_does_not_route_local_request(self):
        env = {"http_proxy": "http://127.0.0.1:1", "HTTP_PROXY": "http://127.0.0.1:1",
               "ALL_PROXY": "http://127.0.0.1:1", "NO_PROXY": "", "no_proxy": ""}
        with patch.dict(os.environ, env), http_fixture([chat_reply()]) as (endpoint, requests):
            self.assertTrue(OllamaClient(endpoint).chat("fixture:tiny", [{"role": "user", "content": "fixture"}]))
        self.assertEqual(len(requests), 1)

    def test_redirect_is_not_followed(self):
        with http_fixture([chat_reply("Must never be reached")]) as (target, target_requests):
            with http_fixture([{"status": 302, "headers": {"Location": target + "/api/chat"}}]) as (endpoint, requests):
                with self.assertRaises(ChatError):
                    OllamaClient(endpoint).chat("fixture:tiny", [{"role": "user", "content": "fixture"}])
            self.assertEqual(len(requests), 1)
            self.assertEqual(target_requests, [])

    def test_http_error_does_not_expose_server_body(self):
        marker = "SECRET-FIXTURE-DO-NOT-PRINT"
        with http_fixture([{"status": 503, "body": marker}]) as (endpoint, _):
            with self.assertRaises(ChatError) as caught:
                OllamaClient(endpoint).chat("fixture:tiny", [{"role": "user", "content": "fixture"}])
        self.assertNotIn(marker, str(caught.exception))

    def test_malformed_json_is_rejected(self):
        with http_fixture([{"body": b"{not json"}]) as (endpoint, _), self.assertRaises(ChatError):
            OllamaClient(endpoint).chat("fixture:tiny", [{"role": "user", "content": "fixture"}])

    def test_duplicate_json_keys_are_rejected(self):
        with http_fixture([{"body": b'{"done":true,"done":true,"message":{"role":"assistant","content":"duplicate"}}'}]) as (endpoint, _), self.assertRaises(ChatError):
            OllamaClient(endpoint).chat("fixture:tiny", [{"role": "user", "content": "fixture"}])

    def test_nonfinite_json_is_rejected(self):
        with http_fixture([{"body": b'{"done":true,"message":{"role":"assistant","content":"x"},"duration":NaN}'}]) as (endpoint, _), self.assertRaises(ChatError):
            OllamaClient(endpoint).chat("fixture:tiny", [{"role": "user", "content": "fixture"}])

    def test_invalid_utf8_is_rejected(self):
        with http_fixture([{"body": b"\xff\xfe"}]) as (endpoint, _), self.assertRaises(ChatError):
            OllamaClient(endpoint).chat("fixture:tiny", [{"role": "user", "content": "fixture"}])

    def test_truncated_declared_body_becomes_safe_error(self):
        body = json.dumps(chat_reply()["body"]).encode("utf-8")
        with http_fixture([{"body": body, "declared_length": len(body) + 50}]) as (endpoint, _), self.assertRaises(ChatError):
            OllamaClient(endpoint).chat("fixture:tiny", [{"role": "user", "content": "fixture"}])

    def test_malformed_http_status_becomes_safe_error(self):
        with http_fixture([{"raw_http": b"Not-an-HTTP-status\r\n\r\n"}]) as (endpoint, _), self.assertRaises(ChatError):
            OllamaClient(endpoint).chat("fixture:tiny", [{"role": "user", "content": "fixture"}])

    def test_oversized_response_with_declared_length_is_rejected(self):
        with http_fixture([{"body": b"x" * (1024 * 1024 + 1)}]) as (endpoint, _), self.assertRaises(ChatError):
            OllamaClient(endpoint).chat("fixture:tiny", [{"role": "user", "content": "fixture"}])

    def test_oversized_response_without_declared_length_is_rejected(self):
        with http_fixture([{"body": b"x" * (1024 * 1024 + 1), "length": False}]) as (endpoint, _), self.assertRaises(ChatError):
            OllamaClient(endpoint).chat("fixture:tiny", [{"role": "user", "content": "fixture"}])

    def test_response_shape_and_completion_are_required(self):
        bodies = [[], {}, {"done": False, "message": {"role": "assistant", "content": "x"}},
                  {"done": True, "message": {"role": "user", "content": "x"}},
                  {"done": True, "message": {"role": "assistant", "content": ""}},
                  {"done": True, "message": {"role": "assistant", "content": "   "}},
                  {"done": True, "message": {"role": "assistant", "content": 4}},
                  {"done": True, "message": {"role": "assistant", "content": "x", "tool_calls": [{"function": {"name": "shell"}}]}},
                  {"done": True, "message": {"role": "assistant", "content": "x"}, "error": "private fixture"}]
        for body in bodies:
            with self.subTest(body=body), http_fixture([{"body": body}]) as (endpoint, _), self.assertRaises(ChatError):
                OllamaClient(endpoint).chat("fixture:tiny", [{"role": "user", "content": "fixture"}])

    def test_timeout_becomes_safe_error(self):
        with http_fixture([{**chat_reply(), "delay": 1.3}]) as (endpoint, _), self.assertRaises(ChatError):
            OllamaClient(endpoint, timeout=1).chat("fixture:tiny", [{"role": "user", "content": "fixture"}])

    def test_client_refuses_invalid_request_before_contact(self):
        with http_fixture([chat_reply()]) as (endpoint, requests):
            client = OllamaClient(endpoint)
            with self.assertRaises(ChatError):
                client.chat("model:cloud", [{"role": "user", "content": "fixture"}])
            self.assertEqual(requests, [])


if __name__ == "__main__":
    unittest.main()
