"""Provider-neutral decisions every provider and core role shares."""

import ipaddress
import re

from ansible.errors import AnsibleFilterError

ROLES = ("proxy", "app", "data", "mon")
SHORT_NAME = re.compile(r"^[a-z][a-z0-9-]{0,15}$")
SECRET = re.compile(r"^[A-Za-z0-9_-]{16,}$")
ANYWHERE = ["0.0.0.0/0", "::/0"]
TAILSCALE_UDP_PORT = "41641"


class FilterModule:
    def filters(self):
        return {
            "shipyard_hostname": shipyard_hostname,
            "shipyard_validate_servers": shipyard_validate_servers,
            "shipyard_firewall_rules": shipyard_firewall_rules,
            "shipyard_validate_secret": shipyard_validate_secret,
            "shipyard_validate_provisioned": shipyard_validate_provisioned,
            "shipyard_tunnel_ingress": shipyard_tunnel_ingress,
        }


def shipyard_hostname(short: str, project: str, env: str) -> str:
    """Return the server's hostname, which is also its tailnet name."""
    return f"{project}-{env}-{short}"


def shipyard_validate_servers(servers: list[dict], provider: str, load_balancer: bool = False) -> list[dict]:
    """Check the environment's server list and return it with defaults filled in.

    :param servers: the `shipyard_servers` list from the environment's vars.
    :param provider: the environment's provider, used for provider-specific required keys.
    :param load_balancer: whether the load balancer module is on, which allows several proxies.
    """
    if not servers:
        raise AnsibleFilterError("shipyard_servers is empty. List at least one server.")
    seen: set[str] = set()
    result = []
    for server in servers:
        name = server.get("name", "")
        if not SHORT_NAME.match(name):
            raise AnsibleFilterError(
                f"Server name {name!r} must start with a letter and use only a-z, 0-9 and '-', up to 16 characters."
            )
        if name in seen:
            raise AnsibleFilterError(f"Server name {name!r} appears twice in shipyard_servers.")
        seen.add(name)
        roles = server.get("roles") or []
        unknown = [role for role in roles if role not in ROLES]
        if not roles or unknown:
            raise AnsibleFilterError(
                f"Server {name!r} has roles {roles}. Each server needs one or more of {', '.join(ROLES)}."
            )
        if provider == "byo":
            for key in ("address", "private_ip"):
                if not server.get(key):
                    raise AnsibleFilterError(f"byo server {name!r} needs {key}.")
        result.append({**server, "roles": sorted(roles), "volume_gb": server.get("volume_gb")})

    proxies = [s["name"] for s in result if "proxy" in s["roles"]]
    if not load_balancer and len(proxies) != 1:
        raise AnsibleFilterError(
            f"Exactly one server needs the proxy role without the load balancer, found {proxies or 'none'}."
        )
    return result


def shipyard_firewall_rules(
    server: dict,
    servers: list[dict],
    exposure: str,
    cloudflare_ips: list[str],
    network_cidr: str,
    load_balancer: bool = False,
) -> list[dict]:
    """Return the inbound rules one server needs, as `{protocol, ports, sources}` dicts.

    Port 22 is never opened, because every login goes through Tailscale SSH.
    """
    if exposure not in ("public", "private"):
        raise AnsibleFilterError(f"shipyard_exposure must be public or private, not {exposure!r}.")
    rules = [
        {"protocol": "udp", "ports": TAILSCALE_UDP_PORT, "sources": ANYWHERE},
        {"protocol": "icmp", "ports": None, "sources": [network_cidr]},
    ]
    roles = server["roles"]
    if "proxy" in roles and exposure == "public":
        if not cloudflare_ips:
            raise AnsibleFilterError(
                "Cloudflare's IP list is empty, so 80 and 443 can't be limited to Cloudflare. Re-run when the list loads."
            )
        sources = sorted(cloudflare_ips) + ([network_cidr] if load_balancer else [])
        for port in ("80", "443"):
            rules.append({"protocol": "tcp", "ports": port, "sources": sources})
    other_app = any("app" in s["roles"] for s in servers if s["name"] != server["name"])
    if "data" in roles and other_app:
        for port in ("5432", "6379"):
            rules.append({"protocol": "tcp", "ports": port, "sources": [network_cidr]})
    return sorted(rules, key=lambda rule: (rule["protocol"], rule["ports"] or ""))


def shipyard_validate_secret(value: str, name: str) -> str:
    """Return the secret if it can sit inside a connection URL unescaped."""
    if not isinstance(value, str) or not SECRET.match(value):
        raise AnsibleFilterError(
            f"{name} must be at least 16 characters of A-Z, a-z, 0-9, '_' or '-', so it works inside a URL. "
            "Generate one with: openssl rand -hex 24"
        )
    return value


def shipyard_validate_provisioned(
    provisioned: list[dict], servers: list[dict], project: str, env: str
) -> list[dict]:
    """Check a provider's output covers every server once, with the fields core roles read."""
    by_name = {entry.get("name"): entry for entry in provisioned}
    for server in servers:
        entry = by_name.get(server["name"])
        if entry is None:
            raise AnsibleFilterError(f"The provider returned nothing for server {server['name']!r}.")
        expected = shipyard_hostname(server["name"], project, env)
        if entry.get("hostname") != expected:
            raise AnsibleFilterError(
                f"Server {server['name']!r} has hostname {entry.get('hostname')!r}, not {expected!r}."
            )
        try:
            ipaddress.ip_address(entry.get("private_ip") or "")
        except ValueError:
            raise AnsibleFilterError(f"Server {server['name']!r} has no valid private_ip.") from None
    if len(by_name) != len(servers):
        extra = sorted(set(by_name) - {s["name"] for s in servers})
        raise AnsibleFilterError(f"The provider returned servers that aren't listed: {extra}.")
    return [{**by_name[s["name"]], "roles": s["roles"]} for s in servers]


def shipyard_tunnel_ingress(routes: list[dict], kamal_proxy_port: int) -> list[dict]:
    """Build cloudflared's ingress list, answering 404 for anything a route doesn't name.

    :param routes: `{hostname, path?, host_header?, service?}` entries. Without `service`, the route goes to
        kamal-proxy, which picks the app by Host, so `host_header` must name the app's registered host.
    """
    ingress: list[dict] = []
    for index, route in enumerate(routes):
        hostname = route["hostname"]
        entry: dict = {"hostname": hostname, "service": route.get("service")}
        if not entry["service"]:
            if not route.get("host_header"):
                raise AnsibleFilterError(
                    f"Tunnel route {hostname!r} goes to kamal-proxy and needs host_header."
                )
            entry["service"] = f"http://127.0.0.1:{kamal_proxy_port}"
        if route.get("host_header"):
            entry["originRequest"] = {"httpHostHeader": route["host_header"]}
        if route.get("path"):
            entry["path"] = route["path"]
        ingress.append(entry)
        later_same_host = any(r["hostname"] == hostname for r in routes[index + 1 :])
        if route.get("path") and not later_same_host:
            ingress.append({"hostname": hostname, "service": "http_status:404"})
    ingress.append({"service": "http_status:404"})
    return ingress
