# Observability

A monitoring node collects metrics, logs and traces from every server in a project, over the tailnet.

- **The monitoring node** runs Prometheus, Loki, Tempo and Grafana. It's its own inventory, `mon`, shared by the project's environments.
- **Every server** runs node-exporter, cAdvisor and Grafana Alloy. Data servers add Postgres and Redis exporters. App servers accept OpenTelemetry from apps.

## Set up

1. Add the monitoring tags to your ACL. [tailscale-acl.hujson](../tailscale-acl.hujson) includes them.
2. Edit `ansible/inventories/mon/group_vars/all/vars.yml`, create its vault with `make vault-init ENV=mon`, and run `make up ENV=mon`. Grafana is at `https://grafana.<domain>` over the tailnet. Sign in as `admin` with `vault_grafana_admin_password`.
3. In each environment's `vars.yml`, set:

   ```yaml
   shipyard_observability: true
   observability_mon_host: example-mon-main
   ```

4. Run `make configure ENV=<env>`.

## Apps

App containers send OpenTelemetry to `http://host.docker.internal:4318`. Add this to the app's Kamal server options:

```yaml
servers:
  web:
    options:
      add-host: host.docker.internal:host-gateway
```

Telemetry is fail-open. If the monitoring node is down, apps keep working.

## Things to know

- Every agent has a memory limit. On a 2 GB server, monitoring agents without limits once starved the apps.
- Logs carry a stable `service` label taken from Kamal's container labels, so a deploy doesn't create a new log stream name.
- Grafana's data sources have fixed IDs (`shipyard-prometheus`, `shipyard-loki`, `shipyard-tempo`), so links from traces to logs survive a rebuild of the node.
- The receivers have no authentication. The tailnet ACL is what limits who can send, so keep the monitoring grant as narrow as the example.
- Servers can't resolve tailnet names, so Shipyard looks up the monitoring node's address from your machine and pins it in Alloy's hosts file. After rebuilding the monitoring node, run `make configure` on each environment.
