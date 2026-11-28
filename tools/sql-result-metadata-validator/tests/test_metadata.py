from __future__ import annotations

import unittest

import sql_result_metadata_validator as helper

COLUMNS = ("Item", "Instance", "RecordedAt", "RecordedBy", "Product", "Attribute", "Sample", "Value")


def validate(rows):
    return helper.validate_metadata(rows, expected_columns=COLUMNS)


def metadata(sql_type="datetime2(6)", scale=6):
    rows = []
    for index, name in enumerate(COLUMNS):
        rows.append((index + 1, name, sql_type if index == 2 else "nvarchar(255)", 8 if index == 2 else 510,
                     26 if index == 2 else 0, scale if index == 2 else 0, True,
                     None if index == 2 else "SQL_Latin1_General_CP1_CI_AS", None, None))
    return rows


class MetadataTests(unittest.TestCase):
    def test_metadata_supports_representable_sql_datetime_types(self):
        for sql_type, scale in (("datetime", 3), ("smalldatetime", 0), ("datetime2(0)", 0), ("datetime2(6)", 6)):
            result = validate(metadata(sql_type, scale))
            self.assertEqual(result[2]["system_type_name"], sql_type)
            self.assertEqual(len(result), 8)
            self.assertEqual(set(result[0]), set(helper.METADATA_COLUMNS))
        self.assertIn("sys.dm_exec_describe_first_result_set(?, ?, 0)", helper.METADATA_SQL)

    def test_metadata_rejects_datetime2_seventh_fractional_digit(self):
        with self.assertRaises(helper.ValidationError) as caught:
            validate(metadata("datetime2(7)", 7))
        self.assertEqual(caught.exception.category, "unsupported_precision")

    def test_metadata_rejects_wrong_columns_types_and_describe_errors(self):
        cases = [metadata()[:-1], list(reversed(metadata()))]
        for column, value in ((1, "WrongName"), (2, "int"), (8, 11526), (9, "UNDECLARED_PARAMETER")):
            rows = metadata()
            altered = list(rows[0])
            altered[column] = value
            rows[0] = tuple(altered)
            cases.append(rows)
        cases.append(metadata("datetimeoffset(6)", 6))
        cases.append(metadata("datetime2(3)", 6))
        for rows in cases:
            with self.subTest(rows=rows), self.assertRaises(helper.ValidationError):
                validate(rows)
