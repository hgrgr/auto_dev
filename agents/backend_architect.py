import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from state import AgentState
from tools import write_code_to_workspace
from config import DEFAULT_MODEL, TEMPERATURE, WORKSPACE_DIR

llm = ChatOpenAI(model=DEFAULT_MODEL, temperature=TEMPERATURE)
llm_with_tools = llm.bind_tools([write_code_to_workspace])

def backend_architect_agent(state: AgentState):
    project_name = state.get("project_name", "unknown_project")
    print(f"\n🏗️ [Backend Architect]: '{project_name}'의 백엔드 시스템 아키텍처를 설계합니다...")
    
    requirements = state.get("requirements", "요구사항이 없습니다.")
    api_contract = state.get("api_contract", "API 명세서가 없습니다.")
    existing_architecture = state.get("backend_architecture", "")
    supervisor_directive = state.get("supervisor_directive", "")
    
    # 백엔드 디렉토리 파일 탐색
    project_dir = os.path.join(WORKSPACE_DIR, project_name, "backend")
    actual_files = []
    if os.path.exists(project_dir):
        for root, _, files in os.walk(project_dir):
            if "venv" in root or "__pycache__" in root: continue
            for f in files:
                actual_files.append(os.path.relpath(os.path.join(root, f), project_dir))
    actual_files_str = "\n".join(actual_files) if actual_files else "생성된 백엔드 파일 없음"

    system_prompt = SystemMessage(content=f"""당신은 수석 백엔드 아키텍트입니다.
PM이 작성한 <API_CONTRACT>를 완벽하게 구현하기 위한 백엔드 시스템(Python, FastAPI/Flask 등) 설계도를 작성하세요.

[🚨 도구 호출 절대 규칙]
1. 'project_name' 파라미터는 반드시 "{project_name}" 으로 고정하세요! (오타 주의)
2. 'module_type' 파라미터는 무조건 "backend"로 지정하세요.
3. 'filename' 파라미터에는 순수 상대 경로만 입력하세요.

[설계 원칙]
1. 환경 제약: 오직 Python 3.13 생태계만을 사용합니다.
2. PM의 기획서와 API 명세서를 바탕으로 디렉토리 구조, DB 스키마, 주요 클래스/함수 스펙을 설계합니다.
3. 설계도는 도구를 사용하여 'docs/backend_architecture.md' 파일로 저장하세요.""")

    user_prompt = HumanMessage(content=f"""
[전체 요구사항]: {requirements}
[API 명세서 (Contract)]: {api_contract}
[기존 설계도]: {existing_architecture}
[현재 실제 디스크 파일 목록]: {actual_files_str}
🚨 [SUPERVISOR 지시사항]: {supervisor_directive}

위 정보를 바탕으로 백엔드 설계도를 작성 및 업데이트하세요.
""")

    response = llm_with_tools.invoke([system_prompt, user_prompt])
    if response.tool_calls:
        for tool_call in response.tool_calls:
            if tool_call["name"] == "write_code_to_workspace":
                result = write_code_to_workspace.invoke(tool_call["args"])
                print(f"   -> 📐 {result}")
    return {"backend_architecture": response.content}
