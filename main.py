# main.py
from dotenv import load_dotenv
load_dotenv()

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage

from state import AgentState
from agents import (
    pm_agent, developer_agent, security_qa_agent, documentation_agent, MAX_QA_ATTEMPTS
)

# --- 라우팅(Edge) 함수 ---
def route_after_qa(state: AgentState):
    if state.get("test_results", "").startswith("FAIL"):
        if state.get("qa_attempts", 0) >= MAX_QA_ATTEMPTS:
            print(f"   -> 🛑 [System]: 최대 QA 재시도 횟수({MAX_QA_ATTEMPTS}회)를 초과했습니다.")
            return "human_approval"
        print("   -> ♻️ [System]: Dev Agent에게 코드 수정을 지시합니다.")
        return "developer"
    print("   -> ✅ [System]: QA 통과. 공식 문서 작성 단계로 이동합니다.")
    return "docs"

def route_after_human(state: AgentState):
    decision = state.get("human_decision", "cancel")
    if decision == "retry":
        print("   -> ♻️ [System]: 인간의 명령으로 QA 카운터를 초기화하고 수정 루프를 재개합니다.")
        return "developer"
    elif decision == "deploy":
        return "deploy"
    else:
        print("   -> 🛑 [System]: 프로세스를 완전히 종료합니다.")
        return END

# --- LangGraph 워크플로우 조립 ---
workflow = StateGraph(AgentState)

workflow.add_node("pm", pm_agent)
workflow.add_node("developer", developer_agent)
workflow.add_node("qa", security_qa_agent)
workflow.add_node("docs", documentation_agent)
workflow.add_node("human_approval", lambda state: {})
workflow.add_node("deploy", lambda state: print("🚀 [DevOps]: 프로덕션에 배포합니다!"))

workflow.set_entry_point("pm")
workflow.add_edge("pm", "developer")
workflow.add_edge("developer", "qa")
workflow.add_conditional_edges("qa", route_after_qa, {
    "developer": "developer",
    "docs": "docs",
    "human_approval": "human_approval"
})
workflow.add_edge("docs", "human_approval")
workflow.add_conditional_edges("human_approval", route_after_human, {
    "developer": "developer",
    "deploy": "deploy",
    END: END
})
workflow.add_edge("deploy", END)

memory = MemorySaver()
app = workflow.compile(checkpointer=memory, interrupt_before=["human_approval"])

# --- 실행 루프 ---
if __name__ == "__main__":
    project_id = "secure_logger_v2"
    config = {
        "configurable": {"thread_id": project_id},
        "recursion_limit": 100
    }
    initial_input = {
        "project_name": project_id, 
        "messages": [HumanMessage(content="보안이 강화된 간단한 로깅 웹서버를 만들어줘. 이번엔 문서화까지 부탁해.")]
    }

    print(f"=== 팩토리 가동 시작 (프로젝트: {project_id}) ===")
    for event in app.stream(initial_input, config=config):
        pass

    while True:
        state = app.get_state(config)
        if not state.next:
            break 
            
        if state.next[0] == "human_approval":
            print("\n[인간 개입 필요] 시스템이 배포 승인을 대기 중이거나 최대 재시도 횟수에 도달했습니다.")
            print("어떻게 처리하시겠습니까?")
            print("  [y] 승인 및 배포 진행")
            print("  [r] 추가 QA 및 수정 진행 (카운터 0으로 초기화)")
            print("  [n] 취소 및 종료")
            user_input = input("선택 (y/r/n): ").strip().lower()

            if user_input == 'y':
                print("승인 완료. 배포를 진행합니다.")
                app.update_state(config, {"human_decision": "deploy"})
            elif user_input == 'r':
                print("수정 루프를 재개합니다. Dev Agent에게 다시 제어권을 넘깁니다.")
                app.update_state(config, {"human_decision": "retry", "qa_attempts": 0})
            else:
                print("배포가 취소되었습니다.")
                app.update_state(config, {"human_decision": "cancel"})
                
            for event in app.stream(None, config=config):
                pass
