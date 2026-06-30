const API_BASE = "http://localhost:8000/api";

export interface Project {
  id: string;
  name: string;
  description: string;
  status: "listening" | "reviewing" | "approved" | "in-progress";
  statusLabel?: string;
  sprint?: string;
  progress: number;
  dueDate?: string;
  tags: string[];
  accent_color: string;
}

export interface KanbanTask {
  id: string;
  title: string;
  description: string;
  status: "todo" | "in_progress" | "done";
  priority: "low" | "medium" | "high" | "critical";
  assignee?: string;
  estimated_effort: string;
  dependencies: string[];
}

export interface Message {
  role: "user" | "assistant";
  content: string;
}

export interface ProjectState {
  project_id: string;
  elicitation_phase: string;
  goals_approved: boolean;
  project_goals: string;
  detected_gaps: string[];
  clarification_questions: string[];
  messages: Message[];
  current_focus: string;
  tasks: KanbanTask[];
}

export const fetchProjects = async (): Promise<Project[]> => {
  const res = await fetch(`${API_BASE}/projects`);
  if (!res.ok) throw new Error("Failed to fetch projects");
  return res.json();
};

export const createProject = async (project: Partial<Project>): Promise<Project> => {
  const res = await fetch(`${API_BASE}/projects`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(project),
  });
  if (!res.ok) throw new Error("Failed to create project");
  return res.json();
};

export const fetchProjectState = async (projectId: string): Promise<Project & ProjectState> => {
  const res = await fetch(`${API_BASE}/projects/${projectId}`);
  if (!res.ok) throw new Error("Failed to fetch project state");
  return res.json();
};

export const sendMessage = async (projectId: string, content: string): Promise<any> => {
  const res = await fetch(`${API_BASE}/projects/${projectId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
  if (!res.ok) throw new Error("Failed to send message");
  return res.json();
};

export const triggerAction = async (projectId: string, action: string): Promise<any> => {
  const res = await fetch(`${API_BASE}/projects/${projectId}/${action}`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(`Failed to trigger action ${action}`);
  return res.json();
};
