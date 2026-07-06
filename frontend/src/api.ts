/// <reference types="vite/client" />
import { apiClient } from "./api/client";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

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
  status: "todo" | "in_progress" | "in_qc" | "in_qa" | "done" | "rejected";
  priority: "low" | "medium" | "high" | "critical";
  assignee?: string;
  estimated_effort: string;
  dependencies: string[];
  evaluation_feedback?: string;
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
  return apiClient(`${API_BASE}/projects`);
};

export const createProject = async (project: Partial<Project>): Promise<Project> => {
  return apiClient(`${API_BASE}/projects`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(project),
  });
};

export const fetchProjectState = async (projectId: string): Promise<Project & ProjectState> => {
  return apiClient(`${API_BASE}/projects/${projectId}`);
};

export const sendMessage = async (projectId: string, content: string): Promise<any> => {
  return apiClient(`${API_BASE}/projects/${projectId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
};

export const triggerAction = async (projectId: string, action: string): Promise<any> => {
  return apiClient(`${API_BASE}/projects/${projectId}/${action}`, {
    method: "POST",
  });
};

export const fetchTasks = async (projectId: string): Promise<KanbanTask[]> => {
  return apiClient(`${API_BASE}/projects/${projectId}/tasks`);
};

export const updateTask = async (projectId: string, taskId: string, payload: { status?: string; assignee?: string }): Promise<any> => {
  return apiClient(`${API_BASE}/projects/${projectId}/tasks/${taskId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
};
