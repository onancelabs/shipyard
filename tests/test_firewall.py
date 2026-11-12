import pytest
from ansible.errors import AnsibleFilterError

from shipyard import shipyard_firewall_rules, shipyard_validate_secret

CLOUDFLARE = ["173.245.48.0/20", "2400:cb00::/32"]
CIDR = "10.10.0.0/16"
ALL_IN_ONE = [{"name": "main", "roles": ["app", "data", "proxy"]}]
SPLIT = [{"name": "app", "roles": ["app", "proxy"]}, {"name": "data", "roles": ["data"]}]


def rules_for(server, servers, exposure="public", cloudflare=CLOUDFLARE):
    return shipyard_firewall_rules(server, servers, exposure, cloudflare, CIDR)


def tcp_ports(rules):
    return {rule["ports"] for rule in rules if rule["protocol"] == "tcp"}


def test_public_proxy_gets_web_ports_from_cloudflare_only():
    rules = rules_for(ALL_IN_ONE[0], ALL_IN_ONE)
    web = [rule for rule in rules if rule["ports"] in ("80", "443")]
    assert len(web) == 2
    assert all(rule["sources"] == sorted(CLOUDFLARE) for rule in web)


def test_private_proxy_gets_no_web_ports():
    assert tcp_ports(rules_for(ALL_IN_ONE[0], ALL_IN_ONE, exposure="private")) == set()


def test_public_proxy_refuses_empty_cloudflare_list():
    with pytest.raises(AnsibleFilterError, match="Cloudflare"):
        rules_for(ALL_IN_ONE[0], ALL_IN_ONE, cloudflare=[])


def test_data_ports_only_on_a_split_data_server():
    assert tcp_ports(rules_for(ALL_IN_ONE[0], ALL_IN_ONE)) == {"80", "443"}
    data_rules = rules_for(SPLIT[1], SPLIT)
    assert tcp_ports(data_rules) == {"5432", "6379"}
    assert all(rule["sources"] == [CIDR] for rule in data_rules if rule["protocol"] == "tcp")


def test_port_22_never_opens():
    for servers in (ALL_IN_ONE, SPLIT):
        for server in servers:
            for exposure in ("public", "private"):
                assert "22" not in {rule["ports"] for rule in rules_for(server, servers, exposure)}


def test_secret_rejects_url_unsafe_characters():
    with pytest.raises(AnsibleFilterError, match="openssl rand -hex 24"):
        shipyard_validate_secret("abc+def/ghi=jklmnopq", "vault_postgres_password")
