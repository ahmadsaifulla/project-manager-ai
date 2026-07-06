# Context

This context defines the core concepts for the multi-tenant AI Project Manager platform, focusing on user roles, project ownership, and task execution.

## Language

**Client**:
An external user (formerly Spectator) who provides project requirements via the AI Chatbot and has strict read-only access to the resulting Kanban board.
_Avoid_: Spectator, User, Customer

**Manager**:
An internal user (formerly Executor) identified by an Employee ID who accesses a global dashboard, creates GitHub repositories for projects, and executes tasks. Has read-write access to their assigned projects.
_Avoid_: Executor, Developer, Employee

**Project**:
A body of work owned by a Client and assigned to Managers. It must have an attached GitHub repository before any tasks can be executed.

**Task**:
An individual unit of work derived from project requirements. Tasks are downloaded as Markdown, executed locally by a Manager, pushed to GitHub, and evaluated by AI QC/QA nodes.
