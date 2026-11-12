# Shipyard guide

This guide takes you from an empty account to a live app on `https://<app>.<your-domain>`, with backups running and no public SSH port. Follow it in order the first time. Each step that exists because something once broke says what it prevents.

## How it fits together

- **Ansible** creates the servers (`make provision`) and configures them (`make configure`). `make up` runs both.
- **A provider** is the only part that talks to a cloud. It turns your `shipyard_servers` list into machines and writes `ansible/inventories/<env>/servers.yml`. Everything after that reads only that file.
- **Tailscale** is the only way in. Servers join your tailnet at first boot, and Ansible, Kamal and CI reach them by name over Tailscale SSH. No server accepts SSH from the internet.
- **Cloudflare** holds each environment's domain. Caddy gets one wildcard certificate per environment through Cloudflare DNS-01 and forwards every request to kamal-proxy.
- **Kamal** deploys your apps. Kamal configs live in each app's repo, not here.
- **Postgres and Redis** run on the data server as a Compose project that Ansible manages. Kamal never deploys them.
- **Secrets** are split. Infrastructure secrets live in an Ansible Vault per environment, committed encrypted. App secrets live in Doppler, and Kamal reads them at deploy time.

## 1. Choose a provider

Set `shipyard_provider` in each environment's `vars.yml`. Environments can use different providers.

| Provider | Use it when | Page |
|---|---|---|
| `digitalocean` | You want Shipyard to create the servers, network, volumes and firewalls for you. | [DigitalOcean](providers/digitalocean.md) |
| `byo` | You already have Ubuntu machines, on any host, and want Shipyard to configure them. | [Bring your own servers](providers/byo.md) |

The dev shape is one server running everything. An API, two server-rendered apps, Postgres and Redis fit in 4 GB of memory. With 2 GB, a deploy that starts a new container beside the old one can run out of memory.

For a cloud Shipyard doesn't ship, see [Writing a provider](writing-a-provider.md).

## 2. Accounts and tokens

Create these before you start. Each token gets the narrowest scope that works.

1. **Tailscale.** Create one OAuth client per environment under **Settings > OAuth clients**, with the **Auth Keys** write scope and the tags `tag:<project>-<env>` and `tag:<project>-ci-<env>`. Shipyard uses it to mint a single-use key for each new server, and CI uses it to join the tailnet. Add the tags to your ACL first (step 5), or the console won't offer them.
2. **Cloudflare.** Add each environment's domain as its own zone. Create one API token per zone with **Zone > DNS > Edit** on that zone only. Set the zone's SSL/TLS mode to **Full (strict)**. One token per zone means a dev token can never change prod's records.
3. **Cloudflare R2.** Create a bucket for backups and an R2 API token with **Object Read & Write** on that bucket only. Note the bucket's S3 endpoint. A bucket in the EU jurisdiction uses `https://<account-id>.eu.r2.cloudflarestorage.com`, and the plain endpoint answers every request with `AccessDenied`.
4. **Your provider.** See the provider's page for its credential.
5. **Doppler.** Create one project per app, with one config per environment (`dev`, `prod`), and a read-only service token for each config.
6. **A container registry.** The examples use GitHub Container Registry, where CI pushes with its built-in `GITHUB_TOKEN`.

Use first-level names such as `api.example-dev.com`. Cloudflare's free certificates don't cover two-level names such as `api.dev.example.com` when the record is proxied.

## 3. Copy the template

Shipyard is a template, not a dependency. Copy it once and own the copy.

- **Standalone:** create a repository from the template on GitHub.
- **Inside a monorepo:** copy the whole tree into `infra/`. Run every `make` command from `infra/`, and move `.github/workflows/` to the monorepo's root, setting `working-directory: infra` on each job.

