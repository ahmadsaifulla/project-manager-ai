# Swarm QA & Testing Constraints

**1. Evidence-Based Verification (Artifacts Mandatory)**
No test is considered "passed" based on agent assertion alone. Every testing phase must generate a verifiable Artifact (e.g., test suite output logs, network payload traces, coverage reports, or browser UI screenshots). 

**2. The Smoke Test Gate**
All testing operations must halt if the critical rendering paths or primary API gateways fail to boot. Sub-agents must not be spawned for deep-dive matrix testing until the core infrastructure is confirmed stable.

**3. Destructive Testing Protocol**
Chaos testing, load testing, and database mutations must only occur in isolated test environments or ephemeral database clones. Never run destructive integration or regression tests against production-state data.

**4. Module Boundaries & Handoffs**
When sub-agents are spawned for specific domains (Frontend, Backend, Orchestrator), they must document API contract mismatches or cross-module integration failures immediately to the Lead Agent.