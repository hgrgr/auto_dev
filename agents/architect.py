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
    if state.get("test_results", "").startswith("FAIL"):
        error_feedback = f"\n[QA 에러 피드백]\n{state['messages'][-1].content}"
        
    # [추가됨] Supervisor의 특별 지시사항 주입
    supervisor_directive = state.get("supervisor_directive", "")
    if supervisor_directive:
        error_feedback += f"\n\n🚨 [SUPERVISOR 긴급 지시사항 (기존 설계를 엎더라도 이 지시를 따를 것)]\n{supervisor_directive}"
    
    existing_architecture = state.get("architecture", "")
    is_update = bool(existing_architecture)
    
    # 아키텍처 업데이트 상황일 때의 프롬프트 구성
    if is_update:
        print("   -> 🏗️ [Architect Agent]: 기존 설계도를 파괴하지 않고 새로운 기능을 안전하게 추가 통합합니다...")
        arch_context = f"\n\n[기존 아키텍처 설계도 (절대 훼손하지 말 것)]\n{existing_architecture}"
    else:
        arch_context = ""

    system_prompt = SystemMessage(content=f"""당신은 수석 소프트웨어 아키텍트입니다.
요구사항 명세서와 QA 피드백을 분석하여 최적의 시스템 아키텍처를 설계하세요.

[절대 규칙 - 엄수]
1. Python 3.13 생태계만을 사용하세요. (Node.js 금지)
2. 디렉토리 구조와 파일명은 반드시 파이썬 확장자(.py)여야 합니다.
3. [가장 중요] 만약 '기존 아키텍처 설계도'가 주어졌다면, 절대 기존 구조를 완전히 갈아엎지 마세요! 기존 시스템의 무결성을 유지하면서, 새로운 기능에 필요한 파일이나 함수만 '추가'하거나 최소한으로 '변경'하는 방식으로 설계도를 업데이트하세요.

작성된 내용을 'docs/architecture.md' 파일로 저장하세요.
도구 호출 시 'project_name'은 '{project_name}'을 사용하세요.""")
    
    user_prompt = HumanMessage(content=f"최신 요구사항 명세서:\n{requirements}{arch_context}\n{error_feedback}")
    
    response = llm_with_tools.invoke([system_prompt, user_prompt])
    
    if response.tool_calls:
        for tool_call in response.tool_calls:
            if tool_call["name"] == "write_code_to_workspace":
                result = write_code_to_workspace.invoke(tool_call["args"])
                print(f"   -> 📐 {result}")
                
    print("   -> 📐 아키텍처 설계 완료.")
    
    # [핵심] 아키텍처가 재설계되었으므로 qa_attempts를 0으로 초기화하여 새 출발하게 해줌
    return {"architecture": response.content, "qa_attempts": 0}
