"""Classify one saved ODBC diagnostic and omit its raw message."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from stat import S_ISREG
import sys


MAX_INPUT_BYTES = 65_536


def safe_error(error: Exception) -> dict[str, str]:
    """Return an allowlisted diagnostic; driver text can contain login details."""
    raw_state = error.args[0] if error.args else ""
    sqlstate = raw_state if isinstance(raw_state, str) and re.fullmatch(r"[A-Z0-9]{5}", raw_state) else "UNKNOWN"
    message = str(error).casefold()
    if "no credentials are available" in message:
        category = "windows_security_context"
        guidance = "Use your normal Windows terminal. The recorded security context could not initialize the connection."
    elif any(word in message for word in ("certificate", "ssl provider", "encryption", "tls")):
        category = "tls_validation"
        # Native Schannel codes can survive localization of the driver text.
        # Keep native codes and raw messages internal. Return an advisory label.
        native_codes = {
            (int(token, 16) if token.startswith("0x") else int(token)) & 0xFFFFFFFF
            for token in re.findall(
                r"(?<![a-z0-9_])(?:0x[0-9a-f]{8}|-?\d{10})(?![a-z0-9_])", message
            )
        }
        if 0x80090322 in native_codes or any(phrase in message for phrase in (
            "target principal name is incorrect", "sec_e_wrong_principal",
            "subject name does not match host name", "hostname mismatch",
            "host name mismatch", "certificate name mismatch",
        )):
            reason = "certificate_hostname_mismatch"
            guidance = "Verify the expected server hostname with the database administrator and use the verified DNS name in your client."
        elif 0x80090325 in native_codes or any(phrase in message for phrase in (
            "authority that is not trusted", "sec_e_untrusted_root",
            "unable to get local issuer certificate", "self-signed certificate",
            "self signed certificate", "untrusted certificate chain",
        )):
            reason = "untrusted_certificate_chain"
            guidance = "Have the database or workstation administrator verify the server certificate chain and provision its approved issuing CA certificates through the normal trust process."
        elif 0x80090328 in native_codes or any(phrase in message for phrase in (
            "certificate has expired", "certificate expired", "sec_e_cert_expired",
        )):
            reason = "certificate_expired"
            guidance = "Have the database administrator verify certificate validity and renewal, and confirm that the workstation clock is correct."
        elif native_codes & {0x80090302, 0x80090326, 0x80090331} or any(phrase in message for phrase in (
            "handshake failure", "handshake failed", "unsupported protocol",
            "protocol version", "no protocols available", "no shared cipher",
            "do not possess a common algorithm", "sec_e_algorithm_mismatch",
            "sec_e_illegal_message", "sec_e_unsupported_function",
        )):
            reason = "protocol_or_handshake"
            guidance = "Have the database or workstation administrator check supported TLS protocols, cipher compatibility, and server handshake logs."
        else:
            reason = "unknown_tls_error"
            guidance = "Use the verified server hostname and trusted certificate chain. The saved diagnostic did not identify a specific TLS cause."
        guidance += " Encryption remains enabled in the recommended configuration. Review the client transport settings."
        return {"sqlstate": sqlstate, "category": category, "reason": reason, "guidance": guidance}
    elif sqlstate == "28000" or "login failed" in message:
        category = "authentication"
        guidance = "Verify the approved SQL login locally."
    elif sqlstate.startswith("08") or "timeout" in message:
        category = "connectivity"
        guidance = "Verify the TCP endpoint, port, network access, and server availability."
    elif sqlstate in {"IM002", "IM003"}:
        category = "driver"
        guidance = "Check that ODBC Driver 18 for SQL Server is available to this Python installation."
    else:
        category = "database_error"
        guidance = "Inspect the original error in your local SQL client."
    return {"sqlstate": sqlstate, "category": category, "guidance": guidance}


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(_value):
    raise ValueError("Invalid JSON number")


def _read_diagnostic(path: Path) -> Exception:
    try:
        if not S_ISREG(path.stat().st_mode):
            raise OSError
        with path.open("rb") as stream:
            raw = stream.read(MAX_INPUT_BYTES + 1)
    except OSError:
        raise ValueError("Input must be a readable regular file") from None
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError("Input exceeds 65,536 bytes")
    try:
        data = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_unique_keys, parse_constant=_reject_constant)
    except (ValueError, RecursionError):
        raise ValueError("Input must be valid UTF-8 JSON with unique keys") from None
    if not isinstance(data, dict) or "message" not in data or data.keys() - {"sqlstate", "message"}:
        raise ValueError("Input must be an object with message and optional sqlstate")
    message = data["message"]
    state = data.get("sqlstate")
    if not isinstance(message, str):
        raise ValueError("Message must be text")
    if state is not None and not isinstance(state, str):
        raise ValueError("SQLSTATE must be text or null")
    return Exception(state, message)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Saved diagnostic JSON")
    args = parser.parse_args()
    try:
        diagnostic = _read_diagnostic(args.input)
    except ValueError as error:
        sys.stderr.write(f"{error}\n")
        return 2
    print(json.dumps(safe_error(diagnostic), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
