import { useState, useEffect } from "react";
import { KanbanTask, Project, fetchTasks, updateTask } from "../../api";
import { GitCommitHorizontal, FlaskConical, Loader2, AlertCircle, Download, Play, GitBranch, Settings } from "lucide-react";
import { downloadTaskMarkdown } from "../../utils/markdownGenerator";

export default function TaskBoard({ project }: { project: Project }) {
  const [tasks, setTasks] = useState<KanbanTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [repoUrl, setRepoUrl] = useState(project.github_repo_url || "");
  const [showSettings, setShowSettings] = useState(false);
  const [savingRepo, setSavingRepo] = useState(false);

  const loadTasks = async () => {
    try {
      const data = await fetchTasks(project.id);
      setTasks(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTasks();
  }, [project.id]);

  const handleStatusChange = async (taskId: string, newStatus: string) => {
    if (newStatus === "in_qc" && !repoUrl.trim()) {
      alert("Please configure a target repository in the settings first!");
      setShowSettings(true);
      return;
    }
    
    // Optimistic update
    setTasks(prev => prev.map(t => t.id === taskId ? { ...t, status: newStatus as any } : t));
    try {
      await updateTask(project.id, taskId, { status: newStatus });
      await loadTasks();
    } catch (e) {
      console.error(e);
      await loadTasks(); // Revert on failure
    }
  };

  const handleStartWork = async (task: KanbanTask) => {
    // 1. Fire PATCH to set status to in_progress
    await handleStatusChange(task.id, "in_progress");

    // 2. Download the markdown file
    const projectWithRepo = { ...project, github_repo_url: repoUrl };
    downloadTaskMarkdown(task, projectWithRepo);
  };

  const handleSaveRepo = async () => {
    setSavingRepo(true);
    try {
      const API_BASE = (import.meta as any).env?.VITE_API_URL || "/api";
      await fetch(`${API_BASE}/config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_name: repoUrl }),
      });
      setShowSettings(false);
    } catch (e) {
      console.error(e);
    } finally {
      setSavingRepo(false);
    }
  };

  const columns: { key: string; label: string; color: string; dot: string }[] = [
    { key: "todo", label: "To Do", color: "text-muted-foreground", dot: "bg-muted-foreground/40" },
    { key: "in_progress", label: "In Progress", color: "text-amber-700", dot: "bg-amber-400" },
    { key: "in_qc", label: "In QC", color: "text-blue-700", dot: "bg-blue-400" },
    { key: "in_qa", label: "In QA", color: "text-purple-700", dot: "bg-purple-400" },
    { key: "done", label: "Done", color: "text-green-700", dot: "bg-green-500" },
    { key: "rejected", label: "Rejected", color: "text-red-700", dot: "bg-red-500" },
  ];

  if (loading) return <div className="flex h-full w-full items-center justify-center"><Loader2 className="animate-spin text-primary" size={24} /></div>;

  return (
    <div className="flex flex-col h-full w-full">
      <div className="flex-shrink-0 px-6 py-4 border-b border-border bg-card rounded-t-xl">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-foreground">Task Board</h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              {project.name} {project.sprint ? `· ${project.sprint}` : ""}
            </p>
          </div>
          <button
            onClick={() => setShowSettings(!showSettings)}
            className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground px-2 py-1.5 rounded-lg hover:bg-secondary transition-colors"
          >
            <Settings size={13} />
            Repo Settings
          </button>
        </div>

        {showSettings && (
          <div className="mt-3 pt-3 border-t border-border/60 flex items-center gap-2">
            <GitBranch size={14} className="text-muted-foreground flex-shrink-0" />
            <input
              type="text"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              placeholder="owner/repo (e.g. facebook/react)"
              className="flex-1 text-xs bg-secondary border border-border rounded-lg px-3 py-1.5 text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary/40"
            />
            <button
              onClick={handleSaveRepo}
              disabled={savingRepo}
              className="text-xs font-medium text-primary-foreground bg-primary px-3 py-1.5 rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              {savingRepo ? "Saving..." : "Save"}
            </button>
          </div>
        )}
      </div>
      <div className="flex-1 overflow-x-auto overflow-y-hidden px-6 py-5 scrollbar-hidden">
        <div className="flex gap-4 h-full">
          {columns.map((col) => {
            const colTasks = tasks.filter(t => t.status === col.key);
            return (
              <div key={col.key} className="flex flex-col" style={{ width: "280px", minWidth: "280px" }}>
                <div className="flex items-center gap-2 mb-3">
                  <span className={`w-2 h-2 rounded-full ${col.dot}`} />
                  <span className={`text-xs font-semibold uppercase tracking-wider ${col.color}`}>
                    {col.label}
                  </span>
                  <span className="ml-auto text-xs font-medium text-muted-foreground bg-secondary px-1.5 py-0.5 rounded-full">
                    {colTasks.length}
                  </span>
                </div>

                <div className="flex-1 bg-secondary/40 rounded-xl p-2 overflow-y-auto space-y-2.5 scrollbar-hidden border border-border/40 shadow-inner">
                  {colTasks.length === 0 ? (
                     <div className="flex items-center justify-center h-16 text-xs text-muted-foreground/50">No tasks</div>
                  ) : (
                    colTasks.map((task) => (
                      <KanbanTaskCard
                        key={task.id}
                        task={task}
                        project={project}
                        repoUrl={repoUrl}
                        onStatusChange={(status) => handleStatusChange(task.id, status)}
                        onStartWork={() => handleStartWork(task)}
                      />
                    ))
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function KanbanTaskCard({
  task,
  project,
  repoUrl,
  onStatusChange,
  onStartWork,
}: {
  task: KanbanTask;
  project: Project;
  repoUrl: string;
  onStatusChange: (s: string) => void;
  onStartWork: () => void;
}) {
  const PRIORITY_CONFIG: Record<string, {label: string, classes: string}> = {
    critical: { label: "Critical", classes: "bg-red-100 text-red-700 border-red-200" },
    high: { label: "High", classes: "bg-orange-50 text-orange-600 border-orange-100" },
    medium: { label: "Med", classes: "bg-amber-50 text-amber-600 border-amber-100" },
    low: { label: "Low", classes: "bg-green-50 text-green-600 border-green-100" },
  };

  const pc = PRIORITY_CONFIG[task.priority] || PRIORITY_CONFIG.medium;
  const isQcDone = task.status === "in_qc" || task.status === "in_qa";
  const targetBranch = `feature/${task.id}`;

  return (
    <div
      className={`bg-card border rounded-xl p-3.5 flex flex-col gap-3 transition-all shadow-sm ${isQcDone ? "border-blue-200 bg-blue-50/40" : task.status === "rejected" ? "border-red-200 bg-red-50/40" : "border-border hover:shadow-md hover:-translate-y-0.5"}`}
    >
      {/* Header: Task ID + Title */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[11px] font-bold px-2 py-0.5 rounded-md bg-primary/10 text-primary font-mono tracking-tight">
              {task.id}
            </span>
            <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${pc.classes}`}>
              {pc.label}
            </span>
          </div>
          <p className="text-xs font-semibold text-foreground leading-snug">{task.title}</p>
        </div>
      </div>

      {/* Branch Tag */}
      <div className="flex items-center gap-1.5">
        <GitBranch size={10} className="text-muted-foreground flex-shrink-0" />
        <span className="text-[10px] font-mono text-muted-foreground truncate bg-secondary px-1.5 py-0.5 rounded-md border border-border/50">
          {targetBranch}
        </span>
      </div>

      {/* Description */}
      <p className="text-[11px] text-muted-foreground leading-relaxed whitespace-pre-wrap line-clamp-3">{task.description}</p>

      {/* QC Feedback */}
      {task.evaluation_feedback && (
        <div className="text-[10px] bg-red-50 text-red-700 p-2 rounded-lg border border-red-100 mt-1">
           <strong className="flex gap-1 items-center mb-1"><AlertCircle size={10} /> QC Feedback:</strong>
           {task.evaluation_feedback}
        </div>
      )}

      {/* Actions Footer */}
      <div className="flex items-center justify-between pt-2 border-t border-border/60">
        <div className="flex items-center gap-1.5">
          <div
            className="w-5 h-5 rounded-full flex items-center justify-center text-[9px] font-bold text-white shadow-sm bg-primary"
          >
            {task.assignee ? task.assignee.charAt(0).toUpperCase() : "?"}
          </div>
        </div>

        {task.status === "todo" ? (
          <button
            onClick={onStartWork}
            className="flex items-center gap-1.5 text-[10px] font-semibold text-white bg-gradient-to-r from-amber-500 to-orange-500 px-3 py-1.5 rounded-lg hover:from-amber-600 hover:to-orange-600 transition-all shadow-sm active:scale-95"
          >
            <Play size={10} fill="currentColor" />
            Start Work
          </button>
        ) : task.status === "in_progress" || task.status === "rejected" ? (
          <div className="flex items-center gap-1.5">
            <button
              onClick={() => {
                const projectWithRepo = { ...project, github_repo_url: repoUrl };
                downloadTaskMarkdown(task, projectWithRepo);
              }}
              className="flex items-center gap-1 text-[10px] font-medium text-muted-foreground hover:text-foreground px-1.5 py-1 rounded-lg hover:bg-secondary transition-colors"
              title="Download task brief"
            >
              <Download size={10} />
            </button>
            <button
              onClick={() => onStatusChange("in_qc")}
              className="flex items-center gap-1 text-[10px] font-medium text-primary border border-primary/30 bg-accent hover:bg-primary hover:text-primary-foreground px-2 py-1 rounded-lg transition-all shadow-sm"
            >
              <GitCommitHorizontal size={10} />
              Handover to QC
            </button>
          </div>
        ) : task.status === "in_qc" ? (
          <span className="flex items-center gap-1 text-[10px] font-medium text-blue-600 bg-blue-100 px-2 py-1 rounded-lg border border-blue-200">
            <FlaskConical size={10} />
            In QC Review
          </span>
        ) : task.status === "in_qa" ? (
           <button
            onClick={() => onStatusChange("done")}
            className="flex items-center gap-1 text-[10px] font-medium text-green-600 bg-green-50 px-2 py-1 rounded-lg hover:bg-green-100 transition-all border border-green-200 shadow-sm"
          >
            Approve QA
          </button>
        ) : (
          <span className="text-[10px] font-medium text-muted-foreground uppercase bg-secondary px-2 py-1 rounded-lg">{task.status.replace("_", " ")}</span>
        )}
      </div>
    </div>
  );
}
