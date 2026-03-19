import os
from langchain_core.tools import tool
from config import WORKSPACE_DIR

@tool
def write_code_to_workspace(project_name: str, filename: str, code: str) -> str:
    """작성된 코드를 workspace 하위의 특정 프로젝트 디렉토리에 파일로 저장합니다."""
    project_dir = os.path.join(WORKSPACE_DIR, project_name)
    filepath = os.path.join(project_dir, filename)
    
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(code)
    return f"Success: {project_name}/{filename} 파일이 저장되었습니다."

@tool
def read_file_from_workspace(project_name: str, filename: str) -> str:
    """workspace 내의 특정 파일의 내용을 읽어옵니다."""
    filepath = os.path.join(WORKSPACE_DIR, project_name, filename)
    
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    return f"Error: {filename} 파일이 존재하지 않습니다."
