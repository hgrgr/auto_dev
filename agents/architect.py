# agents/architect.py
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from state import AgentState
from tools import write_code_to_workspace
from config import DEFAULT_MODEL, TEMPERATURE

llm = ChatOpenAI(model=DEFAULT_MODEL, temperature=TEMPERATURE)
llm_with_tools = llm.bind_tools([write_code_to_workspace])

def architect_agent(state: AgentState):
    project_name = state.get("project_name", "unknown_project")
    print(f"\n🤖 [Architect Agent]: '{project_name}'의 명세서를 바탕으로 시스템 아키텍처를 설계합니다...")
    
    requirements = state.get("requirements", "요구사항이 없습니다.")
    
    system_prompt = SystemMessage(content=f"""당신은 경험이 풍부한 수석 소프트웨어 아키텍트입니다.
PM이 작성한 요구사항 명세서를 분석하여 최적의 시스템 아키텍처, 디렉토리 구조, 데이터베이스 스키마를 설계하세요.

다음 내용을 마크다운으로 상세히 작성하세요:
1. 전체 디렉토리 및 파일 구조 트리 (어떤 파일에 어떤 기능이 들어갈지 명확히 분리할 것)
2. 데이터베이스 스키마 및 모델 설계 (테이블 명, 컬럼, 타입, 관계 등)
3. 주요 컴포넌트 간의 데이터 흐름 및 사용 기술 스택 (Python 3.13 기준)

도구를 사용하여 작성된 내용을 반드시 'docs/architecture.md' 파일로 저장하세요.
도구 호출 시 'project_name'은 '{project_name}'을 사용하세요.""")
    
    user_prompt = HumanMessage(content=f"요구사항 명세서:\n{requirements}")
    
    response = llm_with_tools.invoke([system_prompt, user_prompt])
    
    if response.tool_calls:
        for tool_call in response.tool_calls:
            if tool_call["name"] == "write_code_to_workspace":
                result = write_code_to_workspace.invoke(tool_call["args"])
                print(f"   -> 📐 {result}")
                
    print("   -> 📐 아키텍처 설계 완료.")
    return {"architecture": response.content}
