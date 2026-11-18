# Offline SQL Report Parameter Binder

Prepare SQL placeholders and ordered parameters for a fictional report. The
binder accepts Python `date` or `datetime` values, a sequence of product labels
and an allowed set of labels. It returns the SQL template with one positional
placeholder per product and a tuple containing the two dates followed by the
products in selection order.

This edition preserves the original binding logic and seven tests. It uses a
fictional SQL template and product IDs, with a neutral module name and matching
test expectations. The runtime uses only the Python standard library.

See the [setup and usage guide](SETUP.md) and the [source release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/sql-report-parameter-binder-v0.1.0).
