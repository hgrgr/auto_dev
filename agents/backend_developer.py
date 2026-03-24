import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from state import AgentState
from tools import write_code_to_workspace, read_file_from_workspace
from config import DEFAULT_MODEL, TEMPERATURE, WORKSPACE_DIR

llm = ChatOpenAI(model=DEFAULT_MODEL, temperature=TEMPERATURE)
llm_with_tools = llm.bind_tools([write_code_to_workspace, read_file_from_workspace])

def backend_developer_agent(state: AgentState):
    project_name = state.get("project_name", "unknown_project")
    print(f"\n🐍 [Backend Developer]: '{project_name}' 프로젝트의 파이썬 API 서버를 구현합니다...")
    
    requirements = state.get("requirements", "")
    api_contract = state.get("api_contract", "")
    architecture = state.get("backend_architecture", "")
    test_results = state.get("test_results", "")  # <--- 이 줄 추가!
    supervisor_directive = state.get("supervisor_directive", "") # <--- 추가 (없다면)

    project_dir = os.path.join(WORKSPACE_DIR, project_name, "backend")
    
    # requirements.txt 및 기존 코드 읽기 (기존 로직 유지)
    req_content = "생성 전"
    existing_code_content = ""
    if os.path.exists(project_dir):
        req_path = os.path.join(project_dir, "requirements.txt")
        if os.path.exists(req_path):
            with open(req_path, "r", encoding="utf-8") as f: req_content = f.read()
            
        for root, _, files in os.walk(project_dir):
            if "venv" in root or "__pycache__" in root: continue
            for file in files:
                if file.endswith(".py"):
                    with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                        rel_path = os.path.relpath(os.path.join(root, file), project_dir)
                        existing_code_content += f"\n--- {rel_path} ---\n{f.read()}\n"
 
    system_prompt = SystemMessage(content=f"""당신은 파이썬 백엔드 전문 개발자입니다.
PM이 정의한 API 명세서(Contract)와 아키텍트의 설계도를 정확히 구현하는 코드를 작성하세요.

[🚨 도구 호출 절대 규칙 - 엄수]
1. 'project_name' 파라미터는 반드시 "{project_name}" 으로 고정하세요!
2. 도구 호출 시 'module_type'은 반드시 "backend"로 지정하세요.
3. 'filename'에는 순수 상대 경로만 적으세요.
4. [중요] 백엔드 서버의 메인 실행 파일 이름은 무조건 "main.py"로 작성하세요. (app.py 사용 절대 금지)
5. 🚨 [다중 도구 호출(Multi-Tool Call) 강제]: 한 번의 응답에서 'write_code_to_workspace' 도구를 **반드시 2번 이상 동시에 호출**해야 합니다! 
   - 첫 번째 호출: 'requirements.txt' 작성
   - 두 번째 호출: 'main.py' 작성
   어느 하나라도 누락하여 한 번만 도구를 호출하면 당신은 해고됩니다. 반드시 두 파일을 한 번에 모두 생성하세요!

[개발 지침]
1. 당신의 영역은 오직 'backend'입니다. 프론트엔드 코드는 절대 작성하지 마세요.
2. API 명세서의 Endpoint, Method, Request/Response 구조를 100% 일치시켜야 합니다.
3. 🚨 [매우 중요: 완벽한 requirements.txt 작성]: 
   - 실행에 필요한 모든 패키지를 누락 없이 작성하세요.
   - FastAPI를 사용할 경우, 반드시 'fastapi'와 'uvicorn'을 함께 적어야 합니다.
   - Flask를 사용할 경우, 'Flask'와 'flask-cors'를 함께 적으세요.
4. 🚨 [중요: CORS 설정] 프론트엔드와의 통신을 위해 반드시 CORS 설정을 추가하세요.
""")

    user_prompt = HumanMessage(content=f"""
[API 명세서]:\n{api_contract}\n
[아키텍처]:\n{architecture}\n
[현재 requirements.txt]:\n{req_content}\n
[현재 작성된 코드]:\n{existing_code_content}\n
🚨 [QA 테스트 결과(에러)]: {test_results}  <--- 이 줄 추가!
🚨 [Supervisor 지시사항]: {supervisor_directive}  <--- 이 줄 추가/수정!
이 피드백과 API 명세서를 바탕으로 코드를 생성/수정하세요.
""")

    response = llm_with_tools.invoke([system_prompt, user_prompt])
    if response.tool_calls:
        for tool_call in response.tool_calls:
            if tool_call["name"] == "write_code_to_workspace":
                result = write_code_to_workspace.invoke(tool_call["args"])
                print(f"   -> 💻 {result}")

    return {}
