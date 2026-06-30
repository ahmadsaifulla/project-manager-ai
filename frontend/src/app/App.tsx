import { useState, useRef, useEffect } from "react";
import {
  Send,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  ChevronRight,
  Plus,
  Loader2,
  Bot,
  User,
  Kanban,
  MessageSquare,
  Circle,
  ArrowRight,
  ArrowLeft,
  GitCommitHorizontal,
  FlaskConical,
  Users,
  Calendar,
  ChevronDown,
  Layers,
} from "lucide-react";

// ─── Types ────────────────────────────────────────────────────────────────────

type Phase = "listening" | "processing" | "reviewing" | "approved";
type ActiveTab = "chat" | "board";
type AppView = "dashboard" | "project";

interface Message {
  id: string;
  role: "user" | "ai";
  content: string;
  timestamp: Date;
}

interface KanbanTask {
  id: string;
  title: string;
  description: string;
  assignee?: string;
  priority: "high" | "medium" | "low" | "critical";
  status: "todo" | "in_progress" | "done";
  estimated_effort?: string;
}

interface KanbanBoard {
  todo: KanbanTask[];
  inprogress: KanbanTask[];
  done: KanbanTask[];
}

interface Project {
  id: string;
  name: string;
  description: string;
  status: "listening" | "reviewing" | "approved" | "in-progress";
  statusLabel: string;
  sprint: string;
  team: { initials: string; color: string }[];
  progress: number;
  dueDate: string;
  tags: string[];
  accentColor: string;
  board: KanbanBoard;
}

// ─── Seed data ────────────────────────────────────────────────────────────────

