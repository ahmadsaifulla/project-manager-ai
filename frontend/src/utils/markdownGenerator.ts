import { KanbanTask, Project } from "../api";

export function generateTaskMarkdown(task: KanbanTask, project: Project): string {
  const branchName = `feature/${project.id}-${task.id}`;
  const repoUrl = (project as any).github_repo_url || "https://github.com/owner/repo";

  const markdownContent = `---
task_id: ${task.id}
branch: ${branchName}
status: IN_PROGRESS
repo: ${repoUrl}
dependencies: [${task.dependencies?.join(", ") || ""}]
timestamp: ${new Date().toISOString()}
---
# ${task.id}: ${task.title}

## Core Objective
${task.description}

## Acceptance Criteria (QC Checklist)
${(task as any).acceptance_criteria ? (task as any).acceptance_criteria.map((c: string) => `- [ ] ${c}`).join("\n") : "- [ ] Completion verified."}

## Git Instruction
Run: \`git checkout -b ${branchName}\`
`;
  return markdownContent;
}

export function downloadTaskMarkdown(task: KanbanTask, project: Project): void {
  const content = generateTaskMarkdown(task, project);
  const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `T${task.id}.md`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
