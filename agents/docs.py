# agents/docs.py 전체 교체
import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from state import AgentState
from tools import write_code_to_workspace, read_file_from_workspace
from config import DEFAULT_MODEL, TEMPERATURE, WORKSPACE_DIR

llm = ChatOpenAI(model=DEFAULT_MODEL, temperature=TEMPERATURE)
llm_with_tools = llm.bind_tools([write_code_to_workspace, read_file_from_workspace])

def documentation_agent(state: AgentState):
    project_name = state.get("project_name", "unknown_project")
    print("\n🤖 [Tech Writer Agent]: QA를 통과한 전체 코드를 바탕으로 극도로 상세한 공식 문서를 작성합니다...")
    
    project_dir = os.path.join(WORKSPACE_DIR, project_name)
    
    # [핵심] 상태(State) 대신 실제 로컬 폴더(workspace)에서 모든 .py 파일을 읽어옵니다.
    code_files = {}
    if os.path.exists(project_dir):
        for root, _, files in os.walk(project_dir):
            if "venv" in root or "__pycache__" in root:
                continue
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, project_dir)
                    with open(file_path, "r", encoding="utf-8") as f:
                        code_files[rel_path] = f.read()
                        
    code_content = "\n\n".join([f"--- {filename} ---\n{code}" for filename, code in code_files.items()])
    
    system_prompt = SystemMessage(content=f"""당신은 시니어 테크니컬 라이터입니다. 
주어진 최종 코드를 분석하여 다음 2개의 문서를 작성하고 도구를 사용하여 저장하세요.

1. 파일명: 'README.md'
   - 내용: 프로젝트 개요, 실행 방법 (가상환경 활성화 및 패키지 설치 포함), 환경 변수 세팅법, 주요 기능 설명

2. 파일명: 'docs/specification.md'
   - 목적: 향후 다른 AI 에이전트들이 코드를 수정할 때 시스템 규칙을 파악할 수 있는 완벽한 '단일 진실 공급원(SSOT)'입니다.
   - [핵심] 존재하는 모든 .py 파일에 대해 다음을 명시하세요:
     * 파일 경로 및 목적
     * 클래스 정의 (속성 및 메서드)
     * 모든 함수의 이름, 목적, 입력 파라미터(Type, 필수 여부), 반환값(Type), 발생 가능한 예외(Exceptions)
   - API 엔드포인트가 있다면 Request/Response 예시 JSON을 반드시 포함하세요.

도구 호출 시 'project_name'은 '{project_name}'을 사용하세요.""")
    user_prompt = HumanMessage(content=f"전체 프로젝트 최종 완성 코드:\n{code_content}")
    
    response = llm_with_tools.invoke([system_prompt, user_prompt])
    if response.tool_calls:
        for tool_call in response.tool_calls:
            if tool_call["name"] == "write_code_to_workspace":
                result = write_code_to_workspace.invoke(tool_call["args"])
                print(f"   -> 📝 {result}")
    return state
