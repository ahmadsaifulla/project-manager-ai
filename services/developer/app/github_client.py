import os
from github import Github
from github.GithubException import GithubException
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

GITHUB_PAT = os.getenv("GITHUB_PAT")
if not GITHUB_PAT:
    # If the token is missing, we might want to fail fast or handle it gracefully.
    # For now, we will leave it as None and let PyGithub throw an auth error if used,
    # or we can raise an error immediately. Let's raise an error to fail fast.
    pass

def get_branch_diff(repo_name: str, branch_name: str) -> str:
    """
    Connects to the specified GitHub repository and extracts the raw, text-based
    git diff between the 'main' branch and the provided 'branch_name'.
    """
    if not GITHUB_PAT:
        raise ValueError("GITHUB_PAT is not set in the environment.")
        
    # Initialize the PyGithub client
    client = Github(GITHUB_PAT)
    
    try:
        # Connect to the repository (expects "owner/repo" format)
        repo = client.get_repo(repo_name)
        
        # Compare task branch against main
        comparison = repo.compare("main", branch_name)
        
        # Extract raw patch text from the comparison
        diff_lines = []
        for file in comparison.files:
            if file.patch:
                diff_lines.append(f"--- a/{file.filename}\n+++ b/{file.filename}\n{file.patch}")
            else:
                diff_lines.append(f"--- a/{file.filename}\n+++ b/{file.filename}\n# (Binary file or diff too large)")
                
        return "\n\n".join(diff_lines)
        
    except GithubException as e:
        raise RuntimeError(f"GitHub API Error [{e.status}]: {e.data.get('message', 'Unknown error')}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error while fetching diff: {str(e)}")
