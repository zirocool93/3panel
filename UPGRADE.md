# Upgrade

## Supported flow

Run updates from the deployment checkout:

```bash
cd /opt/vpnbotx
./scripts/update.sh main
```

The update script:

1. creates a PostgreSQL backup;
2. fetches Git refs;
3. fast-forwards the selected branch or checks out the selected ref;
4. rebuilds containers;
5. runs Alembic migrations;
6. restarts the Compose services.

For versioned deployments, pin a Git tag or release branch and test upgrades on a backup copy
before live rollout.

## Rollback constraints

Container rollback and schema rollback are separate concerns. Do not assume an older application
version can read a newer schema. Keep the backup created before an update and review migration
notes before restoring it.

