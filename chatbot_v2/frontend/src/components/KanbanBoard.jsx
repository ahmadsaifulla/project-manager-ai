import React, { useState } from 'react';
import { handoverToQC } from '../api';

const TaskCard = ({ task }) => {
  // Step A: Local states for tracking analysis
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [qcResult, setQcResult] = useState(null);

  // Step B: Event Handler
  const handleQCSubmit = async (taskId, branchName) => {
    setIsAnalyzing(true);
    setQcResult(null); // Reset previous result if any
    
    try {
      const response = await handoverToQC(taskId, branchName);
      setQcResult(response);
    } catch (err) {
      setQcResult({ verdict: false, feedback: "Error triggering QC check.", error: err.message });
    } finally {
      setIsAnalyzing(false);
    }
  };

  // We dynamically generate a branch name based on the task ID if not explicitly provided
  const branchName = task.branch || `feat/${task.id.toLowerCase()}`;

  return (
    <div className="kanban__card">
      <div className="kanban__card-title">{task.title}</div>
      <div className="kanban__card-meta">
        <span className={`kanban__card-priority kanban__card-priority--${task.priority.toLowerCase()}`}>
          {task.priority}
        </span>
        <span>{task.estimated_effort}</span>
      </div>

      {/* QC Action Button */}
      <button 
        onClick={() => handleQCSubmit(task.id, branchName)} 
        disabled={isAnalyzing}
        style={{
          width: '100%',
          padding: '8px',
          background: isAnalyzing ? '#4B5563' : '#4F46E5',
          color: 'white',
          border: 'none',
          borderRadius: '6px',
          cursor: isAnalyzing ? 'not-allowed' : 'pointer',
          marginTop: '12px',
          fontSize: '12px',
          fontWeight: '600',
          transition: 'background 0.2s ease-in-out'
        }}
      >
        {isAnalyzing ? "Analyzing Code..." : "Handover to QC"}
      </button>

      {/* Step C: Visual Feedback Rendering */}
      {qcResult && (
        <div style={{ 
          marginTop: '12px', 
          padding: '10px', 
          background: '#111827', 
          borderRadius: '6px', 
          fontSize: '12px', 
          border: '1px solid #374151',
          boxShadow: 'inset 0 2px 4px 0 rgba(0, 0, 0, 0.05)'
        }}>
          <div style={{ 
            display: 'inline-block', 
            padding: '4px 8px', 
            borderRadius: '4px',
            background: qcResult.verdict ? '#059669' : '#DC2626',
            color: 'white',
            fontWeight: 'bold',
            marginBottom: '8px',
            fontSize: '10px',
            letterSpacing: '0.05em'
          }}>
            {qcResult.verdict ? 'APPROVED' : 'REJECTED'}
          </div>
          <div style={{ 
            color: '#D1D5DB', 
            whiteSpace: 'pre-wrap', 
            maxHeight: '150px', 
            overflowY: 'auto',
            lineHeight: '1.4'
          }}>
            {qcResult.feedback || qcResult.error}
          </div>
        </div>
      )}
    </div>
  );
};

const KanbanBoard = ({ tasks }) => {
  const columns = [
    { id: 'todo', title: 'To Do', status: 'todo' },
    { id: 'in_progress', title: 'In Progress', status: 'in_progress' },
    { id: 'done', title: 'Done', status: 'done' },
  ];

  return (
    <div className="kanban">
      {columns.map((col) => {
        // Safe access in case tasks is undefined initially
        const colTasks = tasks?.filter((t) => t.status === col.status) || [];
        return (
          <div key={col.id} className="kanban__column">
            <div className="kanban__column-header">
              <span className="kanban__column-title">{col.title}</span>
              <span className="kanban__column-count">{colTasks.length}</span>
            </div>
            <div className="kanban__cards">
              {colTasks.map((task) => (
                // Use the new isolated TaskCard component to prevent shared state issues
                <TaskCard key={task.id} task={task} />
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default KanbanBoard;
