from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from state import AgentState
from tools import write_code_to_workspace, read_file_from_workspace
from config import DEFAULT_MODEL, TEMPERATURE

llm = ChatOpenAI(model=DEFAULT_MODEL, temperature=TEMPERATURE)
llm_with_tools = llm.bind_tools([write_code_to_workspace, read_file_from_workspace])

def developer_agent(state: AgentState):
    project_name = state.get("project_name", "default_project")
    print(f"\n🤖 [Dev Agent]: '{project_name}' 프로젝트의 코드를 작성 중입니다...")
    
    requirements = state.get("requirements", "요구사항이 없습니다.")
    architecture = state.get("architecture", "아키텍처 설계가 없습니다.") 

    error_feedback = ""
    if state.get("test_results", "").startswith("FAIL"):
        error_feedback = f"\n이전 코드 검사에서 다음 오류/취약점이 발견되었습니다. 이를 수정하여 다시 작성하세요:\n{state['messages'][-1].content}"

    system_prompt = SystemMessage(content=f"""당신은 수석 소프트웨어 엔지니어입니다. 
주어진 요구사항에 맞는 코드를 작성하고 도구를 사용해 저장하세요. 
도구를 호출할 때 'project_name' 파라미터 값으로 반드시 '{project_name}'을 입력해야 합니다.

[중요 지침] 
1. 도구를 여러 번 호출하여 **반드시 메인 파이썬 코드(.py)와 requirements.txt를 모두** 생성하고 저장해야 합니다. 파이썬 코드 없이 requirements.txt만 저장하면 절대 안 됩니다.
2. 현재 시스템은 **Python 3.13** 환경입니다. requirements.txt 작성 시 반드시 최신 안정화 버전(예: Flask>=3.0, FastAPI 최신 등)을 사용하세요.
3. 실행 중 'ImportError'나 버전 충돌 에러가 발생하면, requirements.txt와 파이썬 코드를 모두 최신 버전에 맞게 수정하여 도구로 다시 덮어쓰세요.
4. 추가 수정 요청이 들어온 경우, 'read_file_from_workspace' 도구를 사용해 반드시 'docs/specification.md'를 먼저 읽고 기존 시스템 규칙을 위반하지 않도록 코드를 작성하세요.""")
    
    user_prompt = HumanMessage(content=f"요구사항:\n{requirements}\n\n아키텍처 설계도:\n{architecture}\n\n{error_feedback}") 
    response = llm_with_tools.invoke([system_prompt, user_prompt])
    
    code_files_updated = {}
    if response.tool_calls:
        for tool_call in response.tool_calls:
            if tool_call["name"] == "write_code_to_workspace":
                result = write_code_to_workspace.invoke(tool_call["args"])
                print(f"   -> 💾 {result}")
                code_files_updated[tool_call["args"]["filename"]] = tool_call["args"]["code"]
    
    return {"code_files": code_files_updated}
