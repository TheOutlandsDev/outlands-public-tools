from datetime import UTC, datetime

import pytest

from production_planning.backend_verification import (
    BackendVerificationError,
    VerificationSpec,
    observation,
    run_backend_verification,
)


NOW = datetime(2000, 9, 1, 14, 30, tzinfo=UTC)


def spec(check_id: str, category: str = "DATABASE") -> VerificationSpec:
    return VerificationSpec(
        check_id=check_id,
        category=category,
        label=check_id.replace(".", " ").title(),
    )


def test_all_pass_report_is_deterministic_and_read_only() -> None:
    checks = (
        (spec("demo.inventory"), lambda: observation("PASS", "Available.", reachable=True)),
        (spec("demo.orders"), lambda: observation("PASS", "Available.", reachable=True)),
    )

    first = run_backend_verification(
        app_version="0.1.0-demo", checks=checks, now=lambda: NOW
    )
    second = run_backend_verification(
        app_version="0.1.0-demo", checks=checks, now=lambda: NOW
    )

    assert first == second
    assert first.overall_status == "PASS"
    assert first.check_count == 2
    assert first.passed_count == 2
    assert first.warning_count == 0
    assert first.failed_count == 0
    assert first.database_writes is False
    assert first.production_modified is False
    assert len(first.result_sha256) == 64


def test_warning_does_not_hide_a_healthy_runtime() -> None:
    report = run_backend_verification(
        app_version="0.1.0-demo",
        checks=(
            (
                spec("demo.review", "POLICY"),
                lambda: observation(
                    "WARNING",
                    "Business review remains open; integrity passed.",
                    gate="BLOCKED",
                ),
            ),
        ),
        now=lambda: NOW,
    )

    assert report.overall_status == "PASS_WITH_WARNINGS"
    assert report.warning_count == 1
    assert report.failed_count == 0


def test_unexpected_verifier_error_is_sanitized_and_fails_closed() -> None:
    def broken_verifier():
        raise RuntimeError("secret-bearing internal text")

    report = run_backend_verification(
        app_version="0.1.0-demo",
        checks=((spec("demo.inventory"), broken_verifier),),
        now=lambda: NOW,
    )

    assert report.overall_status == "FAIL"
    assert report.failed_count == 1
    assert report.checks[0].metrics == {"error_class": "RuntimeError"}
    assert "secret-bearing" not in report.model_dump_json()


def test_registry_rejects_duplicate_or_invalid_identifiers() -> None:
    duplicate = spec("database.connection")
    with pytest.raises(BackendVerificationError, match="unique"):
        run_backend_verification(
            app_version="0.1.0-demo",
            checks=(
                (duplicate, lambda: observation("PASS", "Available.")),
                (duplicate, lambda: observation("PASS", "Available.")),
            ),
            now=lambda: NOW,
        )

    with pytest.raises(ValueError):
        spec("Database Connection")


def test_metrics_are_bounded_and_normalized() -> None:
    with pytest.raises(ValueError):
        observation("PASS", "Available.", **{"Not Normalized": True})

    with pytest.raises(ValueError):
        observation(
            "PASS",
            "Available.",
            **{f"metric-{index}": index for index in range(17)},
        )
