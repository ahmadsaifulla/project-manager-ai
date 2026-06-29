// Unified networking layer pointing directly to the Master Orchestrator API Gateway
const BASE_URL = "http://localhost:8000";

/**
 * Global Configuration endpoints
 */
export async function getProjectConfig() {
    try {
        const response = await fetch(`${BASE_URL}/api/config`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error("getProjectConfig error:", error);
        return { error: "Failed to fetch project configuration. Is the orchestrator running?" };
    }
}

export async function updateProjectConfig(repoName) {
    try {
        const response = await fetch(`${BASE_URL}/api/config`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ repo_name: repoName })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error("updateProjectConfig error:", error);
        return { error: "Failed to update project configuration." };
    }
}

/**
 * Chatbot Node proxy routing
 */
export async function sendChatMessage(message) {
    try {
        const response = await fetch(`${BASE_URL}/api/chat/message`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: message })
        });
        
        if (!response.ok) {
            let errorText = `HTTP error! status: ${response.status}`;
            try {
                const errorData = await response.json();
                errorText = errorData.detail || errorData.error || errorText;
            } catch (e) {}
            throw new Error(errorText);
        }
        
        return await response.json();
    } catch (error) {
        console.error("sendChatMessage error:", error);
        return { error: error.message || "Failed to send message. Is the Orchestrator running?" };
    }
}

export async function triggerChatAction(action) {
    try {
        const response = await fetch(`${BASE_URL}/api/chat/${action}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" }
        });
        
        if (!response.ok) {
            let errorText = `HTTP error! status: ${response.status}`;
            try {
                const errorData = await response.json();
                errorText = errorData.detail || errorData.error || errorText;
            } catch (e) {}
            throw new Error(errorText);
        }
        
        return await response.json();
    } catch (error) {
        console.error(`triggerChatAction (${action}) error:`, error);
        return { error: error.message || `Failed to trigger ${action}. Is the Orchestrator running?` };
    }
}
/**
 * Developer Node proxy routing (QC Engine)
 */
export async function handoverToQC(taskId, branchName) {
    try {
        const response = await fetch(`${BASE_URL}/api/qc/evaluate`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            // Notice: We don't send `repo_name` here, the Orchestrator injects it globally!
            body: JSON.stringify({ task_id: taskId, branch_name: branchName })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error("handoverToQC error:", error);
        return { 
            error: "Failed to trigger QC check. Is the Orchestrator running?", 
            verdict: false 
        };
    }
}
