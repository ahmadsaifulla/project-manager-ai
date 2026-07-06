# Task Concurrency and SLA Management

To handle concurrency, task starvation, and orphaned "In Progress" states when Managers download Tasks, we established the following architectural patterns:

1. **Atomic Pessimistic Locking on Download:**
   The `GET /tasks/{id}/download` endpoint acts as a transactional gatekeeper using a `SELECT FOR UPDATE` SQL query. The API enforces that a task can only transition to `IN_PROGRESS` if its status is `TODO`. Any concurrent attempt to download an `IN_PROGRESS` task by a different manager returns a `409 Conflict` with the current `assignee_id`.

2. **SLA Timer for Stale Task Recovery:**
   To prevent tasks from being trapped indefinitely in the `IN_PROGRESS` state, we introduce an `assigned_at` timestamp in `TaskDb`. A background Task Reclamation Worker (cron-job or Celery beat) will periodically sweep tasks. Any task where `status == 'IN_PROGRESS'` and `assigned_at < (now - 48 hours)` is automatically reclaimed:
   - Status reverts to `TODO`.
   - `assignee_id` is nullified.
   - `assigned_at` is cleared.
   - Task metadata is flagged with `RECLAIMED_BY_SLA`.

3. **Manual Release (Manager Leave Edge Case):**
   Managers are provided a "Release Task" button in the Kanban UI. This allows a Manager to voluntarily relinquish a task, immediately clearing the lock and resetting the status to `TODO`, bypassing the 48-hour SLA limit.
