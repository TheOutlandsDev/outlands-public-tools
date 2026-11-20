"""Preserved order identity tests using fictional order states."""

from pathlib import Path
import sys

import pytest

from order_alias import (
    AuthoritativeFlexCutoverError, LegacyOrderIdentityRecord, candidate_fingerprint,
    map_legacy_identity, run_identity_mapping_gate, semantic_fingerprint,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
from make_orders import NAMESPACES, order, record


def test_candidate_and_legacy_fingerprints_differ_deterministically():
    current = order()
    candidate = candidate_fingerprint(current, NAMESPACES.candidate_policy_revision)
    assert candidate != current.fingerprint(NAMESPACES.legacy_contract_version)
    assert candidate == candidate_fingerprint(current, NAMESPACES.candidate_policy_revision)


def test_semantic_fingerprint_excludes_only_namespace():
    current = order()
    assert semantic_fingerprint(current) not in {
        current.fingerprint(NAMESPACES.legacy_contract_version),
        candidate_fingerprint(current, NAMESPACES.candidate_policy_revision),
    }


def test_valid_legacy_record_maps_to_dual_alias():
    alias = map_legacy_identity(record(), NAMESPACES)
    assert alias.mapping_status == "VERIFIED_COMPATIBLE"
    assert alias.order_id == "DEMO-ORDER-0001"


def test_tampered_legacy_fingerprint_fails_closed():
    bad = LegacyOrderIdentityRecord(legacy_event_fingerprint="f" * 64, order=order())
    with pytest.raises(AuthoritativeFlexCutoverError, match="does not match"):
        map_legacy_identity(bad, NAMESPACES)


def test_replay_is_rejected_as_duplicate_alias():
    with pytest.raises(AuthoritativeFlexCutoverError, match="collision or duplicate"):
        run_identity_mapping_gate((record(), record()), NAMESPACES)


def test_two_orders_map_without_collision():
    result = run_identity_mapping_gate(
        (record(order_id_value := order()), record(order(order_id="DEMO-ORDER-0002"))), NAMESPACES,
    )
    assert order_id_value.order_id == "DEMO-ORDER-0001"
    assert result.mapped_records == result.distinct_semantic_identities == 2


def test_lifecycle_versions_have_distinct_identities():
    result = run_identity_mapping_gate(
        (record(order(version=1)), record(order(version=2, shipped=12))), NAMESPACES,
    )
    assert result.mapped_records == 2
    assert result.distinct_candidate_identities == 2


def test_same_order_version_conflicting_state_fails_closed():
    first = record(order())
    second_order = order(shipped=12)
    second = LegacyOrderIdentityRecord(
        legacy_event_fingerprint=second_order.fingerprint(NAMESPACES.legacy_contract_version), order=second_order
    )
    with pytest.raises(AuthoritativeFlexCutoverError, match="conflicting canonical"):
        run_identity_mapping_gate((first, second), NAMESPACES)


def test_policy_revision_changes_candidate_not_semantic_identity():
    current = order()
    assert candidate_fingerprint(current, "candidate-two") != candidate_fingerprint(
        current, NAMESPACES.candidate_policy_revision
    )
    assert semantic_fingerprint(current) == semantic_fingerprint(current)
