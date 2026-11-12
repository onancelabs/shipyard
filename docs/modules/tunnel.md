# Tunnel

A Cloudflare Tunnel publishes chosen hostnames and paths from an environment without opening any port. Use it for a `private` environment that must still receive something from the internet, such as a payment provider's webhooks.

## Set up

1. Create a tunnel in the Cloudflare dashboard or with `cloudflared tunnel create <name>`. Keep its ID.
2. Paste the tunnel's `<id>.json` credentials into the vault as `vault_tunnel_credentials`, as a `|-` block. A double-quoted JSON string breaks the YAML.
3. In the environment's `vars.yml`:

   ```yaml
   shipyard_tunnel: true
   tunnel_id: 00000000-0000-0000-0000-000000000000
   tunnel_routes:
     - hostname: hooks.example-dev.com
       path: ^/webhooks/
       host_header: api.example-dev.com
   ```

4. Run `make configure ENV=<env>`.

The tunnel runs on the proxy server. Shipyard creates a proxied CNAME for each route's hostname in the environment's zone.

## Routes

- `hostname`: the public name. It must be in the environment's zone.
- `path`: optional regular expression. Requests to the hostname that don't match get a 404.
- `host_header`: the app's own hostname. kamal-proxy picks the app by Host, so a route to kamal-proxy needs it, or every request gets a 404.
- `service`: optional. Without it, the route goes to kamal-proxy.

Every hostname that has a path ends with a 404 for other paths, and the tunnel answers 404 for any hostname it doesn't list.

Test a path rule against real URLs before relying on it. A loose pattern such as `connect` also matches `/connection`. When one app serves public and private routes under one hostname, use Cloudflare Access instead of path rules.
