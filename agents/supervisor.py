# agents/supervisor.py 전체 교체
import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from state import AgentState
from config import DEFAULT_MODEL, TEMPERATURE

llm = ChatOpenAI(model=DEFAULT_MODEL, temperature=TEMPERATURE)

def supervisor_agent(state: AgentState):
    print("\n🧐 [Supervisor Agent]: 데드락(Deadlock) 감지! 3회 이상 해결되지 않은 악성 에러를 심층 분석합니다...")
    
    qa_feedback = state["messages"][-1].content if state.get("messages") else "피드백 없음"
    
    system_prompt = SystemMessage(content="""당신은 AI 소프트웨어 팩토리의 수석 문제 해결사(Supervisor)입니다.
현재 하위 에이전트(Dev, Architect)들이 동일한 에러를 3회 이상 해결하지 못해 시스템이 무한 루프에 빠졌습니다.

QA의 에러 리포트를 심층 분석하여 이 교착 상태를 깰 책임자를 지정하세요.
1. 'architect': Dev가 코드를 수정해도 계속 라이브러리 충돌이 나거나, 파일 간의 순환 참조가 구조적으로 심각하게 꼬여서 아키텍처 자체를 갈아엎어야 하는 경우.
2. 'developer': 아키텍처는 맞는데 Dev가 엉뚱한 곳을 고치고 있거나 지시사항을 잘못 이해하여 발생한 문제일 경우.
3. 'human_approval': 현재 제공된 AI 도구와 환경(Python 3.13)으로는 절대 해결할 수 없는 치명적인 시스템 제약 사항인 경우 인간에게 개입을 요청합니다.

답변은 반드시 'architect', 'developer', 'human_approval' 중 하나만 출력하세요.""")

    user_prompt = HumanMessage(content=f"해결되지 않은 QA 에러 리포트:\n{qa_feedback}")
    
    response = llm.invoke([system_prompt, user_prompt])
    decision = response.content.strip().lower()
    
    if "architect" in decision:
        decision = "architect"
        print("   -> 🏗️ [판단]: 이 문제는 코딩으로 해결할 수 없습니다. Architect에게 아키텍처 전면 재설계를 지시합니다.")
    elif "human" in decision:
        decision = "human_approval"
        print("   -> 🛑 [판단]: AI의 능력 범위를 벗어난 치명적 오류입니다. 인간의 개입을 요청합니다.")
    else:
        decision = "developer"
        print("   -> ♻️ [판단]: 단순하지만 끈질긴 버그입니다. Developer에게 새로운 접근 방식으로 수정을 지시합니다.")

    # [핵심] 실무자들이 다시 3번의 기회를 가질 수 있도록 qa_attempts 카운터를 0으로 초기화!
    return {"qa_attempts": 0, "supervisor_decision": decision}