const PROJECTS: Project[] = [
  {
    id: "analytics-portal",
    name: "Analytics Portal",
    description:
      "Customer-facing usage analytics with Okta SSO, real-time Kafka-driven alerts, and CSV/PDF export.",
    status: "approved",
    statusLabel: "Approved",
    sprint: "Sprint 2 / 3",
    team: [
      { initials: "SR", color: "#5B4EFF" },
      { initials: "MK", color: "#0EA5E9" },
      { initials: "JP", color: "#10B981" },
    ],
    progress: 58,
    dueDate: "Aug 14, 2026",
    tags: ["SaaS", "Data"],
    accentColor: "#5B4EFF",
    board: {
      todo: [
        { id: "t1", title: "Define API schema for usage metrics", description: "OpenAPI spec covering all drill-down endpoints", assigneeInitials: "JP", assigneeColor: "#10B981", priority: "high", tag: "Backend" },
        { id: "t2", title: "Set up Okta sandbox environment", description: "Dev tenant config + SAML metadata exchange", assigneeInitials: "MK", assigneeColor: "#0EA5E9", priority: "medium", tag: "Auth" },
        { id: "t3", title: "CSV export service", description: "Streaming export for large datasets", assigneeInitials: "SR", assigneeColor: "#5B4EFF", priority: "medium", tag: "Backend" },
      ],
      inprogress: [
        { id: "t4", title: "Alert engine — threshold evaluation", description: "Event-driven trigger with <5 min SLA", assigneeInitials: "SR", assigneeColor: "#5B4EFF", priority: "high", tag: "Core" },
        { id: "t5", title: "Postgres query layer + row-level security", description: "Multi-tenant isolation via RLS policies", assigneeInitials: "JP", assigneeColor: "#10B981", priority: "high", tag: "Database" },
      ],
      done: [
        { id: "t6", title: "Stakeholder requirements sign-off", description: "All three business units confirmed scope", assigneeInitials: "MK", assigneeColor: "#0EA5E9", priority: "low", tag: "Planning" },
        { id: "t7", title: "Architecture decision record", description: "Event-driven chosen over polling — rationale documented", assigneeInitials: "SR", assigneeColor: "#5B4EFF", priority: "medium", tag: "Docs" },
      ],
    },
  },
  {
    id: "mobile-redesign",
    name: "Mobile App Redesign",
    description:
      "Full UX overhaul of the iOS and Android apps targeting a 40% reduction in support tickets.",
    status: "reviewing",
    statusLabel: "Under Review",
    sprint: "Sprint 1 / 4",
    team: [
      { initials: "AL", color: "#F59E0B" },
      { initials: "TS", color: "#EF4444" },
    ],
    progress: 22,
    dueDate: "Oct 3, 2026",
    tags: ["Mobile", "UX"],
    accentColor: "#F59E0B",
    board: {
      todo: [
        { id: "m1", title: "User interview synthesis", description: "Condense 24 interviews into theme clusters", assigneeInitials: "AL", assigneeColor: "#F59E0B", priority: "high", tag: "Research" },
        { id: "m2", title: "Navigation structure redesign", description: "Flatten the 4-level tab hierarchy", assigneeInitials: "TS", assigneeColor: "#EF4444", priority: "high", tag: "UX" },
        { id: "m3", title: "Onboarding flow v2 prototype", description: "3-screen reduced onboarding", assigneeInitials: "AL", assigneeColor: "#F59E0B", priority: "medium", tag: "UX" },
      ],
      inprogress: [
        { id: "m4", title: "Component library audit", description: "Map existing components against new design system", assigneeInitials: "TS", assigneeColor: "#EF4444", priority: "medium", tag: "Design System" },
      ],
      done: [
        { id: "m5", title: "Competitive analysis report", description: "Benchmarked 6 direct competitors on 14 UX dimensions", assigneeInitials: "AL", assigneeColor: "#F59E0B", priority: "low", tag: "Research" },
      ],
    },
  },
  {
    id: "payment-gateway",
    name: "Payment Gateway Integration",
    description:
      "Replace legacy Braintree setup with Stripe Connect for marketplace payouts and subscription billing.",
    status: "approved",
    statusLabel: "Approved",
    sprint: "Sprint 3 / 3",
    team: [
      { initials: "DW", color: "#8B5CF6" },
      { initials: "CF", color: "#06B6D4" },
      { initials: "RN", color: "#10B981" },
    ],
    progress: 84,
    dueDate: "Jul 18, 2026",
    tags: ["Payments", "Backend"],
    accentColor: "#8B5CF6",
    board: {
      todo: [
        { id: "p1", title: "PCI DSS compliance checklist", description: "Final SAQ-A review before go-live", assigneeInitials: "CF", assigneeColor: "#06B6D4", priority: "high", tag: "Compliance" },
      ],
      inprogress: [
        { id: "p2", title: "Stripe Connect webhook handler", description: "account.updated + payout.paid events", assigneeInitials: "DW", assigneeColor: "#8B5CF6", priority: "high", tag: "Backend" },
        { id: "p3", title: "Subscription billing migration script", description: "Move 3,400 active subs from Braintree", assigneeInitials: "RN", assigneeColor: "#10B981", priority: "high", tag: "Migration" },
      ],
      done: [
        { id: "p4", title: "Stripe SDK integration", description: "Payment intent flow + 3DS2 handling", assigneeInitials: "DW", assigneeColor: "#8B5CF6", priority: "high", tag: "Backend" },
        { id: "p5", title: "Marketplace payout routing", description: "Split payments with configurable fee retention", assigneeInitials: "RN", assigneeColor: "#10B981", priority: "medium", tag: "Core" },
        { id: "p6", title: "Staging environment smoke tests", description: "All 47 test cases passing on test clocks", assigneeInitials: "CF", assigneeColor: "#06B6D4", priority: "medium", tag: "QA" },
      ],
    },
  },
  {
    id: "hr-portal",
    name: "Internal HR Portal",
    description:
      "Self-service HR hub for leave requests, org chart, payslips, and onboarding task tracking.",
    status: "listening",
    statusLabel: "Requirements",
    sprint: "Pre-sprint",
    team: [
      { initials: "NB", color: "#EC4899" },
    ],
    progress: 8,
    dueDate: "Nov 28, 2026",
    tags: ["Internal", "HR"],
    accentColor: "#EC4899",
    board: {
      todo: [
        { id: "h1", title: "Gather HR admin requirements", description: "Interview 4 HR stakeholders", assigneeInitials: "NB", assigneeColor: "#EC4899", priority: "high", tag: "Discovery" },
      ],
      inprogress: [],
      done: [],
    },
  },
  {
    id: "ai-chatbot",
    name: "AI Support Chatbot",
    description:
      "LLM-powered tier-1 support bot with RAG over the knowledge base, handoff to human agents.",
    status: "approved",
    statusLabel: "Approved",
    sprint: "Sprint 1 / 2",
    team: [
      { initials: "LH", color: "#5B4EFF" },
      { initials: "PV", color: "#F59E0B" },
    ],
    progress: 41,
    dueDate: "Sep 5, 2026",
    tags: ["AI", "Support"],
    accentColor: "#5B4EFF",
    board: {
      todo: [
        { id: "a1", title: "Knowledge base chunking strategy", description: "Evaluate fixed vs semantic chunking on support docs", assigneeInitials: "PV", assigneeColor: "#F59E0B", priority: "high", tag: "RAG" },
        { id: "a2", title: "Human handoff escalation rules", description: "Define confidence threshold triggers", assigneeInitials: "LH", assigneeColor: "#5B4EFF", priority: "medium", tag: "Logic" },
      ],
      inprogress: [
        { id: "a3", title: "Vector store setup (pgvector)", description: "Embedding pipeline for 12k KB articles", assigneeInitials: "PV", assigneeColor: "#F59E0B", priority: "high", tag: "Infrastructure" },
        { id: "a4", title: "Chat widget front-end", description: "Embeddable React widget with streaming response", assigneeInitials: "LH", assigneeColor: "#5B4EFF", priority: "medium", tag: "Frontend" },
      ],
      done: [
        { id: "a5", title: "LLM provider evaluation", description: "Claude 3.5 Sonnet selected over GPT-4o for latency/cost", assigneeInitials: "LH", assigneeColor: "#5B4EFF", priority: "medium", tag: "Research" },
      ],
    },
  },
  {
    id: "data-warehouse",
    name: "Data Warehouse Migration",
    description:
      "Migrate 8TB from on-prem Redshift to Snowflake with zero-downtime cutover and dbt model rewrite.",
    status: "reviewing",
    statusLabel: "Under Review",
    sprint: "Sprint 2 / 5",
    team: [
      { initials: "KL", color: "#06B6D4" },
      { initials: "YM", color: "#10B981" },
      { initials: "BT", color: "#8B5CF6" },
    ],
    progress: 33,
    dueDate: "Dec 12, 2026",
    tags: ["Data", "Infrastructure"],
    accentColor: "#06B6D4",
    board: {
      todo: [
        { id: "dw1", title: "dbt model rewrite — mart layer", description: "Rewrite 34 mart models for Snowflake SQL dialect", assigneeInitials: "YM", assigneeColor: "#10B981", priority: "high", tag: "dbt" },
        { id: "dw2", title: "Cutover runbook", description: "Step-by-step zero-downtime migration plan", assigneeInitials: "KL", assigneeColor: "#06B6D4", priority: "high", tag: "Ops" },
      ],
      inprogress: [
        { id: "dw3", title: "Snowflake account + warehouse sizing", description: "Right-size compute for 3 tiers of workload", assigneeInitials: "BT", assigneeColor: "#8B5CF6", priority: "medium", tag: "Infrastructure" },
        { id: "dw4", title: "Historical data backfill validation", description: "Row-count and checksum comparison for 6-month window", assigneeInitials: "KL", assigneeColor: "#06B6D4", priority: "high", tag: "Validation" },
      ],
      done: [
        { id: "dw5", title: "Redshift schema export", description: "All 147 tables exported and mapped to Snowflake types", assigneeInitials: "YM", assigneeColor: "#10B981", priority: "medium", tag: "Migration" },
        { id: "dw6", title: "Snowflake POC cost model", description: "Projected 31% cost reduction vs. Redshift RA3", assigneeInitials: "BT", assigneeColor: "#8B5CF6", priority: "low", tag: "Planning" },
      ],
    },
  },
];

