from __future__ import annotations

import unittest

from opskit.ports import parse_proc_net, parse_windows_netstat


class PortParserTests(unittest.TestCase):
    def test_windows_netstat_listeners_only(self) -> None:
        sample = """
          TCP    0.0.0.0:135          0.0.0.0:0          LISTENING       1040
          TCP    192.0.2.5:50000       198.51.100.10:443        ESTABLISHED     2222
          TCP    [::]:445             [::]:0             LISTENING       4
          UDP    0.0.0.0:5353         *:*                                1234
        """
        rows = parse_windows_netstat(sample)
        self.assertEqual(3, len(rows))
        self.assertEqual([135, 445, 5353], [row["local_port"] for row in rows])
        self.assertEqual("BOUND", rows[-1]["state"])

    def test_windows_netstat_can_include_connections(self) -> None:
        sample = (
            "TCP    192.0.2.5:50000    198.51.100.10:443    ESTABLISHED    2222"
        )
        rows = parse_windows_netstat(sample, include_connections=True)
        self.assertEqual(1, len(rows))
        self.assertEqual("198.51.100.10", rows[0]["remote_address"])
        self.assertEqual(443, rows[0]["remote_port"])

    def test_proc_net_tcp_listener(self) -> None:
        sample = """  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode
   0: 0100007F:1F90 00000000:0000 0A 00000000:00000000 00:00000000 00000000  1000 0 12345 1
   1: 050200C0:C350 0A6433C6:01BB 01 00000000:00000000 00:00000000 00000000  1000 0 12346 1
"""
        rows = parse_proc_net(sample, "tcp")
        self.assertEqual(1, len(rows))
        self.assertEqual("127.0.0.1", rows[0]["local_address"])
        self.assertEqual(8080, rows[0]["local_port"])


if __name__ == "__main__":
    unittest.main()
