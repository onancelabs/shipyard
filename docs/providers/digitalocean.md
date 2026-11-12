# DigitalOcean

Set `shipyard_provider: digitalocean`. Shipyard creates everything an environment needs and nothing else.

## Credential

Create a personal access token under **API > Tokens** with read and write scope, and put it in the vault as `vault_digitalocean_token`.

## What it creates

| Resource | Name | Notes |
|---|---|---|
| VPC | `<project>-<env>` | Uses `shipyard_network_cidr` in `shipyard_region`. Pick a range that doesn't overlap another environment's. |
| Droplets | `<project>-<env>-<name>` | Ubuntu 24.04, no SSH key, tagged `<project>-<env>` and `role-<role>`. |
| Volumes | `<project>-<env>-<name>` | Only for servers with `volume_gb`. Formatted ext4 and attached. |
| Firewalls | `<project>-<env>-<name>` | One per droplet. No inbound port 22. |

Sizes and regions use DigitalOcean's slugs, such as `s-2vcpu-4gb` and `nyc3`. `doctl compute size list` and `doctl compute region list` show them.

## Things to know

- **Firewalls can't be edited in place.** The DigitalOcean module only creates and deletes firewalls. When a server's rules change (for example, after switching exposure), Shipyard deletes that firewall and creates it again in the same run. The server has no cloud firewall for a few seconds during that.
- **Cloudflare's ranges are read at provision time.** When Cloudflare publishes new ranges, run `make provision` to pick them up.
- **Outbound mail ports are blocked.** DigitalOcean blocks outbound SMTP on ports 25, 465 and 587 for new accounts. Use your mail provider's alternate ports, such as 2465 or 2587, for alerts or app mail.
- **Recreating a droplet** is the fix for a failed first boot. See [Rebuild a server](../runbooks/rebuild-a-server.md).
- **Break-glass access** is the droplet's **Recovery Console** in the control panel. See [Break-glass access](../runbooks/break-glass.md).
- **Load balancer:** not supported yet.