Then install the toolchain. You need [uv](https://docs.astral.sh/uv/) and Tailscale on your machine.

```bash
make install
```

`make install` installs the pinned Python, Ansible, collections and linters into the repo. Nothing goes into your system Python.

## 4. Fill in vars and the vault

1. Edit `ansible/inventories/dev/group_vars/all/vars.yml`: `shipyard_project`, `shipyard_region`, `shipyard_network_cidr`, `shipyard_domain`, `shipyard_acme_email` and the server list. Sizes and regions use the provider's own names.
2. Create the vault and paste in every key from `vault.yml.example` with its value:

   ```bash
   make vault-init ENV=dev
   ```

3. Generate the Postgres and Redis passwords with `openssl rand -hex 24`. The passwords go inside connection URLs such as `postgres://app:<password>@postgres:5432/app`, so they must be URL-safe. Shipyard refuses a password with `+`, `/` or `=` before it touches a server.
4. Store the vault password in your password manager. CI needs it too (step 9).

To change a value later, run `make vault ENV=dev`.

Commit the encrypted `vault.yml`. Never commit `ansible/.vault_pass`.

## 5. Tailscale ACLs and tags

Copy [tailscale-acl.hujson](tailscale-acl.hujson) into your tailnet's access controls and replace `<project>`. It does three things:

- Declares the tags. Servers carry `tag:<project>-<env>`, and CI runs carry `tag:<project>-ci-<env>`.
- Lets each CI tag reach only its own environment, so a dev deploy can never touch prod.
- Lets admins use Tailscale SSH as `root`, with a fresh login check for prod.

Tags include the project, so several projects can share one tailnet without reaching each other's servers.

Servers run Tailscale with `--accept-dns=false`, so MagicDNS names don't resolve on the servers themselves. Your machine and CI resolve them, which is all Ansible and Kamal need.

## 6. Bring up dev

Make sure your machine is on the tailnet, then:

```bash
make up ENV=dev
```

`make up` first runs `make check`, which stops in seconds if uv, the collections, the vault or Tailscale is missing. Then it:

1. Creates the network and servers. Each new server boots with a single-use Tailscale key that expires after 30 minutes. A slow first boot once outlasted a 10-minute key and the server never joined. The key sits in the server's user data, which is readable from the server, so only a single-use key may go there.
2. Writes `servers.yml`. Commit it, so `make configure` and CI can reach the servers without calling the cloud.
3. Waits up to five minutes for each server to answer over Tailscale, then configures it: security updates with a nightly reboot window, swap, Docker, Caddy, Postgres, Redis and backups.
4. Publishes DNS records last. A record never points at a server that isn't ready.

Run it again. The second run must report `changed=0`. Then check the environment from outside and inside:

```bash
make verify ENV=dev
```

`make verify` confirms that port 22 is closed on every public address, that 80 and 443 refuse your machine (Cloudflare is the only allowed source), that every server answers over Tailscale and reaches the others' private addresses, and that each data volume is mounted.

If something looks wrong, `make diag ENV=dev` prints each server's containers, disk, memory, recent Caddy log and Tailscale status.

### What the host roles take care of

- **Docker storage.** New Docker installs default to the containerd image store, which monitoring agents can't read. Shipyard pins the classic `overlay2` store. Switching stores on a running server orphans every container, so Shipyard refuses to switch on a server that has containers unless you pass `-e docker_migrate_to_overlay2=true`.
- **Disk space.** Container logs are capped at three 10 MB files, and a weekly job prunes images and containers older than seven days. It never prunes volumes.
- **Caddy config.** Caddy mounts its config directory, not the single file. Ansible writes files by replacing them, and a container that mounts one file keeps reading the old copy.
- **Redis.** Redis uses `noeviction` by default, because BullMQ loses queue keys when Redis evicts them. Its memory limit is about twice `maxmemory`, because an append-only rewrite forks the process and copies pages. The password lives in `redis.conf`, so it never shows in `docker inspect`.
- **Password changes.** Changing `vault_postgres_password` or `vault_redis_password` and running `make configure` changes the password in the running service. See [Rotate a secret](runbooks/rotate-a-secret.md).

## 7. Add your first app

Kamal configs live in the app's repo. [`examples/`](../examples) has a web app and an API to copy from.

1. Copy `examples/web/config/` and `examples/web/.kamal/` into the app's repo, and set `service`, `image`, `registry.username`, `app_port` and the destination's `proxy.host`.
2. Keep these settings identical in every app on a server, because all apps share one kamal-proxy:

   ```yaml
   proxy:
     ssl: false
     run:
       http_port: 8080
       https_port: 8443
       metrics_port: 9090
   ```

   `ssl: false` is correct. Caddy terminates TLS and forwards to kamal-proxy on port 8080.
3. Give the app a health check path, and make sure the app listens on `0.0.0.0` inside the container. Some frameworks bind to the container's own address unless told otherwise, which breaks health checks. Inside a container, check `127.0.0.1`, never `localhost`, which can resolve to the IPv6 address `::1` where nothing listens.
4. For an app that needs Postgres or Redis, copy `examples/api/`. It joins the Docker network named after your project, so in dev it reaches `postgres:5432` and `redis:6379` by container name. In prod it uses the data server's private address from `servers.yml`.
5. Put the app's secrets in Doppler. In dev, `DATABASE_URL` is `postgres://<user>:<vault_postgres_password>@postgres:5432/<db>` and `REDIS_URL` is `redis://:<vault_redis_password>@redis:6379/0`. These passwords live in both the vault and Doppler, so change them in both places together.
6. Deploy from your machine with `doppler run -- kamal deploy -d dev`, or from CI with `examples/workflows/deploy.yml`.

In a monorepo, keep each app's config under `apps/<app>/config/` and deploy with `kamal deploy -c apps/<app>/config/deploy.yml -d dev`, pointing `builder.context` and `builder.dockerfile` at the repo root and the app's Dockerfile.

The examples keep three old containers (`retain_containers: 3`), so a deploy-heavy dev server doesn't fill its disk with old releases.

## 8. Optional modules

Each module is off until you turn it on in the environment's `vars.yml`.

- **Tunnel** (`shipyard_tunnel: true`): see [Tunnel](modules/tunnel.md).
- **Load balancer** (`shipyard_load_balancer: true`): see [Load balancer](modules/load-balancer.md).
- **Observability** (`shipyard_observability: true`): see [Observability](modules/observability.md).

## 9. Stand up prod

1. Edit `ansible/inventories/prod/group_vars/all/vars.yml`. Prod splits apps and data onto two servers, and the data server keeps Postgres and Redis on a block volume, so the data survives a rebuild of the server.
2. Create prod's vault with `make vault-init ENV=prod`, using prod's own Tailscale client, Cloudflare token and passwords.
3. Run `make provision ENV=prod` to create the servers.
4. The example ACL asks admins to log in again before SSH to prod, and Ansible can't show that prompt. Run `ssh root@<project>-prod-app` and `ssh root@<project>-prod-data` once, and complete the login in your browser.
5. Run `make configure ENV=prod`, then `make up ENV=prod` for `changed=0`, then `make verify ENV=prod`.
6. In prod, apps reach Postgres and Redis on the data server's private address, on ports 5432 and 6379. Only servers on the private network can connect.

To run provisioning from GitHub Actions, create a GitHub environment per Shipyard environment with these secrets and variables:

| Name | Kind | Value |
|---|---|---|
| `VAULT_PASSWORD` | secret | The environment's vault password. |
| `TS_OAUTH_CLIENT_ID` | secret | The environment's Tailscale OAuth client ID. |
| `TS_OAUTH_SECRET` | secret | The environment's Tailscale OAuth client secret. |
| `SHIPYARD_PROJECT` | variable | Your `shipyard_project`. |

Then run **provision dev** or **provision prod** from the Actions tab. Each environment has its own workflow, so each has its own run history. Protect the `prod` environment with required reviewers.

## 10. Day-two runbooks

- [Rotate a secret](runbooks/rotate-a-secret.md)
- [Restore a backup](runbooks/restore-a-backup.md)
- [Rebuild a server](runbooks/rebuild-a-server.md)
- [Move an environment to another provider](runbooks/move-provider.md)
- [Break-glass access](runbooks/break-glass.md)
- [Recover a failed Tailscale join](runbooks/tailscale-join.md)

To delete an environment's servers, run `make destroy ENV=dev CONFIRM=dev`. Block volumes stay unless you add `EXTRA="-e destroy_volumes=true"`.

## 11. Write a provider

See [Writing a provider](writing-a-provider.md).

## Make targets

| Target | What it does |
|---|---|
| `make install` | Installs the pinned toolchain and collections. |
| `make lint` | Runs yamllint, ansible-lint and ruff. |
| `make test` | Runs the firewall rule tests. |
| `make check` | Checks uv, the collections, the vault and Tailscale for an environment. |
| `make vault-init` | Creates an environment's encrypted vault. |
| `make vault` | Edits an environment's vault. |
| `make provision` | Creates or updates servers and writes `servers.yml`. |
| `make configure` | Configures the servers in `servers.yml` and publishes DNS. |
| `make up` | Runs `check`, `provision` and `configure`. |
| `make verify` | Checks ports, tailnet access, private networking and volumes. |
| `make diag` | Prints a status snapshot from every server. |
| `make destroy` | Deletes an environment's servers. Needs `CONFIRM=<env>`. |

Every target takes `ENV=` (default `dev`), `VAULT=` (default `--ask-vault-pass`) and `EXTRA=` for extra `ansible-playbook` arguments.
