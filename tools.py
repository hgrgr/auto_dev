import os
from langchain_core.tools import tool
from config import WORKSPACE_DIR

@tool
def write_code_to_workspace(project_name: str, filename: str, code: str) -> str:
    """
    작성된 코드를 프로젝트 디렉토리에 저장합니다.
    
    Args:
        project_name: 프로젝트 이름 (예: 'shopping')
        filename: 저장할 파일의 '순수 상대 경로'. 
                 🚨 주의: 절대로 'project-root/', './', 또는 프로젝트명을 경로 앞에 붙이지 마세요.
                 (OK: 'docs/architecture.md', 'models/user.py' / NO: 'project-root/docs/architecture.md')
        code: 저장할 내용
    """
    # [방어적 로직 추가] 모델이 기어코 접두사를 붙였을 경우 강제로 제거
    prefixes_to_clean = ["project-root/", "./", f"{project_name}/"]
    clean_filename = filename
    for prefix in prefixes_to_clean:
        if clean_filename.startswith(prefix):
            clean_filename = clean_filename[len(prefix):]

    project_dir = os.path.join(WORKSPACE_DIR, project_name)
    filepath = os.path.join(project_dir, clean_filename)

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(code)
    
    # 반환 메시지에서도 'project-root'가 보이지 않게 clean_filename 사용
    return f"Success: {clean_filename} 파일이 저장되었습니다."

@tool
def read_file_from_workspace(project_name: str, filename: str) -> str:
    """
    프로젝트 디렉토리 내의 특정 파일 내용을 읽어옵니다.
    
    Args:
        project_name: 프로젝트 이름
        filename: 읽어올 파일의 상대 경로 (예: 'models/user.py')
    """
    # 읽기 도구에도 동일한 방어 로직 적용 권장
    clean_filename = filename.replace("project-root/", "").replace("./", "")
    if clean_filename.startswith(f"{project_name}/"):
        clean_filename = clean_filename[len(project_name)+1:]

    filepath = os.path.join(WORKSPACE_DIR, project_name, clean_filename)

    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    return f"Error: {clean_filename} 파일이 존재하지 않습니다."
