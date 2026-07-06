# API Auth and RBAC Strategy

We need to enforce strict Role-Based Access Control (RBAC) boundaries between Clients (read-only) and Managers (read-write) at the API level.

We decided to use FastAPI route-level dependency injection instead of global middleware for authorization. We will implement a tiered dependency structure:
1. `authenticate_user`: Validates the JWT/Auth Token and returns the base `UserDb` record.
2. `require_client`: Verifies the user has an associated `ClientProfile`.
3. `require_manager`: Verifies the user has an associated `ManagerProfile`.
4. `verify_project_ownership`: A parameterized dependency (e.g., `Depends(ProjectOwnership("client"))`) that ensures the requested project belongs to the current user (`project.client_id == current_user.id`).
5. `verify_github_url`: A dependency ensuring the `github_repo_url` exists for Manager write access.

By utilizing this Double-Gate Strategy at the route level, we ensure:
- A Client attempting to hit a Manager route will receive a `403 Forbidden` because they lack a `ManagerProfile`.
- A Client attempting to fetch projects they don't own will trigger a `404 Not Found` (or `403 Forbidden`) via resource isolation during the SQL query joining `ProjectDb` and `ClientProfile`.
- The logic remains explicit, testable, and strictly adheres to the principle of least privilege at the point of action.
