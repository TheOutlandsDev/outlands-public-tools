from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from opskit.ports import parse_proc_net, parse_windows_netstat


SOURCE_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = SOURCE_ROOT / "examples"
LINUX_HEADER = "sl local_address rem_address st tx_queue rx_queue tr tm->when retrnsmt uid timeout inode"


def linux_table(*endpoints: str) -> str:
    rows = [
        f"{index}: {pair} 00000000:00000000 00:00000000 00000000 1000 0 {index + 1} 1"
        for index, pair in enumerate(endpoints)
    ]
    return "\n".join((LINUX_HEADER, *rows))


class SocketTableTests(unittest.TestCase):
    def test_windows_ipv6_and_udp_rows(self) -> None:
        rows = parse_windows_netstat((EXAMPLES / "windows-netstat.txt").read_text(encoding="utf-8"))
        self.assertEqual(
            [
                ("tcp", "192.0.2.5", 8080, "LISTENING"),
                ("tcp", "2001:db8::a", 8081, "LISTENING"),
                ("udp", "2001:db8::a", 5353, "BOUND"),
            ],
            [(row["protocol"], row["local_address"], row["local_port"], row["state"]) for row in rows],
        )

    def test_linux_ipv6_and_udp_rows(self) -> None:
        tcp6 = parse_proc_net((EXAMPLES / "linux-tcp6.txt").read_text(encoding="utf-8"), "tcp6")
        udp = parse_proc_net((EXAMPLES / "linux-udp.txt").read_text(encoding="utf-8"), "udp")
        udp6 = parse_proc_net(
            linux_table("B80D012000000000000000000A000000:14E9 00000000000000000000000000000000:0000 07"),
            "udp6",
        )
        self.assertEqual(
            [
                ("tcp", "2001:db8::a", 8080, "LISTEN"),
                ("udp", "192.0.2.5", 5353, "BOUND"),
                ("udp", "2001:db8::a", 5353, "BOUND"),
            ],
            [(row["protocol"], row["local_address"], row["local_port"], row["state"])
             for row in tcp6 + udp + udp6],
        )

    def test_malformed_windows_rows_do_not_stop_parsing(self) -> None:
        rows = parse_windows_netstat(
            """
TCP 192.0.2.5:8080 0.0.0.0:0 LISTENING 1040
TCP A-MISSING-PORT 0.0.0.0:0 LISTENING 1041
TCP 192.0.2.5:70000 0.0.0.0:0 LISTENING 1042
TCP not-an-address:8082 0.0.0.0:0 LISTENING 1043
TCP 192.0.2.5:8083 0.0.0.0:0 LISTENING invalid-pid
UDP 192.0.2.5:5353
UDP 192.0.2.5:5354 *:* 1044
"""
        )
        self.assertEqual([8080, 5354], [row["local_port"] for row in rows])

    def test_malformed_linux_rows_do_not_stop_parsing(self) -> None:
        rows = parse_proc_net(
            linux_table(
                "0100007F:1F90 00000000:0000 0A",
                "0100007F 00000000:0000 0A",
                "0100007F:1F91 00000000 0A",
                "050200C0:1Z92 00000000:0000 0A",
                "050200C0:10000 00000000:0000 0A",
                "ZZZZZZZZ:1F93 00000000:0000 0A",
                "050200C0:1F94 00000000:0000 0A",
            ),
            "tcp",
        )
        self.assertEqual([8080, 8084], [row["local_port"] for row in rows])

    def test_remote_fields_require_opt_in(self) -> None:
        windows = (EXAMPLES / "windows-netstat.txt").read_text(encoding="utf-8")
        linux = (EXAMPLES / "linux-tcp6.txt").read_text(encoding="utf-8")
        for rows in (parse_windows_netstat(windows), parse_proc_net(linux, "tcp6")):
            self.assertTrue(all(row["remote_address"] is None and row["remote_port"] is None for row in rows))
        windows_connection = parse_windows_netstat(windows, include_connections=True)[-1]
        linux_connection = parse_proc_net(linux, "tcp6", include_connections=True)[-1]
        self.assertEqual(("198.51.100.10", 443), (windows_connection["remote_address"], windows_connection["remote_port"]))
        self.assertEqual(("2001:db8::b", 443), (linux_connection["remote_address"], linux_connection["remote_port"]))
        self.assertEqual("ESTABLISHED", windows_connection["state"])
        self.assertEqual("ESTABLISHED", linux_connection["state"])

    def test_platform_pid_fields(self) -> None:
        windows = parse_windows_netstat((EXAMPLES / "windows-netstat.txt").read_text(encoding="utf-8"))
        linux = parse_proc_net((EXAMPLES / "linux-udp.txt").read_text(encoding="utf-8"), "udp")
        self.assertEqual([1040, 1041, 1042], [row["pid"] for row in windows])
        self.assertEqual([None], [row["pid"] for row in linux])

    def test_cli_reads_supplied_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            cases = (
                ("windows-netstat", "windows-netstat.txt", [8080, 8081, 5353]),
                ("linux-tcp6", "linux-tcp6.txt", [8080]),
                ("linux-udp", "linux-udp.txt", [5353]),
            )
            for table_format, example, expected_ports in cases:
                with self.subTest(table_format=table_format):
                    sample = folder / f"saved {example}"
                    capture = (EXAMPLES / example).read_bytes()
                    sample.write_bytes(capture)
                    command = [
                        sys.executable, "-B", "-m", "opskit", "ports",
                        "--format", table_format, "--input", str(sample),
                    ]
                    result = subprocess.run(
                        command, cwd=SOURCE_ROOT, capture_output=True, text=True, timeout=20,
                    )
                    self.assertEqual(0, result.returncode, result.stderr)
                    self.assertEqual("", result.stderr)
                    self.assertEqual(expected_ports, [row["local_port"] for row in json.loads(result.stdout)["rows"]])
                    self.assertEqual(capture, sample.read_bytes())

            missing = folder / "private missing capture.txt"
            result = subprocess.run(
                [
                    sys.executable, "-B", "-m", "opskit", "ports",
                    "--format", "windows-netstat", "--input", str(missing),
                ],
                cwd=SOURCE_ROOT, capture_output=True, text=True, timeout=20,
            )
            self.assertEqual(2, result.returncode)
            self.assertNotIn(str(missing), result.stderr)
            self.assertEqual("", result.stdout)


if __name__ == "__main__":
    unittest.main()
