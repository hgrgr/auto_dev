import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from state import AgentState
from tools import write_code_to_workspace
from config import DEFAULT_MODEL, TEMPERATURE, WORKSPACE_DIR

llm = ChatOpenAI(model=DEFAULT_MODEL, temperature=TEMPERATURE)
llm_with_tools = llm.bind_tools([write_code_to_workspace])

def frontend_architect_agent(state: AgentState):
    project_name = state.get("project_name", "unknown_project")
    print(f"\n🎨 [Frontend Architect]: '{project_name}'의 React 프론트엔드 아키텍처를 설계합니다...")
    
    api_contract = state.get("api_contract", "API 명세서가 없습니다.")
    existing_architecture = state.get("frontend_architecture", "")
    
    project_dir = os.path.join(WORKSPACE_DIR, project_name, "frontend")
    actual_files = []
    if os.path.exists(project_dir):
        for root, _, files in os.walk(project_dir):
            if "node_modules" in root or ".git" in root: continue
            for f in files:
                actual_files.append(os.path.relpath(os.path.join(root, f), project_dir))
    actual_files_str = "\n".join(actual_files) if actual_files else "생성된 프론트엔드 파일 없음"

    system_prompt = SystemMessage(content=f"""당신은 React 프론트엔드 수석 아키텍트입니다.
사용자 요구사항과 PM이 작성한 <API_CONTRACT>를 바탕으로 컴포넌트 구조, 상태 관리, 라우팅 설계를 수행합니다.

[🚨 도구 호출 절대 규칙]
1. 'project_name' 파라미터는 반드시 "{project_name}" 으로 고정하세요!
2. 도구 호출 시 'module_type' 파라미터는 무조건 "frontend"로 지정하세요.
3. 'filename' 파라미터에는 순수 상대 경로만 입력하세요.

[설계 원칙]
1. 프레임워크: React 기반 시스템 (Vite 또는 Create React App 구조)을 상정하여 설계합니다.
2. 백엔드(Python) 코드는 절대 설계하지 않습니다. 오직 UI와 클라이언트 측 API 호출 구조만 설계합니다.
3. 설계도는 도구를 사용하여 'docs/frontend_architecture.md' 파일로 저장하세요.""")

    user_prompt = HumanMessage(content=f"""
[API 명세서 (Contract)]: {api_contract}
[기존 설계도]: {existing_architecture}
[현재 디스크 파일 목록]: {actual_files_str}

위 정보를 바탕으로 React 기반의 프론트엔드 디렉토리/컴포넌트 설계도를 작성하세요.
""")

    response = llm_with_tools.invoke([system_prompt, user_prompt])
    if response.tool_calls:
        for tool_call in response.tool_calls:
            if tool_call["name"] == "write_code_to_workspace":
                result = write_code_to_workspace.invoke(tool_call["args"])
                print(f"   -> 📐 {result}")

    return {"frontend_architecture": response.content}
