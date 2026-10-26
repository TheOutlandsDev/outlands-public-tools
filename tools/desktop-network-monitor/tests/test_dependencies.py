"""Actual installed packet decoding and system counters; generated traffic only."""
from pathlib import Path
import importlib.metadata
import json
import math
import multiprocessing as mp
import os
import queue
import sys
import threading
import time
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import monitor_core as core
import monitor_worker as worker


def child_fixture_capture(channel, stop, interface, seconds):
    if interface == 'fictional-ignore-stop':
        time.sleep(30)
    else:
        channel.put({'kind':'progress','report':core.demo().report()})
        while not stop.wait(.05):pass
        channel.put({'kind':'result','report':core.demo().report('cancelled')})


class DependencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from scapy.layers.inet import IP,TCP,UDP,ICMP
            cls.IP,cls.TCP,cls.UDP,cls.ICMP=IP,TCP,UDP,ICMP
        except ImportError:
            if os.environ.get('NETWORK_MONITOR_REQUIRE_DEPENDENCIES')=='1':raise
            raise unittest.SkipTest('Optional Scapy dependency unavailable')

    def decode(self,packet):return core.packet_record(packet,self.IP,self.TCP,self.UDP)

    def test_real_scapy_tcp_and_udp_decoding_is_offline(self):
        packet=self.IP(src='192.0.2.10',dst='198.51.100.20')/self.TCP(sport=50000,dport=23)
        result=self.decode(packet)
        self.assertEqual(result['protocol'],'TCP');self.assertEqual(result['destination_port'],23)
        udp=self.IP(src='192.0.2.10',dst='198.51.100.20')/self.UDP(sport=53,dport=50000)
        self.assertEqual(self.decode(udp)['protocol'],'UDP')

    def test_icmp_quoted_tcp_does_not_borrow_nested_ports(self):
        packet=(self.IP(src='192.0.2.10',dst='198.51.100.20')/self.ICMP(type=3)/
                self.IP(src='198.51.100.20',dst='203.0.113.30')/self.TCP(dport=23))
        result=self.decode(packet)
        self.assertEqual(result['protocol'],'OTHER');self.assertIsNone(result['destination_port'])

    def test_noninitial_fragment_has_no_transport_ports(self):
        packet=self.IP(src='192.0.2.10',dst='198.51.100.20',frag=2,proto=6)/self.TCP(dport=23)
        result=self.decode(packet)
        self.assertEqual(result['protocol'],'OTHER');self.assertIsNone(result['source_port'])

    def test_real_wire_roundtrip_uses_generated_bytes_only(self):
        packet=self.IP(src='192.0.2.10',dst='198.51.100.20')/self.TCP(dport=443)
        raw=bytes(packet)
        decoded=self.IP(raw)
        self.assertEqual(self.decode(decoded)['destination_port'],443)

    def test_required_dependency_versions_and_license_metadata_present(self):
        expected={'scapy':'2.8.0','psutil':'7.2.2','requests':'2.34.2'}
        for name,version in expected.items():
            self.assertEqual(importlib.metadata.version(name),version)
            metadata=importlib.metadata.metadata(name)
            self.assertTrue(metadata.get('License-Expression') or metadata.get('License') or metadata.get_all('Classifier'))


class IsolationTests(unittest.TestCase):
    def test_spawned_worker_can_be_cancelled_without_real_capture(self):
        stop=threading.Event();timer=threading.Timer(.4,stop.set);timer.start()
        try:
            with patch.object(worker,'capture_child',child_fixture_capture):
                result=worker.run_isolated('capture',('fictional-interface',30),stop)
        finally:timer.join()
        self.assertEqual(result['outcome'],'cancelled')

    def test_unresponsive_owned_worker_is_terminated_on_cancel(self):
        stop=threading.Event();timer=threading.Timer(.2,stop.set);timer.start();started=time.monotonic()
        try:
            with patch.object(worker,'capture_child',child_fixture_capture):
                result=worker.run_isolated('capture',('fictional-ignore-stop',30),stop)
        finally:timer.join()
        self.assertEqual(result['outcome'],'cancelled')
        self.assertTrue(result['capture_incomplete'])
        self.assertEqual(result['status'],'REVIEW_REQUIRED')
        self.assertLess(time.monotonic()-started,5)

    def test_actual_local_counter_snapshot_has_no_identity_fields(self):
        try:result=worker.system_snapshot()
        except core.MonitorError:
            if os.environ.get('NETWORK_MONITOR_REQUIRE_DEPENDENCIES')=='1':raise
            self.skipTest('Optional psutil unavailable')
        self.assertEqual(set(result),{'cpu_percent','memory_percent','cpu_sample_seconds',
                                     'network_bytes_received_total','network_bytes_sent_total'})
        self.assertTrue(0<=result['cpu_percent']<=100)
        self.assertTrue(0<=result['memory_percent']<=100)


if __name__=='__main__':unittest.main()
