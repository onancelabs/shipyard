# Load balancer

The provider's managed load balancer goes in front of the proxy servers. Turn it on with `shipyard_load_balancer: true`, which also lets more than one server have the `proxy` role.

| Provider | Supported |
|---|---|
| `digitalocean` | Yes |
| `byo` | No. `make up` stops with a message. |

## DigitalOcean

- TLS passes through on port 443 to Caddy, so certificates stay on the servers.
- The load balancer accepts traffic only from Cloudflare's IPv4 ranges. The proxy servers' firewalls also accept traffic from the private network, because that's where the load balancer connects from.
- DNS moves to the load balancer's address during the next `make configure`.
- The target servers are fixed when the load balancer is created. To add or remove a proxy server, delete the load balancer in the control panel and run `make up` again.

## Turning it off

1. Set `shipyard_load_balancer: false` and keep one `proxy` server.
2. Run `make up`. DNS moves back to the proxy server.
3. Delete the load balancer in the provider's control panel.
