from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage

from config import MAX_QA_ATTEMPTS, RECURSION_LIMIT
from state import AgentState
from agents import pm_agent, architect_agent, developer_agent, security_qa_agent, documentation_agent

# --- 라우팅(Edge) 함수 ---
# main.py 내부의 라우팅 부분 수정
def route_after_qa(state: AgentState):
    test_results = state.get("test_results", "")
    
    if test_results.startswith("FAIL"):
        if state.get("qa_attempts", 0) >= MAX_QA_ATTEMPTS:
            print(f"   -> 🛑 [System]: 최대 QA 재시도 횟수({MAX_QA_ATTEMPTS}회)를 초과했습니다.")
            return "human_approval"
            
        # [핵심 로직] 에러 종류에 따라 분기
        if test_results.startswith("FAIL_ARCH"):
            print("   -> 🏗️ [System]: 치명적 구조 결함 발견! Architect Agent에게 재설계를 지시합니다.")
            return "architect"
        else:
            print("   -> ♻️ [System]: 단순 버그 발견! Dev Agent에게 코드 수정을 지시합니다.")
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
workflow.add_node("architect", architect_agent)
workflow.add_node("developer", developer_agent)
workflow.add_node("qa", security_qa_agent)
workflow.add_node("docs", documentation_agent)
workflow.add_node("human_approval", lambda state: {})
workflow.add_node("deploy", lambda state: print("🚀 [DevOps]: 프로덕션에 배포합니다!"))

workflow.set_entry_point("pm")
workflow.add_edge("pm", "architect")
workflow.add_edge("architect", "developer")
workflow.add_edge("developer", "qa")
workflow.add_conditional_edges("qa", route_after_qa, {
    "architect": "architect",
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
    project_id = "secure_logger_v5"
    
    config = {
        "configurable": {"thread_id": project_id},
        "recursion_limit": RECURSION_LIMIT
    }
    
    initial_input = {
        "project_name": project_id, 
        "messages": [HumanMessage(content="보안이 강화된 간단한 로깅 웹서버를 만들어줘.")]
    }

    print(f"=== 팩토리 가동 시작 (프로젝트: {project_id}) ===")
    
    try:
        # 변경됨: stream_mode를 "updates"로 명시하고, 내부 이벤트를 강제로 프린트하여 흐름을 추적합니다.
        for event in app.stream(initial_input, config=config, stream_mode="updates"):
            # 어떤 에이전트 노드가 실행되었는지 디버깅 출력
            node_name = list(event.keys())[0]
            print(f"   ⚙️ [System Debug]: '{node_name}' 노드 작업 완료")
            
    except Exception as e:
        print(f"\n🚨 [치명적 에러 발생]: {e}")

    while True:
        state = app.get_state(config)
        
        if not state.next:
            print("\n🏁 [System]: 프로세스가 완료되었거나 더 이상 진행할 노드가 없습니다.")
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
                
            # 변경됨: 인간 개입 이후의 흐름도 출력
            for event in app.stream(None, config=config, stream_mode="updates"):
                node_name = list(event.keys())[0]
                print(f"   ⚙️ [System Debug]: '{node_name}' 노드 작업 완료")
