# agents/architect.py 전체 교체
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from state import AgentState
from tools import write_code_to_workspace
from config import DEFAULT_MODEL, TEMPERATURE

llm = ChatOpenAI(model=DEFAULT_MODEL, temperature=TEMPERATURE)
llm_with_tools = llm.bind_tools([write_code_to_workspace])

def architect_agent(state: AgentState):
    project_name = state.get("project_name", "unknown_project")
    print(f"\n🤖 [Architect Agent]: '{project_name}'의 시스템 아키텍처를 설계합니다...")
    
    requirements = state.get("requirements", "요구사항이 없습니다.")
    
    # [핵심 추가] QA에서 FAIL_ARCH로 넘어온 경우 피드백 수용
    error_feedback = ""
    if state.get("test_results", "").startswith("FAIL_ARCH"):
        print("   -> ⚠️ [System]: 이전 설계에 치명적 결함이 발견되어 재설계를 진행합니다.")
        error_feedback = f"\n[QA 에이전트의 구조적 결함 피드백]\n이전 설계에 다음 문제가 있었습니다. 이를 반영하여 아키텍처를 전면 수정하세요:\n{state['messages'][-1].content}"
    
    system_prompt = SystemMessage(content=f"""당신은 경험이 풍부한 수석 소프트웨어 아키텍트입니다.
요구사항 명세서와 (만약 있다면) QA의 결함 피드백을 분석하여 최적의 시스템 아키텍처를 설계하세요.

[절대 규칙 - 엄수]
1. 오직 Python 3.13 생태계만을 사용하여 설계해야 합니다. (Node.js, JS 절대 금지)
2. 디렉토리 구조와 파일명은 반드시 파이썬 확장자(.py)를 가져야 합니다.
3. 각 .py 파일별 상세 스펙(함수명, 파라미터, 반환값, 비즈니스 로직)을 명확히 작성하세요.

도구를 사용하여 작성된 내용을 반드시 'docs/architecture.md' 파일로 저장하세요.
도구 호출 시 'project_name'은 '{project_name}'을 사용하세요.""")
    
    user_prompt = HumanMessage(content=f"요구사항 명세서:\n{requirements}\n{error_feedback}")
    
    response = llm_with_tools.invoke([system_prompt, user_prompt])
    
    if response.tool_calls:
        for tool_call in response.tool_calls:
            if tool_call["name"] == "write_code_to_workspace":
                result = write_code_to_workspace.invoke(tool_call["args"])
                print(f"   -> 📐 {result}")
                
    print("   -> 📐 아키텍처 설계 완료.")
    
    # [핵심] 아키텍처가 재설계되었으므로 qa_attempts를 0으로 초기화하여 새 출발하게 해줌
    return {"architecture": response.content, "qa_attempts": 0}
