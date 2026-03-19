# agents/supervisor.py 전체 교체
import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from state import AgentState
from config import DEFAULT_MODEL, TEMPERATURE, AGENT_CAPABILITIES

llm = ChatOpenAI(model=DEFAULT_MODEL, temperature=TEMPERATURE)

def supervisor_agent(state: AgentState):
    print("\n🧐 [Supervisor Agent]: 데드락 감지! 에이전트 권한 명세서를 바탕으로 에러를 심층 분석합니다...")
    
    qa_feedback = state["messages"][-1].content if state.get("messages") else "피드백 없음"
    
    system_prompt = SystemMessage(content=f"""당신은 AI 소프트웨어 팩토리의 수석 문제 해결사(Supervisor)입니다.
현재 하위 에이전트들이 에러를 3회 이상 해결하지 못해 무한 루프에 빠졌습니다.

다음 [에이전트 권한 명세서]를 읽고, 현재 발생한 에러가 누구의 권한 범위를 벗어났기 때문에 발생한 데드락인지 정확히 진단하세요.
{AGENT_CAPABILITIES}

진단이 끝나면 이 문제를 해결할 담당자를 지정하고, 그 담당자의 권한에 맞는 구체적인 해결 지시(Directive)를 내리세요.
(예시: 에러가 SSL 인증서 누락인데 Developer는 인증서 생성 권한이 없다면, Developer에게 "인증서 생성 권한이 없으므로 코드 내에서 SSL 설정을 해제(Bypass)하라"고 지시해야 합니다.)

[응답 포맷 (반드시 아래 형식을 지킬 것)]
TARGET: [architect 또는 developer 또는 human_approval]
DIRECTIVE: [해당 에이전트가 수행해야 할 구체적인 행동 지침]""")

    user_prompt = HumanMessage(content=f"해결되지 않은 QA 에러 리포트:\n{qa_feedback}")
    
    response = llm.invoke([system_prompt, user_prompt])
    result_text = response.content.strip()
    
    # 텍스트 파싱
    target = "developer"
    directive = "이전 에러를 확인하고 코드를 수정하세요."
    
    for line in result_text.split('\n'):
        if line.startswith("TARGET:"):
            target_val = line.replace("TARGET:", "").strip().lower()
            if "architect" in target_val: target = "architect"
            elif "human" in target_val: target = "human_approval"
            else: target = "developer"
        elif line.startswith("DIRECTIVE:"):
            directive = line.replace("DIRECTIVE:", "").strip()

    if target == "architect":
        print(f"   -> 🏗️ [판단]: Architect의 설계 수정이 필요합니다.\n   -> 📝 [지시]: {directive}")
    elif target == "human_approval":
        print(f"   -> 🛑 [판단]: AI 권한 밖의 문제입니다. 인간의 개입을 요청합니다.\n   -> 📝 [지시]: {directive}")
    else:
        print(f"   -> ♻️ [판단]: Developer의 코드 우회/수정이 필요합니다.\n   -> 📝 [지시]: {directive}")

    return {"qa_attempts": 0, "supervisor_decision": target, "supervisor_directive": directive}
