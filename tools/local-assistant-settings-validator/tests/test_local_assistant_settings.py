import unittest

from local_assistant_settings import Settings, validate_local_url


class ConfigTests(unittest.TestCase):
    def test_only_loopback_ollama_is_allowed(self) -> None:
        self.assertEqual(
            validate_local_url("http://127.0.0.1:11434"),
            "http://127.0.0.1:11434",
        )
        with self.assertRaises(ValueError):
            validate_local_url("https://example.com")
        with self.assertRaises(ValueError):
            validate_local_url("http://192.0.2.20:11434")

    def test_settings_are_bounded(self) -> None:
        settings = Settings(
            temperature=9,
            context_window=1,
            max_tool_rounds=999,
        ).validate()
        self.assertEqual(settings.temperature, 2.0)
        self.assertEqual(settings.context_window, 4096)
        self.assertEqual(settings.max_tool_rounds, 30)
        named = Settings(owner_name="  Example Operator  ").validate()
        self.assertEqual(named.owner_name, "Example Operator")
