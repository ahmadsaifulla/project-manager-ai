# Supertype/Subtype Pattern for User Profiles

We are transitioning the AI Project Manager from a single-user prototype to a multi-tenant, production-grade SaaS platform requiring strict Role-Based Access Control (RBAC) between Clients and Managers.

We decided to use a Supertype/Subtype pattern for our database schema to model users. We will maintain a unified `UserDb` table handling pure authentication primitives (UUID, email, password hash/OAuth token). This base table will link via a 1:1 Foreign Key to specialized profile tables: `ClientProfile` (storing personal details and onboarding context) and `ManagerProfile` (storing employee_id and internal org data).

We chose this over a single `users` table with a `role` enum and nullable columns because the data requirements for Clients and Managers diverge significantly. A single table would become null-heavy and increase the risk of data leakage. This specialized schema keeps the authentication layer lean while allowing strict business logic to be enforced at the API layer (e.g., checking project ownership via `client_id` on the `ProjectDb`, or enforcing that Managers have an assigned `github_repo_url` before starting work).
