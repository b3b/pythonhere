from network_here import get_all_available_ipv4_adrresses


def test_address_detected():
    adresses = list(get_all_available_ipv4_adrresses())
    assert adresses
    for _, ip in adresses:
        assert len(ip.split('.')) == 4
