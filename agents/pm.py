from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from state import AgentState
from config import DEFAULT_MODEL, TEMPERATURE

llm = ChatOpenAI(model=DEFAULT_MODEL, temperature=TEMPERATURE)

def pm_agent(state: AgentState):
    project_name = state.get("project_name", "unknown_project")
    print(f"\n🤖 [PM Agent]: '{project_name}'의 사용자 요구사항을 분석하여 명세서를 작성합니다...")
    
    if state.get("messages"):
        first_msg = state["messages"][0]
        user_message = first_msg.content if hasattr(first_msg, 'content') else first_msg[1]
    else:
        user_message = "요구사항 없음"
        
    # agents/pm.py 내부의 system_prompt 수정
    system_prompt = SystemMessage(content="""당신은 뛰어난 역량을 가진 IT 프로덕트 매니저(PM)이자 시스템 아키텍트입니다.
사용자의 모호한 요구사항을 분석하여 개발자가 즉시 코딩을 시작할 수 있는 수준의 '기술 명세서(PRD)'를 작성해야 합니다.

[절대 규칙]
이 팩토리는 파이썬(Python) 전용 공장입니다. 추천 기술 스택은 **반드시 Python 3.13 기반(FastAPI, Flask 등)**으로만 한정해야 하며, 절대 Node.js, Java, Go 등을 언급하지 마세요.

프로젝트 개요, 기능 목록, API 엔드포인트 스펙, 보안 요구사항 등을 마크다운 형식으로 정리하세요.""")

    user_prompt = HumanMessage(content=f"최초 사용자 요구사항: {user_message}")
    
    response = llm.invoke([system_prompt, user_prompt])
    print("   -> 📝 명세서 작성 완료.")
    return {"requirements": response.content}
