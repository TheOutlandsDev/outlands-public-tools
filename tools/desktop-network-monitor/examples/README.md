# Fictional examples

`python -B monitor.py demo` uses only invented documentation-range IPv4 records
and does not import Scapy/psutil/Requests/Tk. It reports three accepted IPv4
packets and two packets matching local review rules: one port match and one
length match. No reputation lookup runs and exported events contain no address.

Use the generator and replay commands in [README](../README.md) with an existing
external private workspace. A new directory contains packets.json in the exact
supported replay schema. It refuses an existing destination. Replay leaves the
input unchanged; --output creates a new aggregate JSON file without replacing
anything. Generated examples/outputs belong outside the checkout.

The GUI's fictional demo runs the same model and displays FICTIONAL DEMO. It is
distinct from the explicit System snapshot, live capture and OTX actions.
Test keys and interface labels are clearly invented and never sent to a service.
