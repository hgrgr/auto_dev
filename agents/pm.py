# agents/pm.py 전체 교체
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from state import AgentState
from config import DEFAULT_MODEL, TEMPERATURE

llm = ChatOpenAI(model=DEFAULT_MODEL, temperature=TEMPERATURE)

def pm_agent(state: AgentState):
    project_name = state.get("project_name", "unknown_project")
    existing_requirements = state.get("requirements", "")
    
    # 처음 실행인지, 추가 스프린트인지 확인
    is_update = bool(existing_requirements)
    
    if is_update:
        print(f"\n🤖 [PM Agent]: '{project_name}'의 기존 시스템에 사용자 피드백을 반영하여 명세서를 업데이트합니다...")
        context_prompt = f"[기존 명세서]\n{existing_requirements}\n\n[사용자의 새로운 추가/수정 요구사항]\n{state['messages'][-1].content}"
    else:
        print(f"\n🤖 [PM Agent]: '{project_name}'의 최초 사용자 요구사항을 분석하여 명세서를 작성합니다...")
        first_msg = state["messages"][0]
        user_message = first_msg.content if hasattr(first_msg, 'content') else first_msg[1]
        context_prompt = f"최초 사용자 요구사항: {user_message}"

    system_prompt = SystemMessage(content=f"""당신은 뛰어난 역량을 가진 IT 프로덕트 매니저(PM)입니다.
사용자의 요구사항을 분석하여 개발자가 즉시 코딩을 시작할 수 있는 수준의 '기술 명세서(PRD)'를 작성해야 합니다.

[절대 규칙]
1. 이 팩토리는 파이썬(Python 3.13) 전용입니다. (Node.js 등 타 언어 금지)
2. 만약 이것이 '추가/수정 요구사항'이라면, 절대 기존 명세서를 완전히 뒤엎지 마세요. 기존 기능을 유지한 상태에서 새로운 기능이 어떻게 통합될지 '추가된 기능' 항목을 명확히 분리하여 증분(Incremental) 업데이트를 수행하세요.

프로젝트 개요, 기존 기능 목록, 신규 추가 기능 목록, 변경되는 API 스펙 등을 마크다운 형식으로 작성하세요.""")
    
    user_prompt = HumanMessage(content=context_prompt)
    
    response = llm.invoke([system_prompt, user_prompt])
    print("   -> 📝 명세서 작성(또는 업데이트) 완료.")
    
    return {"requirements": response.content}