const INITIAL_MESSAGES: Message[] = [
  {
    id: "1",
    role: "ai",
    content:
      "Hi, I'm your AI Project Coordinator. Describe your project and I'll help you map requirements, identify risks, and structure a delivery plan. What are you building?",
    timestamp: new Date(Date.now() - 9 * 60000),
  },
  {
    id: "2",
    role: "user",
    content:
      "We need a customer-facing analytics portal for our SaaS product. It should let clients drill into their usage data, export reports, and set up email alerts when thresholds are crossed.",
    timestamp: new Date(Date.now() - 7 * 60000),
  },
  {
    id: "3",
    role: "ai",
    content:
      "Understood. A few clarifying questions: (1) Will clients authenticate via your existing SSO or a separate login? (2) What data sources feed into the usage metrics — your own event pipeline, or a third-party like Segment? (3) Do alerts need to be real-time or is daily digest sufficient to start?",
    timestamp: new Date(Date.now() - 6 * 60000),
  },
  {
    id: "4",
    role: "user",
    content:
      "SSO via Okta. Data comes from our internal Kafka pipeline already processed into Postgres. Alerts should fire within 5 minutes of a threshold being crossed — real-time matters here.",
    timestamp: new Date(Date.now() - 4 * 60000),
  },
  {
    id: "5",
    role: "ai",
    content:
      "Good — that shapes the architecture considerably. The <5-minute alert requirement means we'll need a background polling or event-driven trigger rather than a batch job. I'm mapping out the requirement set now. Anything else before I run a full analysis?",
    timestamp: new Date(Date.now() - 2 * 60000),
  },
];



// ─── Helpers ─────────────────────────────────────────────────────────────────

