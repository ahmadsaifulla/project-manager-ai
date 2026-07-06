# QC Workflow and State Transitions

We are defining the execution workflow for Managers working on Tasks within the multi-tenant SaaS platform. Specifically, this addresses how the LangGraph AI QC Node evaluates code and how state transitions are handled upon failure.

1. **GitHub Context via Commit SHA:** 
   We will not use ephemeral branch names as the source of truth for evaluation. When a Manager triggers "Handover to QC" via the API (`PATCH /tasks/{id}/handover`), the payload must include the immutable `git_commit_sha`. The Orchestrator saves this SHA to the `TaskDb`. The AI QC Node then fetches the repository using the project's `github_repo_url` and performs a `git checkout <commit_sha>` to evaluate the exact code that was pushed, preventing race conditions from concurrent commits.

2. **Loop-Back State Transition on Failure:**
   If the AI QC Agent evaluates the code and returns a FAIL, we will not transition the task to a terminal `REJECTED` state. Instead, we implement a "Loop-Back" transition:
   - `Task.status` is reverted to `IN_PROGRESS`.
   - `Task.evaluation_feedback` is populated with the AI-generated report.
   - The task is cleared of the "Handover" intent.
   This guarantees a good UX by returning the task to the Manager's Kanban board immediately with actionable feedback, rather than trapping the task in a dead-end state.

3. **Control Handover:**
   Upon a QC failure, the LangGraph execution graph terminates. The AI QC Node does not automatically re-queue the task for further processing. The Orchestrator notifies the UI, returning control to the human Manager (the "Operator"), who must reconcile the feedback and push a new commit to start the cycle again.
