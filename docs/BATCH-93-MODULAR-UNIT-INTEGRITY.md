# Batch 93: measurement and unit integrity sources

Four independent MIT source tools validate explicit unit catalogs, resolve exact linear conversion paths, reconcile supplied quantity claims, and compare selected conversion outcomes under two catalog revisions. Each module contains its own unit core and copies of already public MIT helpers. Fictional HVAC duct, game distance, and software data-size examples use only supplied JSON.

An edge defines target quantity as source quantity multiplied by a positive rational factor. Catalog checks establish dimension and unit references; path checks separately require every unit to reach its dimension's declared base and every alternate path or cycle to agree. Quantity checks use exact rational arithmetic and explicit half-even or half-away final rounding to 0–6 decimal places. Changed outcomes and ambiguous or inconsistent catalogs withhold qualified scope.

The tools do not read instruments, SQL databases, browsers, network services, or original private records. Affine temperature offsets, exchange rates, calibration and physical accuracy are outside the contract. Reports can expose supplied identifiers, factors, and values; keep private reports private. Combined packaging remains deferred.