function formatTime(d: Date) {
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

const PRIORITY_CONFIG = {
  high: { label: "High", classes: "bg-red-50 text-red-600 border-red-100" },
  medium: { label: "Med", classes: "bg-amber-50 text-amber-600 border-amber-100" },
  low: { label: "Low", classes: "bg-green-50 text-green-600 border-green-100" },
};

const STATUS_CONFIG: Record<Project["status"], { dot: string; label: string; bg: string; text: string }> = {
  approved: { dot: "bg-green-500", label: "Approved", bg: "bg-green-50", text: "text-green-700" },
  reviewing: { dot: "bg-amber-400", label: "Under Review", bg: "bg-amber-50", text: "text-amber-700" },
  listening: { dot: "bg-primary", label: "Requirements", bg: "bg-accent", text: "text-accent-foreground" },
  "in-progress": { dot: "bg-blue-500", label: "In Progress", bg: "bg-blue-50", text: "text-blue-700" },
};

// ─── Project Dashboard ────────────────────────────────────────────────────────

function ProjectDashboard({ projects, onSelect, onCreate }: { projects: Project[]; onSelect: (p: Project) => void; onCreate: () => void }) {
  const [filter, setFilter] = useState<"all" | Project["status"]>("all");

  const filtered = filter === "all" ? projects : projects.filter((p) => p.status === filter);

  const filterOptions: { key: "all" | Project["status"]; label: string }[] = [
    { key: "all", label: "All Projects" },
    { key: "approved", label: "Approved" },
    { key: "reviewing", label: "Under Review" },
    { key: "listening", label: "Requirements" },
  ];

  return (
    <div className="flex-1 flex flex-col bg-background overflow-hidden">
      {/* Dashboard header */}
      <div className="flex-shrink-0 px-8 pt-8 pb-5 border-b border-border bg-card">
        <div className="flex items-end justify-between">
          <div>
            <h1 className="text-xl font-semibold text-foreground tracking-tight">
              Project Portfolio
            </h1>
            <p className="text-sm text-muted-foreground mt-0.5">
              {projects.length} active projects · Select one to open the workspace
            </p>
          </div>
          <button onClick={onCreate} className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground text-sm font-medium transition-all hover:bg-primary/90 active:scale-[0.98]">
            <Plus size={14} />
            New Project
          </button>
        </div>

        {/* Filter pills */}
        <div className="flex items-center gap-1.5 mt-5">
          {filterOptions.map((opt) => (
            <button
              key={opt.key}
              onClick={() => setFilter(opt.key)}
              className={`px-3.5 py-1.5 rounded-full text-xs font-medium transition-all ${filter === opt.key
                ? "bg-primary text-primary-foreground"
                : "bg-secondary text-muted-foreground hover:text-foreground"
                }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Project grid */}
      <div className="flex-1 overflow-y-auto px-8 py-6 scrollbar-hidden">
        <div className="grid grid-cols-1 gap-4" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))" }}>
          {filtered.map((project) => {
            const sc = STATUS_CONFIG[project.status];
            return (
              <button
                key={project.id}
                onClick={() => onSelect(project)}
                className="text-left bg-card border border-border rounded-2xl p-5 transition-all hover:shadow-md hover:-translate-y-0.5 hover:border-primary/20 group"
              >
                {/* Top row */}
                <div className="flex items-start justify-between mb-4">
                  <div
                    className="w-10 h-10 rounded-xl flex items-center justify-center border border-background/5"
                    style={{ backgroundColor: project.accent_color + "18" }}
                  >
                    <Layers size={16} style={{ color: project.accent_color }} />
                  </div>
                  <span className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${sc.bg} ${sc.text}`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${sc.dot}`} />
                    {sc.label}
                  </span>
                </div>

                <h3 className="text-sm font-semibold text-foreground mb-1 group-hover:text-primary transition-colors">
                  {project.name}
                </h3>
                <p className="text-xs text-muted-foreground leading-relaxed mb-4 line-clamp-2">
                  {project.description}
                </p>

                {/* Progress bar */}
                <div className="mb-4">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-xs text-muted-foreground">{project.sprint}</span>
                    <span className="text-xs font-medium text-foreground">{project.progress}%</span>
                  </div>
                  <div className="h-1.5 w-full bg-secondary rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-500 ease-out"
                      style={{ width: `${project.progress}%`, backgroundColor: project.accent_color }}
                    />
                  </div>
                </div>

                {/* Footer */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1">
                    {/* Team avatars removed since backend doesn't supply team */}
                  </div>
                  <div className="flex items-center gap-1 text-xs text-muted-foreground">
                    <Calendar size={11} />
                    {project.dueDate}
                  </div>
                </div>

                {/* Tags */}
                <div className="flex gap-1.5 mt-3 flex-wrap">
                  {project.tags.map((tag) => (
                    <span
                      key={tag}
                      className="px-2 py-0.5 rounded-full bg-secondary text-xs text-muted-foreground"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ─── Kanban Board ─────────────────────────────────────────────────────────────

function KanbanTaskCard({
  task,
  qcDone,
  onQCHandover,
}: {
  task: KanbanTask;
  qcDone: boolean;
  onQCHandover: () => void;
}) {
  const pc = PRIORITY_CONFIG[task.priority];

  return (
    <div
      className={`bg-card border rounded-xl p-3.5 flex flex-col gap-3 transition-all ${qcDone ? "border-green-200 bg-green-50/40" : "border-border hover:shadow-sm"
        }`}
    >
      {/* Tag + priority */}
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-secondary text-muted-foreground">
          {task.tag}
        </span>
        <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${pc.classes}`}>
          {pc.label}
        </span>
      </div>

      {/* Title + description */}
      <div>
        <p className="text-xs font-semibold text-foreground leading-snug">{task.title}</p>
        <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">{task.description}</p>
      </div>

      {/* Footer: assignee + QC button */}
      <div className="flex items-center justify-between pt-1 border-t border-border/60">
        <div className="flex items-center gap-1.5">
          <div
            className="w-5 h-5 rounded-full flex items-center justify-center text-[9px] font-bold text-white shadow-sm"
            style={{ backgroundColor: "#8B5CF6" }}
          >
            {task.assignee ? task.assignee.charAt(0).toUpperCase() : "?"}
          </div>
          <span className="text-[10px] text-muted-foreground">{task.assignee || "Unassigned"}</span>
        </div>

        {qcDone ? (
          <span className="flex items-center gap-1 text-[10px] font-medium text-green-600 bg-green-100 px-2 py-1 rounded-lg">
            <FlaskConical size={10} />
            In QC Review
          </span>
        ) : (
          <button
            onClick={onQCHandover}
            className="flex items-center gap-1 text-[10px] font-medium text-primary border border-primary/30 bg-accent hover:bg-primary hover:text-primary-foreground px-2 py-1 rounded-lg transition-all"
          >
            <GitCommitHorizontal size={10} />
            Code Pushed: Handover to QC
          </button>
        )}
      </div>
    </div>
  );
}

function KanbanBoardView({ project, tasks }: { project: Project, tasks: KanbanTask[] }) {
  const [qcHandedOver, setQcHandedOver] = useState<Set<string>>(new Set());

  function toggleQC(taskId: string) {
    setQcHandedOver((prev) => {
      const next = new Set(prev);
      if (next.has(taskId)) next.delete(taskId);
      else next.add(taskId);
      return next;
    });
  }

  const columns: { key: string; label: string; color: string; dot: string }[] = [
    { key: "todo", label: "To Do", color: "text-muted-foreground", dot: "bg-muted-foreground/40" },
    { key: "in_progress", label: "In Progress", color: "text-amber-700", dot: "bg-amber-400" },
    { key: "done", label: "Done", color: "text-green-700", dot: "bg-green-500" },
  ];

  const getTasksByStatus = (status: string) => tasks.filter(t => t.status === status);

  return (
    <div className="flex flex-col h-full">
      <div className="flex-shrink-0 px-6 py-4 border-b border-border bg-card">
        <h2 className="text-sm font-semibold text-foreground">Task Board</h2>
        <p className="text-xs text-muted-foreground mt-0.5">
          {project.name} {project.sprint ? `· ${project.sprint}` : ""}
        </p>
      </div>
      <div className="flex-1 overflow-x-auto overflow-y-hidden px-6 py-5 scrollbar-hidden">
        <div className="flex gap-4 h-full" style={{ minWidth: "700px" }}>
          {columns.map((col) => {
            const colTasks = getTasksByStatus(col.key);
            return (
              <div key={col.key} className="flex flex-col" style={{ width: "280px", minWidth: "280px" }}>
                {/* Column header */}
                <div className="flex items-center gap-2 mb-3">
                  <span className={`w-2 h-2 rounded-full ${col.dot}`} />
                  <span className={`text-xs font-semibold uppercase tracking-wider ${col.color}`}>
                    {col.label}
                  </span>
                  <span className="ml-auto text-xs font-medium text-muted-foreground bg-secondary px-1.5 py-0.5 rounded-full">
                    {tasks.length}
                  </span>
                </div>

                {/* Column bg */}
                <div className="flex-1 bg-secondary/40 rounded-xl p-2 overflow-y-auto space-y-2.5 scrollbar-hidden">
                  {colTasks.length === 0 ? (
                    <div className="flex items-center justify-center h-16 text-xs text-muted-foreground/50">
                      No tasks
                    </div>
                  ) : (
                    colTasks.map((task) => (
                      <KanbanTaskCard
                        key={task.id}
                        task={task}
                        qcDone={qcHandedOver.has(task.id)}
                        onQCHandover={() => toggleQC(task.id)}
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

// ─── Chat sub-components ──────────────────────────────────────────────────────

function ChatBubble({ msg }: { msg: Message | any }) {
  const isAI = msg.role === "ai" || msg.role === "assistant";
  return (
    <div className={`flex gap-3 ${isAI ? "" : "flex-row-reverse"}`}>
      <div
        className={`flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center mt-0.5 ${isAI ? "bg-primary/10 text-primary" : "bg-secondary text-muted-foreground"
          }`}
      >
        {isAI ? <Bot size={14} /> : <User size={14} />}
      </div>
      <div className={`max-w-[78%] ${isAI ? "" : "items-end flex flex-col"}`}>
        <div
          className={`px-4 py-3 rounded-2xl text-sm leading-relaxed ${isAI
            ? "bg-card text-card-foreground border border-border rounded-tl-sm"
            : "bg-primary text-primary-foreground rounded-tr-sm"
            }`}
        >
          {msg.content}
        </div>
      </div>
    </div>
  );
}

function ThinkingIndicator() {
  return (
    <div className="flex gap-3 animate-pulse opacity-80 mt-2">
      <div className="flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center bg-primary/10 text-primary">
        <Bot size={14} />
      </div>
      <div className="bg-card border border-border rounded-2xl rounded-tl-sm px-4 py-3 flex items-center gap-2">
        <span className="text-xs text-muted-foreground font-medium">Architect AI is thinking...</span>
      </div>
    </div>
  );
}

function ProcessingDots() {
  return (
    <div className="flex gap-3">
      <div className="flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center bg-primary/10 text-primary">
        <Bot size={14} />
      </div>
      <div className="bg-card border border-border rounded-2xl rounded-tl-sm px-4 py-3 flex items-center gap-1.5">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="w-1.5 h-1.5 rounded-full bg-primary/40 inline-block"
            style={{ animation: `pmBounce 1.2s ease-in-out ${i * 0.2}s infinite` }}
          />
        ))}
      </div>
    </div>
  );
}

function IdlePanel() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center gap-5 px-8">
      <div className="w-14 h-14 rounded-2xl bg-accent flex items-center justify-center">
        <Sparkles size={24} className="text-accent-foreground" />
      </div>
      <div className="text-center">
        <p className="text-sm font-medium text-foreground mb-1">
          Listening and mapping your project requirements...
        </p>
        <p className="text-xs text-muted-foreground leading-relaxed max-w-[220px]">
          Continue describing your project. I&apos;ll structure everything once you trigger analysis.
        </p>
      </div>
      <div className="w-full max-w-[200px] space-y-2 mt-2">
        {["Authentication model", "Data sources", "Alert latency"].map((item, i) => (
          <div key={i} className="flex items-center gap-2.5 px-3 py-2 rounded-lg bg-secondary/60">
            <Circle size={6} className="text-primary fill-primary flex-shrink-0" />
            <span className="text-xs text-muted-foreground">{item}</span>
            <span className="ml-auto text-xs font-medium text-green-600">✓</span>
          </div>
        ))}
        <div className="flex items-center gap-2.5 px-3 py-2 rounded-lg bg-secondary/60">
          <Circle size={6} className="text-muted-foreground fill-muted-foreground/30 flex-shrink-0" />
          <span className="text-xs text-muted-foreground">Mobile scope</span>
          <span className="ml-auto text-xs text-muted-foreground/50">—</span>
        </div>
      </div>
    </div>
  );
}

function ReviewPanel({ projectState, onApprove, onModify }: { projectState: ProjectState; onApprove: () => void; onModify: () => void }) {
  return (
    <div className="flex flex-col h-full">
      <div className="px-5 py-4 border-b border-border">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-amber-400" />
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Under Review</span>
        </div>
        <h2 className="text-sm font-semibold text-foreground mt-1">Requirements Analysis</h2>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5 scrollbar-hidden">
        <div>
          <div className="flex items-center gap-1.5 mb-2.5">
            <CheckCircle2 size={13} className="text-green-500" />
            <span className="text-xs font-semibold uppercase tracking-wider text-green-700">Project Goals</span>
          </div>
          <p className="text-xs text-foreground leading-relaxed whitespace-pre-wrap">{projectState.project_goals}</p>
        </div>

        {projectState.detected_gaps && projectState.detected_gaps.length > 0 && (
          <div>
            <div className="flex items-center gap-1.5 mb-2.5">
              <AlertCircle size={13} className="text-amber-500" />
              <span className="text-xs font-semibold uppercase tracking-wider text-amber-700">Detected Gaps</span>
            </div>
            <ul className="space-y-2">
              {projectState.detected_gaps.map((item, i) => (
                <li key={i} className="flex items-start gap-2 text-xs text-foreground leading-relaxed px-3 py-2 rounded-lg bg-amber-50 border border-amber-100">
                  <AlertCircle size={11} className="text-amber-400 flex-shrink-0 mt-0.5" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
        )}

        {projectState.clarification_questions && projectState.clarification_questions.length > 0 && (
          <div>
            <div className="flex items-center gap-1.5 mb-2.5">
              <ArrowRight size={13} className="text-primary" />
              <span className="text-xs font-semibold uppercase tracking-wider text-primary">Clarification Questions</span>
            </div>
            <ul className="space-y-2">
              {projectState.clarification_questions.map((item, i) => (
                <li key={i} className="flex items-start gap-2 text-xs text-foreground leading-relaxed">
                  <ChevronRight size={12} className="text-primary flex-shrink-0 mt-0.5" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div className="px-5 py-4 border-t border-border space-y-2.5">
        <button
          onClick={onApprove}
          className="w-full py-2.5 px-4 rounded-xl bg-primary text-primary-foreground text-sm font-medium transition-all hover:bg-primary/90 active:scale-[0.98]"
        >
          Approve Requirements &amp; Goals
        </button>
        <button
          onClick={onModify}
          className="w-full py-2.5 px-4 rounded-xl border border-border text-sm font-medium text-foreground transition-all hover:bg-secondary active:scale-[0.98]"
        >
          That&apos;s not what I wanted, modify
        </button>
      </div>
    </div>
  );
}

function ApprovedPanel({ projectState, onAddMore }: { projectState: ProjectState; onAddMore: () => void }) {
  return (
    <div className="flex flex-col h-full">
      <div className="px-5 py-4 border-b border-border flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-green-500" />
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Approved &amp; Locked</span>
          </div>
          <h2 className="text-sm font-semibold text-foreground mt-1">Project Approved</h2>
        </div>
        <button
          onClick={onAddMore}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-primary/30 bg-accent text-accent-foreground text-xs font-medium transition-all hover:bg-accent/80"
        >
          <Plus size={12} />
          Add Requirements
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-4 scrollbar-hidden space-y-5">
        <div className="rounded-xl bg-green-50 border border-green-100 px-4 py-3">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle2 size={14} className="text-green-600" />
            <span className="text-xs font-semibold text-green-700">Scope Confirmed</span>
          </div>
          <p className="text-xs text-green-900/80 leading-relaxed whitespace-pre-wrap">{projectState.project_goals}</p>
        </div>

        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">Tasks Breakdown</h3>
          <ul className="space-y-2">
            {projectState.tasks && projectState.tasks.map((task, i) => (
              <li key={i} className="flex items-start gap-2 text-xs text-foreground leading-relaxed">
                <ChevronRight size={12} className="text-green-400 flex-shrink-0 mt-0.5" />
                {task.title}
              </li>
            ))}
          </ul>
        </div>

        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">Delivery Roadmap</h3>
          <div className="space-y-2.5">
            {projectState.sprints && projectState.sprints.map((sprint) => (
              <div key={sprint.id} className="flex items-start gap-3 px-3.5 py-3 rounded-xl bg-secondary/60 border border-border">
                <div className="w-6 h-6 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <span className="text-xs font-semibold text-primary">{sprint.id}</span>
                </div>
                <div>
                  <div className="text-xs font-semibold text-foreground">{sprint.label}</div>
                  <div className="text-xs text-muted-foreground mt-0.5">{sprint.focus}</div>
                </div>
              </div>
            ))}
          </div>
        </div>


      </div>
    </div>
  );
}

// ─── Project Workspace ────────────────────────────────────────────────────────

function ProjectWorkspace({ project, onBack }: { project: Project; onBack: () => void }) {
  const [projectState, setProjectState] = useState<ProjectState | null>(null);
  const [isThinking, setIsThinking] = useState(false);
  const [loading, setLoading] = useState(true);
  const [input, setInput] = useState("");
  const feedRef = useRef<HTMLDivElement>(null);

  const fetchState = async () => {
    try {
      const state = await import("../api").then(api => api.fetchProjectState(project.id));
      setProjectState(state);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchState();
  }, [project.id]);

  const phase = projectState?.elicitation_phase as Phase || "listening";
  const messages = projectState?.messages || [];
  const sidePanelVisible = phase === "reviewing" || phase === "approved";
  const [activeTab, setActiveTab] = useState<ActiveTab>("chat");

  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight;
    }
  }, [messages, phase]);

  async function sendMessage() {
    if (!input.trim() || (phase !== "listening" && projectState?.elicitation_phase !== "stress_testing")) return;
    const text = input.trim();
    setInput("");

    const optimisticMsg: Message = {
      id: `temp_${Date.now()}`,
      role: "user",
      content: text,
      timestamp: new Date()
    };
    setProjectState(prev => prev ? {
      ...prev,
      messages: [...(prev.messages || []), optimisticMsg]
    } : null);

    setIsThinking(true);
    try {
      await import("../api").then(api => api.sendMessage(project.id, text));
      await fetchState();
    } finally {
      setIsThinking(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  }

  async function beginAnalysis() {
    await import("../api").then(api => api.triggerAction(project.id, "finish-sharing"));
    await fetchState();
  }

  async function handleApprove() {
    await import("../api").then(api => api.triggerAction(project.id, "approve-goals"));
    await fetchState();
  }

  async function handleModify() {
    await import("../api").then(api => api.triggerAction(project.id, "reject-goals"));
    await fetchState();
  }

  async function handleAddMore() {
    await import("../api").then(api => api.triggerAction(project.id, "unlock-requirements"));
    await fetchState();
  }

  const inputLocked = phase === "approved";
  const inputProcessing = phase === "processing" || phase === "reviewing";

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Project nav bar */}
      <header className="flex-shrink-0 h-12 border-b border-border bg-card px-5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={onBack}
            className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft size={14} />
            Projects
          </button>
          <span className="text-muted-foreground/30">·</span>
          <span className="text-sm font-semibold text-foreground">{project.name}</span>
        </div>

        <div className="flex items-center bg-secondary rounded-lg p-0.5 gap-0.5">
          {[
            { key: "chat" as ActiveTab, label: "Chat", icon: <MessageSquare size={12} /> },
            { key: "board" as ActiveTab, label: "Task Board", icon: <Kanban size={12} /> },
          ].map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${activeTab === tab.key ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
                } ${tab.key === "board" && phase !== "approved" ? "opacity-50" : ""}`}
            >
              {tab.icon}
              {tab.label}
              {tab.key === "board" && phase !== "approved" && (
                <span className="text-[10px] bg-muted-foreground/20 text-muted-foreground px-1.5 py-0.5 rounded-full ml-0.5">
                  soon
                </span>
              )}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          {phase === "listening" && <div className="flex items-center gap-1.5 text-xs text-muted-foreground"><span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />Listening</div>}
          {phase === "processing" && <div className="flex items-center gap-1.5 text-xs text-amber-600"><Loader2 size={12} className="animate-spin" />Analyzing</div>}
          {phase === "reviewing" && <div className="flex items-center gap-1.5 text-xs text-amber-600"><span className="w-1.5 h-1.5 rounded-full bg-amber-400" />Under Review</div>}
          {phase === "approved" && <div className="flex items-center gap-1.5 text-xs text-green-600"><CheckCircle2 size={12} />Approved</div>}
        </div>
      </header>

      {/* Body */}
      <div className="flex-1 flex min-h-0">
        {activeTab === "chat" && (
          <>
            <div
              className="flex flex-col bg-background border-r border-border transition-all duration-300"
              style={{ width: sidePanelVisible ? "60%" : "100%" }}
            >
              <div ref={feedRef} className="flex-1 overflow-y-auto px-6 py-5 space-y-5 scrollbar-hidden">
                {messages.map((msg, i) => <ChatBubble key={i} msg={msg} />)}
                {phase === "processing" && <ProcessingDots />}
                {isThinking && <ThinkingIndicator />}
              </div>

              <div className="flex-shrink-0 px-5 py-4 border-t border-border bg-card">
                {inputProcessing ? (
                  <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-secondary text-sm text-muted-foreground">
                    <Loader2 size={15} className="animate-spin text-primary" />
                    <span>{phase === "processing" ? "Analyzing your requirements..." : "Review the requirements in the side panel."}</span>
                  </div>
                ) : inputLocked ? (
                  <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-secondary/60 border border-border">
                    <CheckCircle2 size={15} className="text-green-500" />
                    <span className="text-sm text-muted-foreground">Requirements approved.</span>
                  </div>
                ) : (
                  <div className="flex items-end gap-2">
                    <div className="flex-1">
                      <textarea
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Describe your project requirements..."
                        rows={1}
                        className="w-full resize-none bg-input-background rounded-xl px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground outline-none focus:ring-2 focus:ring-primary/30 transition-all scrollbar-hidden"
                        style={{ minHeight: "44px", maxHeight: "120px" }}
                        onInput={(e) => {
                          const t = e.currentTarget;
                          t.style.height = "auto";
                          t.style.height = Math.min(t.scrollHeight, 120) + "px";
                        }}
                      />
                    </div>
                    {phase === "listening" && (
                      <button
                        onClick={beginAnalysis}
                        className="flex items-center gap-1.5 px-3.5 py-2.5 rounded-xl border border-primary/40 bg-accent text-accent-foreground text-xs font-medium transition-all hover:bg-primary hover:text-primary-foreground hover:border-primary whitespace-nowrap"
                      >
                        <Sparkles size={13} />
                        Begin Analysis
                      </button>
                    )}
                    {projectState?.elicitation_phase === "stress_testing" && projectState?.project_goals && (
                      <button
                        onClick={handleApprove}
                        className="flex items-center gap-1.5 px-3.5 py-2.5 rounded-xl bg-green-500 text-white text-xs font-medium transition-all hover:bg-green-600 whitespace-nowrap"
                      >
                        <CheckCircle2 size={13} />
                        Approve Goals
                      </button>
                    )}
                    <button
                      onClick={sendMessage}
                      disabled={!input.trim()}
                      className="w-10 h-10 rounded-xl bg-primary text-primary-foreground flex items-center justify-center flex-shrink-0 transition-all hover:bg-primary/90 disabled:opacity-30 disabled:cursor-not-allowed"
                    >
                      <Send size={15} />
                    </button>
                  </div>
                )}
              </div>
            </div>

            <div
              className="flex flex-col bg-card border-l border-border overflow-hidden"
              style={{
                width: sidePanelVisible ? "40%" : "0%",
                opacity: sidePanelVisible ? 1 : 0,
                transition: "width 0.35s cubic-bezier(0.4,0,0.2,1), opacity 0.3s ease",
              }}
            >
              {(phase === "processing" || phase === "listening") && sidePanelVisible && <IdlePanel />}
              {phase === "reviewing" && <ReviewPanel onApprove={handleApprove} onModify={handleModify} />}
              {phase === "approved" && <ApprovedPanel onAddMore={handleAddMore} />}
            </div>
          </>
        )}

        {activeTab === "board" && (
          <div className="flex-1 bg-background overflow-hidden">
            <KanbanBoardView project={project} tasks={projectState?.tasks || []} />
          </div>
        )}
      </div>
    </div>
  );
}

import { fetchProjects, createProject } from "../api";

// ─── Root App ─────────────────────────────────────────────────────────────────

export default function App() {
  const [view, setView] = useState<AppView>("dashboard");
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  const reloadProjects = () => {
    fetchProjects()
      .then(setProjects)
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    reloadProjects();
  }, []);

  async function handleNewProject() {
    setLoading(true);
    try {
      const p = await createProject({
        id: `proj_${Date.now()}`,
        name: "New Project",
        description: "A new project",
        status: "listening",
        progress: 0,
        tags: [],
        accent_color: "#5B4EFF"
      } as any);
      await fetchProjects().then(setProjects);
      openProject(p);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  function openProject(p: Project) {
    setSelectedProject(p);
    setView("project");
  }

  function goBack() {
    setView("dashboard");
    setSelectedProject(null);
  }

  return (
    <div
      className="h-screen w-screen bg-background flex flex-col overflow-hidden"
      style={{ fontFamily: "'Inter', system-ui, sans-serif" }}
    >
      <style>{`
        @keyframes pmBounce {
          0%, 80%, 100% { transform: scale(0.8); opacity: 0.4; }
          40% { transform: scale(1); opacity: 1; }
        }
        .scrollbar-hidden { scrollbar-width: none; }
        .scrollbar-hidden::-webkit-scrollbar { display: none; }
        .line-clamp-2 {
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }
      `}</style>

      {/* Global top bar */}
      <header className="flex-shrink-0 h-12 border-b border-border bg-card px-5 flex items-center justify-between">
        <button
          onClick={goBack}
          className="flex items-center gap-2.5 hover:opacity-80 transition-opacity"
        >
          <div className="w-7 h-7 rounded-lg bg-primary flex items-center justify-center">
            <Sparkles size={14} className="text-primary-foreground" />
          </div>
          <span className="text-sm font-semibold text-foreground tracking-tight">
            AI Project Manager
          </span>
          <span className="hidden sm:block text-xs text-muted-foreground font-mono bg-muted px-2 py-0.5 rounded-full">
            beta
          </span>
        </button>

        {view === "dashboard" && (
          <div className="flex items-center gap-3">
            <div className="text-xs text-muted-foreground flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
              {projects.filter((p) => p.status === "approved").length} approved
            </div>
            <div className="text-xs text-muted-foreground flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
              {projects.filter((p) => p.status === "reviewing").length} in review
            </div>
          </div>
        )}

        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center text-xs font-semibold text-primary">
            AD
          </div>
          <ChevronDown size={13} className="text-muted-foreground" />
        </div>
      </header>

      {/* View router */}
      {view === "dashboard" && (
        loading ? (
          <div className="flex-1 flex items-center justify-center bg-background">
            <Loader2 className="animate-spin text-primary" size={24} />
          </div>
        ) : (
          <ProjectDashboard projects={projects} onSelect={openProject} onCreate={handleNewProject} />
        )
      )}
      {view === "project" && selectedProject && (
        <ProjectWorkspace project={selectedProject} onBack={() => { reloadProjects(); goBack(); }} />
      )}
    </div>
  );
}
