# Goals

## Current Phase: Production Maintenance

BIND is production-ready at v1.7.1. Active goals:

- Maintain SQLite backend stability; monitor for schema drift or FTS5 edge cases.
- Keep Cloudflare-resistance layers current as upstream anti-bot measures evolve.
- Maintain CI passing on all commits.

## Deferred / Future

- Performance tuning for very large datasets (>100k records) — not yet a practical concern post-SQLite.
- Additional torrent source adapters beyond current scope — operator decision required.
