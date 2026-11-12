# Bring your own servers

Set `shipyard_provider: byo` to configure machines that already exist, on any host. Shipyard creates nothing and destroys nothing.

## Requirements

- Ubuntu 24.04 on each machine, with `curl` and Python 3.
- Your SSH key accepted on each machine, as `root` or as a user with passwordless `sudo`. Shipyard uses it once, to join the machine to the tailnet.
- A private network between the machines, if there's more than one.

## Server list

Each entry adds where to reach the machine the first time and its private address:

```yaml
shipyard_provider: byo
shipyard_network_cidr: 10.0.0.0/24
shipyard_servers:
  - name: main
    roles: [proxy, app, data]
    address: 203.0.113.10      # used for the first SSH session only
    private_ip: 10.0.0.10
    ssh_user: ubuntu           # optional, default root
    volume_device: /dev/disk/by-id/scsi-0EXAMPLE_volume   # optional
```

`size` and `shipyard_region` aren't used.

## What it does

1. Pings each machine's tailnet name. A machine that answers is left alone.
2. For each machine that doesn't, mints a single-use Tailscale key, connects to `address` over SSH and runs `tailscale up --ssh`.
3. Over Tailscale, installs a host firewall (`nftables`) with the same rules every provider applies. It accepts everything on `tailscale0`, Tailscale's UDP port and the server's own rules, and drops the rest. Port 22 is reachable only over Tailscale.

The firewall replaces only its own `shipyard` table, so Docker's rules stay in place.

## Things to know

- **Ports Docker publishes skip the host firewall.** Docker forwards published ports before the host's input rules see them. Shipyard publishes Postgres and Redis on the private address only, so keep that address off the public internet.
- **Disable password logins yourself.** Shipyard doesn't change `sshd` on machines it didn't create.
- **Destroy refuses.** Remove `servers.yml` to make Shipyard forget the machines.
- **Load balancer:** not supported.
- **Break-glass access** is whatever console your host offers.
