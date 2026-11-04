"""Verify complete supplied ISO week labels against a pinned date cohort."""
from datetime import date
import week_core as c
import toolkit as t

FORMAT = 'outlands-iso-week-claims-v1'


def check(raw):
    value = t.decode(raw)
    t.fields(value, {'format', 'snapshot', 'cohort_sha256', 'claims'})
    t.require(value['format'] == FORMAT, 'FORMAT_INVALID')
    t.sha(value['cohort_sha256'])
    cohort, pin = c.analyze(value['snapshot'])
    t.require(pin == value['cohort_sha256'], 'COHORT_PIN_INVALID')
    claims = value['claims']
    t.require(type(claims) is list and len(claims) <= 512, 'CLAIM_LIMIT')
    selected = {}
    for row in claims:
        t.fields(row, {'id', 'iso_year', 'iso_week'})
        t.identifier(row['id'])
        t.require(row['id'] not in selected, 'CLAIM_DUPLICATE')
        t.integer(row['iso_year'], 2100, 1899)
        t.integer(row['iso_week'], 53, 1)
        try:
            date.fromisocalendar(row['iso_year'], row['iso_week'], 1)
        except ValueError:
            raise t.Rejected('CLAIM_WEEK_INVALID') from None
        selected[row['id']] = row
    expected = {row['id']: row['week'] for row in cohort['assignments']}
    findings = []
    for key in sorted(expected.keys() - selected.keys()):
        findings.append({'id': key, 'code': 'CLAIM_MISSING'})
    for key in sorted(selected.keys() - expected.keys()):
        findings.append({'id': key, 'code': 'CLAIM_UNEXPECTED'})
    for key in sorted(expected.keys() & selected.keys()):
        row = selected[key]
        actual = f"{row['iso_year']:04d}-W{row['iso_week']:02d}"
        if actual != expected[key]:
            findings.append({'id': key, 'code': 'WEEK_MISMATCH',
                             'expected_week': expected[key], 'claimed_week': actual})
    return {'format': FORMAT, 'status': 'REVIEW_REQUIRED' if findings else 'PASS',
            'input_sha256': t.digest(raw), 'cohort_sha256': pin,
            'claims_sha256': t.digest(t.encode([selected[x] for x in sorted(selected)])),
            'expected_rows': len(expected), 'claimed_rows': len(selected),
            'findings': findings, 'source_completeness_verified': False,
            'timezone_or_timestamp_inferred': False, 'target_changes_performed': False}


def main(argv=None):
    parser = t.Parser(description=__doc__)
    parser.add_argument('--input', required=True); parser.add_argument('--out')
    return t.run(parser, lambda args: check(t.read(args.input)), argv)


if __name__ == '__main__': raise SystemExit(main())
