# Restore a backup

Backups run nightly from the data server. Each database in `backups_databases` goes to `s3://<bucket>/<prefix>/<db>-<timestamp>.dump` in Postgres custom format. Dumps older than `backups_retention_days` are deleted after each successful backup.

## Restore the newest dump

On the data server, as root over Tailscale SSH:

```bash
/opt/<project>/backups/pg-restore.sh <db>
```

The script downloads the newest dump for `<db>` and runs `pg_restore --clean --if-exists`, which replaces the database's current objects.

## Restore a specific dump

List the dumps, then pass a name:

```bash
/opt/<project>/backups/pg-restore.sh <db> <db>-20261112T031700Z.dump
```

## Drill

Run a drill after standing up an environment and then every few months:

1. Run the backup by hand: `/opt/<project>/backups/pg-backup.sh`. It exits non-zero if any database failed.
2. Create a scratch database: `docker exec postgres createdb -U <user> restore_drill`.
3. Restore the newest dump into it: `/opt/<project>/backups/pg-restore.sh <db> latest restore_drill`.
4. Check a few row counts against the live database, then drop `restore_drill`.

The backup log is `/var/log/<project>-pg-backup.log`. To get alerted when a backup fails, set `backups_heartbeat_url` to a dead man's switch URL from a service such as Healthchecks.io. Shipyard calls it only after every database backed up.
