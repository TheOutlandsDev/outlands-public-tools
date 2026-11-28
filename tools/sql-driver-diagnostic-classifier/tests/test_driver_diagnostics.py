from __future__ import annotations

import json
import unittest

from sql_driver_diagnostic_classifier import safe_error


class DriverError(Exception):
    pass


class ConnectionDiagnosticTests(unittest.TestCase):
    def test_driver_diagnostics_do_not_echo_credentials(self) -> None:
        error = DriverError("28000", "Login failed for secret-login; PWD=secret-password")
        result = safe_error(error)
        self.assertEqual(result["category"], "authentication")
        self.assertEqual(result["sqlstate"], "28000")
        self.assertNotIn("secret-", json.dumps(result))
        result = safe_error(DriverError("not-a-state-secret", "certificate mismatch secret-login"))
        self.assertEqual(result["sqlstate"], "UNKNOWN")
        self.assertEqual(result["category"], "tls_validation")
        self.assertNotIn("secret", json.dumps(result))

    def test_tls_diagnostics_classify_allowlisted_causes_without_raw_text(self) -> None:
        examples = (
            ("The target principal name is incorrect. (-2146893022)", "certificate_hostname_mismatch"),
            ("The certificate chain was issued by an authority that is not trusted. (-2146893019)", "untrusted_certificate_chain"),
            ("The received certificate has expired. (-2146893016)", "certificate_expired"),
            ("The client and server cannot communicate because they do not possess a common algorithm. (-2146893007)", "protocol_or_handshake"),
            ("An unexpected TLS diagnostic occurred.", "unknown_tls_error"),
        )
        for detail, expected in examples:
            with self.subTest(reason=expected):
                result = safe_error(DriverError(
                    "08001", "[Microsoft][ODBC Driver 18 for SQL Server]SSL Provider: "
                    + detail + " server=private-host.invalid UID=secret-login PWD=secret-password",
                ))
                self.assertEqual(result["category"], "tls_validation")
                self.assertEqual(result["reason"], expected)
                self.assertEqual(result["sqlstate"], "08001")
                serialized = json.dumps(result)
                for private in ("private-host", "secret-login", "secret-password", "ODBC", detail):
                    self.assertNotIn(private, serialized)
                self.assertIn("Encryption remains enabled", result["guidance"])

    def test_tls_native_codes_support_localized_messages(self) -> None:
        codes = {
            "certificate_hostname_mismatch": ("0x80090322", "-2146893022", "2148074274"),
            "untrusted_certificate_chain": ("0x80090325", "-2146893019", "2148074277"),
            "certificate_expired": ("0x80090328", "-2146893016", "2148074280"),
            "protocol_or_handshake": ("0x80090302", "0x80090326", "0x80090331", "-2146893007"),
        }
        for expected, native_codes in codes.items():
            for code in native_codes:
                with self.subTest(code=code):
                    result = safe_error(DriverError("08001", f"SSL Provider: localized text ({code})"))
                    self.assertEqual(result["reason"], expected)
                    self.assertNotIn(code, json.dumps(result))

    def test_tls_messages_without_native_codes_and_unknown_fallback(self) -> None:
        examples = (
            ("SSL routines::certificate verify failed:subject name does not match host name", "certificate_hostname_mismatch"),
            ("SSL routines::certificate verify failed: unable to get local issuer certificate", "untrusted_certificate_chain"),
            ("SSL routines::certificate verify failed: self-signed certificate", "untrusted_certificate_chain"),
            ("SSL routines::certificate verify failed: self signed certificate in certificate chain", "untrusted_certificate_chain"),
            ("SSL routines::certificate verify failed: certificate has expired", "certificate_expired"),
            ("TLS handshake failed", "protocol_or_handshake"),
            ("SSL Provider: SEC_E_ALGORITHM_MISMATCH", "protocol_or_handshake"),
            ("SSL Provider: SEC_E_CERT_UNKNOWN", "unknown_tls_error"),
            ("SSL Provider: invalid code token x0x80090322z", "unknown_tls_error"),
        )
        for message, expected in examples:
            with self.subTest(message=message):
                self.assertEqual(safe_error(DriverError("08001", message))["reason"], expected)

    def test_windows_security_context_keeps_priority_over_tls_wording(self) -> None:
        result = safe_error(DriverError("08001", "SSL Provider: No credentials are available in the security package."))
        self.assertEqual(result["category"], "windows_security_context")
        self.assertNotIn("reason", result)
