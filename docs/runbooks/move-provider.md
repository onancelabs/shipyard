# Move an environment to another provider

Apps and Kamal configs don't change, because hostnames stay `<project>-<env>-<name>`.

1. Take a backup of every database.
2. Destroy the old servers with `make destroy ENV=<env> CONFIRM=<env>`, or keep them running until the new ones serve traffic and rename the environment for the new copy.
3. Change `shipyard_provider` and the provider's settings (sizes, region) in `vars.yml`, and add the new provider's credential to the vault.
4. Run `make up ENV=<env>`, then `make verify ENV=<env>`.
5. Restore the databases on the new data server. See [Restore a backup](restore-a-backup.md).
6. Update the private address in `DATABASE_URL` and `REDIS_URL` in Doppler if apps and data are on separate servers.
7. Redeploy every app with `kamal deploy -d <env>`.

DNS moves to the new servers during step 4, when configure publishes the records.
