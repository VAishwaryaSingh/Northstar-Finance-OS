from mappings import ReferenceData, map_account, map_customer, map_entity, map_vendor


def make_reference_data() -> ReferenceData:
    return ReferenceData(
        entities_by_code={"NHH-UK": "ENT-001", "NHS-US": "ENT-002"},
        customers_by_code={"C0001": "CUST-001"},
        vendors_by_code={"V0001": "VEND-001"},
        vendors_by_name={"medical supplies ltd": "VEND-001"},
        vendor_names=["Medical Supplies Ltd"],
        accounts_by_code={"5000": "ACC-001"},
    )


def test_map_entity_resolves_known_code():
    ref = make_reference_data()
    assert map_entity("NHH-UK", ref) == "ENT-001"


def test_map_entity_returns_none_for_blank_code():
    ref = make_reference_data()
    assert map_entity("", ref) is None
    assert map_entity(None, ref) is None


def test_map_entity_returns_none_for_unknown_code():
    ref = make_reference_data()
    assert map_entity("XX-ZZ", ref) is None


def test_map_customer_and_account():
    ref = make_reference_data()
    assert map_customer("C0001", ref) == "CUST-001"
    assert map_customer("C9999", ref) is None
    assert map_account("5000", ref) == "ACC-001"
    assert map_account("9999", ref) is None


def test_map_vendor_exact_code_match():
    ref = make_reference_data()
    vendor_id, method = map_vendor("V0001", "Medical Supplies Ltd", ref)
    assert vendor_id == "VEND-001"
    assert method == "exact_code"


def test_map_vendor_fuzzy_name_match_recovers_close_spelling():
    # This is the actual pair from 04-data/data-quality-log.md's
    # "Inconsistent Vendor Name" issue -- vendor_code is blank (unmapped at
    # source), so resolution has to fall back to the fuzzy name match.
    ref = make_reference_data()
    vendor_id, method = map_vendor(None, "Med Supplies Ltd", ref)
    assert vendor_id == "VEND-001"
    assert method == "fuzzy_name"

    vendor_id, method = map_vendor(None, "Medical Supplies Limited", ref)
    assert vendor_id == "VEND-001"
    assert method == "fuzzy_name"


def test_map_vendor_unresolved_when_nothing_close_enough():
    ref = make_reference_data()
    vendor_id, method = map_vendor(None, "Completely Different Company", ref)
    assert vendor_id is None
    assert method == "unresolved"


def test_map_vendor_unresolved_when_both_fields_blank():
    ref = make_reference_data()
    vendor_id, method = map_vendor(None, None, ref)
    assert vendor_id is None
    assert method == "unresolved"


def test_map_functions_treat_nan_as_blank_not_a_real_value():
    # Regression test: building a DataFrame from a list of dicts turns a
    # Python None into a float NaN whenever the column also holds strings
    # elsewhere, and NaN is truthy in plain Python -- this silently broke
    # every map_* function's blank check until _blank() was added.
    ref = make_reference_data()
    nan = float("nan")
    assert map_entity(nan, ref) is None
    assert map_customer(nan, ref) is None
    assert map_account(nan, ref) is None
    vendor_id, method = map_vendor(nan, nan, ref)
    assert vendor_id is None
    assert method == "unresolved"
