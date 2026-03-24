import os
from langchain_core.tools import tool
from config import WORKSPACE_DIR

@tool
def write_code_to_workspace(project_name: str, module_type: str, filename: str, code: str) -> str:
    """
    작성된 코드를 프로젝트의 특정 모듈(backend, frontend, docs) 디렉토리에 저장합니다.
    
    Args:
        project_name (str): 프로젝트 이름
        module_type (str): 파일이 저장될 모듈의 종류. 반드시 다음 3개 중 하나여야 합니다: ['backend', 'frontend', 'docs']
        filename (str): 저장할 파일의 '순수 상대 경로'. (예: 'main.py', 'src/App.js', 'api_contract.md')
                       🚨 주의: 경로에 'project-root/'나 './', 'backend/' 등의 접두사를 중복해서 붙이지 마세요.
        code (str): 저장할 코드 또는 텍스트 내용
    """
    # 1. module_type 검증 (방어적 로직)
    valid_modules = ["backend", "frontend", "docs"]
    if module_type not in valid_modules:
        return f"Error: module_type은 {valid_modules} 중 하나여야 합니다. (입력값: {module_type})"

    # 2. filename에서 불필요한 접두사 강제 제거 (방어적 로직)
    prefixes_to_clean = ["project-root/", "./", f"{project_name}/", f"{module_type}/"]
    clean_filename = filename
    for prefix in prefixes_to_clean:
        if clean_filename.startswith(prefix):
            clean_filename = clean_filename[len(prefix):]

    # 3. 최종 경로 생성 (예: workspace/shopping/backend/main.py)
    project_dir = os.path.join(WORKSPACE_DIR, project_name)
    filepath = os.path.join(project_dir, module_type, clean_filename)

    # 4. 저장
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(code)
    
    return f"Success: [{module_type}] 파트에 {clean_filename} 파일이 저장되었습니다."

@tool
def read_file_from_workspace(project_name: str, module_type: str, filename: str) -> str:
    """
    프로젝트 디렉토리 내의 특정 파일 내용을 읽어옵니다.
    
    Args:
        project_name (str): 프로젝트 이름
        module_type (str): 읽어올 파일이 위치한 모듈 ('backend', 'frontend', 'docs')
        filename (str): 읽어올 파일의 상대 경로
    """
    clean_filename = filename.replace("project-root/", "").replace("./", "")
    if clean_filename.startswith(f"{module_type}/"):
        clean_filename = clean_filename[len(module_type)+1:]

    filepath = os.path.join(WORKSPACE_DIR, project_name, module_type, clean_filename)

    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    return f"Error: [{module_type}] 파트에 {clean_filename} 파일이 존재하지 않습니다."
