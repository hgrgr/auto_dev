from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage

from config import MAX_QA_ATTEMPTS, RECURSION_LIMIT
from state import AgentState
from agents import pm_agent, architect_agent, developer_agent, security_qa_agent, documentation_agent, supervisor_agent # supervisor 추가

# --- 라우팅(Edge) 함수 ---
def route_after_qa(state: AgentState):
    test_results = state.get("test_results", "")
    attempts = state.get("qa_attempts", 0)
    
    if test_results.startswith("FAIL"):
        # [핵심] 3회 이상 동일한 에러 루프에 빠지면 Supervisor 호출
        if attempts >= 3:
            print(f"   -> 🚨 [System]: 해결되지 않는 에러 {attempts}회 누적 감지! Supervisor에게 에스컬레이션(Escalation)합니다.")
            return "supervisor"
            
        # 3회 미만일 경우 실무자들이 알아서 처리
        if test_results.startswith("FAIL_ARCH"):
            print("   -> 🏗️ [System]: 구조 결함 감지. Architect Agent에게 전달합니다.")
            return "architect"
        else:
            print("   -> ♻️ [System]: 일반 버그 감지. Dev Agent에게 전달합니다.")
            return "developer"
            
    print("   -> ✅ [System]: QA 통과. 공식 문서 작성 단계로 이동합니다.")
    return "docs"

def route_after_supervisor(state: AgentState):
    decision = state.get("supervisor_decision", "human_approval")
    return decision

def route_after_human(state: AgentState):
    decision = state.get("human_decision", "cancel")
    if decision == "retry":
        print("   -> ♻️ [System]: 인간의 명령으로 QA 카운터를 초기화하고 수정 루프를 재개합니다.")
        return "developer"
    elif decision == "deploy":
        return "deploy"
    elif decision == "new_feature":
        print("   -> 🚀 [System]: 새로운 요구사항이 접수되었습니다! PM Agent에게 스프린트 계획을 지시합니다.")
        return "pm" # [추가됨] 새로운 기능 요청 시 PM으로 이동
    else:
        print("   -> 🛑 [System]: 프로세스를 완전히 종료합니다.")
        return END

# --- LangGraph 워크플로우 조립 ---
workflow = StateGraph(AgentState)

workflow.add_node("pm", pm_agent)
workflow.add_node("architect", architect_agent)
workflow.add_node("developer", developer_agent)
workflow.add_node("qa", security_qa_agent)
workflow.add_node("supervisor", supervisor_agent) # [노드 추가]
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
    "supervisor": "supervisor",
    "docs": "docs"
})
workflow.add_conditional_edges("supervisor", route_after_supervisor, {
    "architect": "architect",
    "developer": "developer",
    "human_approval": "human_approval"
})
workflow.add_edge("docs", "human_approval")

workflow.add_conditional_edges("human_approval", route_after_human, {
    "pm": "pm",
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
            print("\n=======================================================")
            print("✨ [개발 및 QA 완료] 배포 승인 대기 중입니다.")
            print("=======================================================")
            
            # [해결 1] PM이 작성한 현재 시스템 명세서를 화면에 출력해 줍니다.
            # state.values 를 통해 상태 데이터에 접근합니다.
            current_reqs = state.values.get("requirements", "명세서 정보가 없습니다.")
            print("\n📋 [현재 개발된 시스템 기능 요약]")
            print("-" * 60)
            print(current_reqs)
            print("-" * 60)
            
            print("\n어떻게 처리하시겠습니까?")
            print("  [y] 승인 및 프로덕션 배포")
            print("  [r] 현재 요구사항 내에서 QA 및 코드 강제 재수정")
            print("  [n] 취소 및 종료")
            print("  [기타 텍스트] 추가하고 싶은 새로운 기능이나 요구사항을 자유롭게 입력하세요.")
            
            user_input = input("\n선택 또는 새 요구사항 입력: ").strip()

            if user_input.lower() == 'y':
                print("승인 완료. 배포를 진행합니다.")
                app.update_state(config, {"human_decision": "deploy"})
            elif user_input.lower() == 'r':
                print("수정 루프를 재개합니다.")
                app.update_state(config, {"human_decision": "retry", "qa_attempts": 0})
            elif user_input.lower() == 'n':
                print("배포가 취소되었습니다.")
                app.update_state(config, {"human_decision": "cancel"})
            else:
                print("\n📝 새로운 요구사항이 접수되었습니다. 다음 스프린트(버전업)를 시작합니다.")
                
                # [해결 2] 기존 메시지를 불러올 필요 없이, 새 메시지만 보내면 LangGraph가 알아서 병합합니다.
                new_message = HumanMessage(content=f"[추가 요구사항 업데이트]: {user_input}")
                
                app.update_state(config, {
                    "human_decision": "new_feature", 
                    "qa_attempts": 0,
                    "messages": [new_message] # operator.add 덕분에 자동으로 기존 대화에 추가됨
                })
                
            for event in app.stream(None, config=config, stream_mode="updates"):
                node_name = list(event.keys())[0]
                print(f"   ⚙️ [System Debug]: '{node_name}' 노드 작업 완료")
