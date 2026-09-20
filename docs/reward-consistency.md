# Daily reward consistency

Daily coins are awarded once per user per IST submission day. Wallet-row locks
serialize submission, coin updates and redemption. Attempt and ledger locking
reads refresh stale state under MySQL REPEATABLE READ. A persisted ledger-day
check also prevents a reset streak cache from awarding the same day twice.
Daily assignment creation shares the wallet lock to avoid overlapping browser
requests creating competing assignments. No schema migration is required.

The history UI uses the daily reward's stored earning date (`note`) and formats
other timestamps in IST, interpreting naive database timestamps as UTC. Two
awards on different IST days can share a UTC calendar date; these must not be
removed as duplicates. No historical transactions are hidden or deleted.

## Diagnose existing rows (read-only)

Run against the application database to find repeated awards for the same
recorded earning day:

```sql
SELECT user_id, note AS earning_day, COUNT(*) AS award_count,
       GROUP_CONCAT(id ORDER BY id) AS transaction_ids, SUM(amount) AS total
FROM edge_coin_transactions
WHERE reason = 'daily_question'
  AND note REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
GROUP BY user_id, note
HAVING COUNT(*) > 1;
```

Investigate ledger and cached balance together before correcting old records:
concurrent updates may have recorded two credits while only incrementing the
cached balance once. Do not blindly delete a row or subtract coins. The deployed
Aiven database was not accessed or modified as part of this fix.

Regression tests cover repeat awards, stale session state, reset streak caches,
next-day eligibility, lifetime streak bonuses, rollback, and stale redemption
balances. They use SQLite; true concurrent MySQL lock behavior still requires a
MySQL integration environment.
