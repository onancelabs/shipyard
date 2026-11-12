# Rebuild a server

Rebuild a server when its first boot failed, its disk is beyond repair, or you're changing its image.

1. If it's a data server, take a fresh backup first: `/opt/<project>/backups/pg-backup.sh`. Data on a block volume survives the rebuild. Data on the root disk doesn't.
2. Delete the server in the provider's console, or with the provider's CLI. Leave its volume.
3. Remove the old machine from the tailnet in the Tailscale admin console, so the new one can take the same name.
4. Run `make up ENV=<env>`. Shipyard creates only the missing server, mints a key for it alone, reattaches the volume, recreates its firewall and rewrites `servers.yml`.
5. Redeploy the apps that ran on it with `kamal deploy -d <env>`.
6. Commit the updated `servers.yml`, since the server's addresses changed.

If the rebuilt server held data on its root disk, restore from the backup. See [Restore a backup](restore-a-backup.md).
