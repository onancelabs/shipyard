"""Map Shipyard's neutral firewall rules to DigitalOcean's API shape."""


class FilterModule:
    def filters(self):
        return {"do_inbound_rules": do_inbound_rules, "do_rules_match": do_rules_match}


def do_inbound_rules(rules: list[dict]) -> list[dict]:
    """Return the `inbound_rules` body DigitalOcean expects for neutral rules."""
    result = []
    for rule in rules:
        entry = {"protocol": rule["protocol"], "sources": {"addresses": list(rule["sources"])}}
        if rule["ports"]:
            entry["ports"] = rule["ports"]
        result.append(entry)
    return result


def do_rules_match(existing: list[dict], desired: list[dict]) -> bool:
    """Compare rule sets ignoring order, since DigitalOcean can't update a firewall in place."""
    return _normalise(existing) == _normalise(desired)


def _normalise(rules: list[dict]) -> set[tuple]:
    normalised = set()
    for rule in rules:
        ports = str(rule.get("ports") or "0")
        if ports == "all":
            ports = "0"
        addresses = frozenset((rule.get("sources") or {}).get("addresses") or [])
        normalised.add((rule["protocol"], ports, addresses))
    return normalised
