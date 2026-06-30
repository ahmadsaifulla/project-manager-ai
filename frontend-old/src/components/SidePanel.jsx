import React from 'react';
import KanbanBoard from './KanbanBoard';

const SidePanel = ({
  projectState,
  onApproveGoals,
  onRejectGoals,
  onUnlockRequirements,
  onFinishSharing,
}) => {
  if (!projectState) return null;

  const {
    elicitation_phase,
    goals_approved,
    project_goals,
    tasks,
  } = projectState;

  const renderContent = () => {
    if (goals_approved && tasks.length > 0) {
      return (
        <div className="side-panel__goals">
          <div className="side-panel__goal-section">
            <h4>Project Board</h4>
            <KanbanBoard tasks={tasks} />
          </div>
          <div className="side-panel__actions">
            <button className="btn btn--secondary" onClick={onUnlockRequirements}>
              Unlock Requirements
            </button>
          </div>
        </div>
      );
    }

    if (elicitation_phase === 'stress_testing') {
      return (
        <div className="side-panel__goals">
          <div className="side-panel__goal-section">
            <h4>Draft Project Goals</h4>
            {project_goals ? (
              <div dangerouslySetInnerHTML={{ __html: project_goals.replace(/\n/g, '<br/>') }} />
            ) : (
              <p>Analyzing requirements...</p>
            )}
          </div>
          <div className="side-panel__actions">
            <button className="btn btn--primary" onClick={onApproveGoals}>
              Approve Goals
            </button>
            <button className="btn btn--danger" onClick={onRejectGoals}>
              Reject & Modify
            </button>
          </div>
        </div>
      );
    }

    return (
      <div className="side-panel__idle">
        <div className="side-panel__idle-icon">👂</div>
        <p>I'm listening to your requirements. Just tell me what you want to build.</p>
        <button className="btn btn--primary" onClick={onFinishSharing} style={{ marginTop: '16px' }}>
          Begin Analysis
        </button>
      </div>
    );
  };

  return (
    <aside className="side-panel">
      <div className="side-panel__header">
        <h3 className="side-panel__title">Project Workspace</h3>
        <span className="side-panel__subtitle">
          Status: {goals_approved ? 'Execution' : 'Planning'}
        </span>
      </div>
      <div className="side-panel__content">{renderContent()}</div>
    </aside>
  );
};

export default SidePanel;
