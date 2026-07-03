# Kanban Phase Updates (Version 2)

This document outlines the specific upgrades achieved during the Kanban sprint stabilization phase.

## Frontend Shielding
* **Error Boundary and Toast Notifications:** Implemented a robust error handling flow with Toast notifications across the React frontend.
  * *Why:* To shield the React state from unmounting or entering a corrupt "White Screen of Death" during fatal 500 API errors. Errors are now gracefully surfaced to the user without breaking the session.

## Backend Architecture
* **LangGraph DAG State Machine Fix:** Restructured the `approve_goals` route to execute `ainvoke` securely *before* updating the database state via `aupdate_state`.
  * *Why:* To prevent race conditions and permanent database lockouts. If the graph crashed previously (e.g. from an LLM timeout), the state would prematurely lock to `goals_approved=True`, resulting in permanent 400 Bad Request errors on all subsequent user retries. Transactional execution shields the DB.

* **Database Expansion:** Added an `evaluation_feedback` column and expanded the `taskstatus` ENUM.
  * *Why:* To natively support the Quality Control (QC) pipeline's data requirements and review cycles within the Postgres schema.
