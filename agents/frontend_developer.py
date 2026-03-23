import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from state import AgentState
from tools import write_code_to_workspace, read_file_from_workspace
from config import DEFAULT_MODEL, TEMPERATURE, WORKSPACE_DIR, BACKEND_PORT, FRONTEND_PORT

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
                if file.endswith((".js", ".jsx", ".css", ".json", ".html")) and file not in ["package-lock.json", "yarn.lock"]:   
                    with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                        rel_path = os.path.relpath(os.path.join(root, file), project_dir)
                        existing_code_content += f"\n--- {rel_path} ---\n{f.read()}\n"
    
    system_prompt = SystemMessage(content=f"""당신은 React 프론트엔드 전문 개발자입니다.
아키텍트의 설계도와 API 명세서를 보고 화면 컴포넌트와 API 연동 코드를 구현합니다.

[🚨 도구 호출 절대 규칙 - 엄수]
1. 'project_name' 파라미터는 반드시 "{project_name}" 으로 고정하세요!
2. 도구 호출 시 'module_type'은 반드시 "frontend"로 지정하세요.
3. 'filename'에는 순수 경로만 적으세요. (예: package.json, src/App.jsx, src/pages/HomePage.jsx)
4. 🚨 [다중 도구 호출(Multi-Tool Call) 강제]: 당신은 한 번의 응답에서 'write_code_to_workspace' 도구를 **반드시 3~4번 이상 동시에 호출**하여 필요한 모든 파일을 한 번에 생성해야 합니다!
   - 예시: 한 번에 `package.json`, `src/App.jsx`, `src/pages/HomePage.jsx`, `src/components/ProductList.jsx` 를 모두 각각의 도구 호출로 생성하세요.
   - 누락된 페이지나 컴포넌트가 하나라도 있으면 빌드 에러가 발생합니다. 설계도에 있는 모든 JSX 파일을 한 번의 턴에 모두 만드세요!
5. 🚨 [도구 강제 호출]: 에러 피드백이나 Supervisor의 지시를 받으면, 절대 말로만 대답하지 마세요! 문제를 해결하기 위해 반드시 하나 이상의 파일에 대해 'write_code_to_workspace' 도구를 호출하여 코드를 덮어쓰고 저장해야만 임무가 끝납니다.

[개발 지침]
1. 🚨 [매우 중요: Vite 및 빌드 스크립트 강제]: 프론트엔드 환경 세팅을 위해 반드시 Vite 기반의 `package.json`을 구성하세요. 
   `scripts` 섹션에는 무조건 아래 두 가지가 포함되어야 합니다:
   - `"dev": "vite --port {FRONTEND_PORT}"`
   - `"build": "vite build"`
   또한 필수 패키지로 `vite`, `@vitejs/plugin-react`, `react`, `react-dom`을 반드시 명시하세요.
2. 🚨 [매우 중요: 확장자 규칙]: Vite 등 모던 빌드 환경을 위해, JSX 구문(HTML 태그)이 포함된 모든 React 컴포넌트 파일의 확장자는 반드시 `.js`가 아닌 `.jsx`로 작성하세요. (예: App.jsx, main.jsx) 
3. 백엔드와의 통신은 Fetch API나 Axios를 사용하세요.
4. 백엔드 API를 호출할 때, 반드시 API 명세서(Contract)에 기재된 '백엔드 로컬 서버 주소(http://localhost:{BACKEND_PORT})'를 Base URL로 사용하여 절대 경로로 요청을 보내야 합니다.
""")


    test_results = state.get("test_results", "")
    supervisor_directive = state.get("supervisor_directive", "")

    user_prompt = HumanMessage(content=f"""
[API 명세서]:\n{api_contract}\n
[프론트엔드 아키텍처]:\n{architecture}\n
[현재 작성된 코드]:\n{existing_code_content}\n
🚨 [QA 테스트 결과(에러)]: {test_results}
🚨 [Supervisor 지시사항]: {supervisor_directive}

이 요구사항에 맞춰 필요한 React 구성 요소(package.json, src/*, index.html 등)들을 작성하거나 수정하세요.
""")

    response = llm_with_tools.invoke([system_prompt, user_prompt])
    if response.tool_calls:
        for tool_call in response.tool_calls:
            if tool_call["name"] == "write_code_to_workspace":
                result = write_code_to_workspace.invoke(tool_call["args"])
                print(f"   -> 💻 {result}")

    return {}
