# Supported packet metadata and aggregate reports

Replay input is UTF-8 JSON with exactly schema `outlands-packet-metadata/1`
and a nonempty packets array. Maximum input is 1 MiB / 5,000 records; duplicate
keys, floats/nonfinite JSON numbers, unknown fields, unsupported controls,
excess nesting and over-limit collections are refused. All packet fields:

```json
{"source":"192.0.2.10","destination":"198.51.100.20","protocol":"TCP",
 "source_port":50000,"destination_port":443,"bytes":100}
```

Addresses must be IPv4 text. Protocol is TCP, UDP or OTHER. TCP/UDP ports are
integers 0–65,535, never booleans; OTHER requires null ports. Bytes is an integer
0–65,535, never a boolean. No payload, timestamp, interface, process or extra
annotation is accepted. A packet's source=destination counts once for tracked
host observation. Host counts are appearances in accepted packets, not unique
connections or complete capture coverage. Unsupported input stops replay;
there is no silent input repair or truncation.

## Local rules

Default retained ports are 23, 135, 139, 445, 6667 and 6668. The retained length
range is inclusive 40–2,000 bytes. A packet outside that range adds LENGTH_RULE;
a TCP/UDP endpoint in the port set adds PORT_RULE. A packet matching both still
counts once in packets_matching_local_rules. These configurable Python Rules
are simple review hints, not malware signatures, intrusion verdicts or threat
severity. OTX pulse observations never increment those local packet counters.

Scapy adaptation reads the first IPv4 layer and only its immediate TCP/UDP
payload when the fragment offset is zero and the outer protocol agrees. Quoted
ICMP/tunneled headers do not donate ports to the outer endpoints. No payload
or raw packet summary is returned by the metadata adapter. Different capture
link types can produce different observed lengths. IPv6 is outside scope.

## Aggregate report

Schema is outlands-network-monitor/1. Mode is demo/replay/live; outcome is
completed/cancelled/failed/packet_limit. Packet/byte/matching-packet totals,
invalid-record counts, bounded host count, untracked host observations and
omitted-rule-event counts are explicit. Events contain only packet ordinal,
protocol, bytes and local rule codes. At most the first 200 matching events
are retained; later matches are counted as omitted. Host tracking stops at
256 unique addresses; subsequent untracked endpoint appearances are counted.

addresses_included and reputation_requests_automatic are false in exports.
capture_incomplete is true on failure or forced cancellation without a complete
child result. The parent retains the last received aggregate and makes missing
final coverage review-required. A normal graceful cancellation is still labelled
cancelled. Kernel/backend drops and between-run traffic are not measured.

Export validates the supported aggregate field allowlist, types, counts, event
ordering and fixed interpretation before writing. Internal address-detail views
cannot be exported by this aggregate writer. Counts/rule structure can still
identify a session; this is not anonymization or an arbitrary metadata scrubber.

New filenames match `[A-Za-z0-9][A-Za-z0-9_. -]{0,114}\.json`, ignoring case,
with Windows reserved basenames refused on all platforms. Paths must be absolute
local routes with stable trusted existing parents; no links, traversal, UNC/ADS
or existing-file replacement. Partial new files can remain on write interruption.

## Reputation observation

Explicit OTX requests target one public unicast IPv4 address at the fixed HTTPS
service. Only a bounded, valid pulse_info.count integer (0–10,000,000) becomes
reported_pulse_count. Missing/malformed/duplicate count keys, HTTP errors,
oversized responses, request failure and worker timeout do not become zero.
Zero is a reported pulse count, not a clean verdict. Online results omit the
queried address and key, are not added to aggregate traffic exports, and do not
establish that the remote service is accurate, complete, current or authoritative.
