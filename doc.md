# Vector index runbook

This runbook covers the nightly reindex job and the checks that follow it.

## Reindex

Run the job from the scheduler, never from a laptop:

```bash
python -m pipeline.reindex \
  --source s3://docs/current \
  --max-tokens 512 \
  --overlap 64
```

The job reads every document under the source prefix, chunks it, and writes
new vectors to a staging index. It does not touch the live index until the
checks below pass.

## Checks

Run these before you call the job done. If any of them fail, stop and follow
the rollback steps instead of promoting the staging index.

| Check | Command | Expected |
| --- | --- | --- |
| Row count | `select count(*) from staging_index` | within 2% of source document count |
| Freshness | `select max(updated_at) from staging_index` | under 15 minutes old |
| Sample query | `curl -s $STAGING_URL/search?q=test` | 200 response with at least one result |

## Rollback

If a check fails, do not delete the staging index; leave it for whoever
debugs the failure next. Point the search service back at the previous
snapshot, and page whoever owns the nightly job before you touch anything
else. A bad reindex is recoverable. A deleted staging index is not.
