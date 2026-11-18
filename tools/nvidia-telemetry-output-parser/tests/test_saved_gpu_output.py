from __future__ import annotations

from sentinel_monitor.collectors.nvidia import parse_gpu_output


def test_parse_saved_csv_skips_bad_rows_and_keeps_quoted_names() -> None:
    csv_output = (
        "0,GPU-DEMO-01,short row\r\n"
        "bad,GPU-DEMO-02,Invalid index,42,10,2,100,400,50.5,250,28,P8,324,3304,"
        "DEMO-02,00000000:A2:00.0,999.01,TCC,TCC\r\n"
        '2,GPU-DEMO-03,"Example GPU, Series A",42,10,2,100,400,50.5,250,28,P8,324,3304,'
        "DEMO-03,00000000:A3:00.0,999.01,TCC,TCC\r\n"
    )

    readings, status = parse_gpu_output(csv_output)

    assert len(readings) == 1
    assert readings[0].index == 2
    assert readings[0].name == "Example GPU, Series A"
    assert readings[0].memory_percent == 25.0
    assert status == "Active: 1 NVIDIA GPU(s) | driver 999.01 | TCC"


def test_parse_saved_csv_preserves_missing_numeric_values() -> None:
    csv_output = (
        "0,GPU-DEMO-01,Example GPU,N/A,[n/a],Not Supported,,0,unknown,250,28,P8,324,3304,"
        "DEMO-01,00000000:A1:00.0,999.01,TCC,TCC\n"
    )

    (reading,), _ = parse_gpu_output(csv_output)

    assert reading.temperature_c is None
    assert reading.utilization_percent is None
    assert reading.memory_utilization_percent is None
    assert reading.memory_used_mb is None
    assert reading.memory_total_mb == 0.0
    assert reading.power_draw_w is None
    assert reading.power_limit_w == 250.0
    assert reading.memory_percent is None


def test_parse_saved_output_matches_replays_by_bus() -> None:
    csv_output = (
        "0,GPU-DEMO-01,Example GPU A,42,10,2,100,400,50.5,250,28,P8,324,3304,"
        "DEMO-01,00000000:a1:00.0,999.01,TCC,TCC\n"
        "1,GPU-DEMO-02,Example GPU B,43,11,3,110,400,51.5,250,29,P8,324,3304,"
        "DEMO-02,00000000:A2:00.0,999.01,WDDM,WDDM\n"
        "2,GPU-DEMO-03,Example GPU C,44,12,4,120,400,52.5,250,30,P8,324,3304,"
        "DEMO-03,00000000:A3:00.0,999.01,WDDM,WDDM\n"
    )
    replay_output = (
        "Replays Since Reset : 99\n"
        "Bus Id : 00000000:a2:00.0\n"
        "Replays Since Reset : 7\n"
        "Bus Id : 00000000:A1:00.0\n"
        "Replays Since Reset : 0\n"
        "Bus Id : 00000000:A4:00.0\n"
        "Replays Since Reset : 1024\n"
    )

    readings, status = parse_gpu_output(csv_output, replay_output)

    assert [reading.pcie_replays_since_reset for reading in readings] == [0, 7, None]
    assert status == "Active: 3 NVIDIA GPU(s) | driver 999.01 | TCC/WDDM | PCIe replay GPU 0=0 GPU 1=7"
