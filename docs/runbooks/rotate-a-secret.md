# Rotate a secret

## Postgres or Redis password

1. Generate a new value with `openssl rand -hex 24`.
2. Put it in the vault with `make vault ENV=<env>`.
3. Run `make configure ENV=<env>`. For Postgres, Shipyard finds that the old password no longer works and runs `ALTER ROLE`. For Redis, the changed config recreates the container.
4. Update `DATABASE_URL` or `REDIS_URL` in Doppler for every app that uses it.
5. Redeploy those apps with `kamal deploy -d <env>`.

Apps lose their connection between steps 3 and 5. Rotate when a short interruption is acceptable.

## Cloudflare, R2 or provider token

1. Create the new token with the same scope, and put it in the vault.
2. Run `make up ENV=<env>`.
3. Revoke the old token.

## Tailscale OAuth client

1. Create a new client with the same scope and tags.
2. Update the vault and the GitHub environment's `TS_OAUTH_CLIENT_ID` and `TS_OAUTH_SECRET`.
3. Delete the old client. Servers that already joined keep working, because their node keys don't depend on the client.

## Vault password

Run `cd ansible && uv run ansible-vault rekey inventories/<env>/group_vars/all/vault.yml`, then update the password manager and the GitHub environment's `VAULT_PASSWORD`.
