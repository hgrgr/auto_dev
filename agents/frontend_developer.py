import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from state import AgentState
from tools import write_code_to_workspace, read_file_from_workspace
from config import DEFAULT_MODEL, TEMPERATURE, WORKSPACE_DIR

llm = ChatOpenAI(model=DEFAULT_MODEL, temperature=TEMPERATURE)
llm_with_tools = llm.bind_tools([write_code_to_workspace, read_file_from_workspace])

def frontend_developer_agent(state: AgentState):
    project_name = state.get("project_name", "unknown_project")
    print(f"\n⚛️ [Frontend Developer]: '{project_name}' 프로젝트의 React UI 코드를 작성 중입니다...")
    
    api_contract = state.get("api_contract", "")
    architecture = state.get("frontend_architecture", "")
    
    project_dir = os.path.join(WORKSPACE_DIR, project_name, "frontend")
    existing_code_content = ""
    
    if os.path.exists(project_dir):
        for root, _, files in os.walk(project_dir):
            if "node_modules" in root or "dist" in root or "build" in root: continue
            for file in files:
                if file.endswith((".js", ".jsx", ".css", ".json", ".html")):
                    with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                        rel_path = os.path.relpath(os.path.join(root, file), project_dir)
                        existing_code_content += f"\n--- {rel_path} ---\n{f.read()}\n"

    system_prompt = SystemMessage(content=f"""당신은 React 프론트엔드 전문 개발자입니다.
아키텍트의 설계도와 API 명세서를 보고 화면 컴포넌트와 API 연동 코드를 구현합니다.

[🚨 도구 호출 절대 규칙 - 엄수]
1. 'project_name' 파라미터는 반드시 "{project_name}" 으로 고정하세요!
2. 도구 호출 시 'module_type'은 반드시 "frontend"로 지정하세요.
3. 'filename'에는 순수 경로만 적으세요.

[개발 지침]
1. 프론트엔드 환경 세팅을 위해 반드시 올바른 `package.json` 파일과 최소한의 Vite/React 보일러플레이트를 구성하세요.
2. 컴포넌트는 함수형(Functional Component)과 Hooks를 사용합니다.
3. 백엔드와의 통신은 Fetch API나 Axios를 사용하고, API 명세서의 엔드포인트를 정확히 호출하세요.""")

    user_prompt = HumanMessage(content=f"""
[API 명세서]:\n{api_contract}\n
[프론트엔드 아키텍처]:\n{architecture}\n
[현재 작성된 코드]:\n{existing_code_content}\n

이 요구사항에 맞춰 필요한 React 구성 요소(package.json, src/*, index.html 등)들을 작성하거나 수정하세요.
""")

    response = llm_with_tools.invoke([system_prompt, user_prompt])
    if response.tool_calls:
        for tool_call in response.tool_calls:
            if tool_call["name"] == "write_code_to_workspace":
                result = write_code_to_workspace.invoke(tool_call["args"])
                print(f"   -> 💻 {result}")

    return {}
