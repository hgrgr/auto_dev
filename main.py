import os
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage

from config import RECURSION_LIMIT, WORKSPACE_DIR, MAX_QA_ATTEMPTS
from state import AgentState

# 분리된 에이전트들을 모두 임포트합니다.
from agents import (
    pm_agent, 
    backend_architect_agent, 
    backend_developer_agent, 
    frontend_architect_agent, 
    frontend_developer_agent,
    security_qa_agent, 
    documentation_agent, 
    supervisor_agent
)

# --- 라우팅(Edge) 함수 ---
def route_after_qa(state: AgentState):
    test_results = state.get("test_results", "")
    attempts = state.get("qa_attempts", 0)
    
    if test_results.startswith("FAIL"):
        if attempts >= 3:
            print(f"   -> 🚨 [System]: 에러 {attempts}회 누적! Supervisor에게 에스컬레이션합니다.")
            return "supervisor"
            
        # QA가 판별한 구체적인 에러 영역으로 정확히 분기
        if "FAIL_BACKEND_ARCH" in test_results:
            print("   -> 🏗️ [System]: 백엔드 구조 결함. Backend Architect에게 반환합니다.")
            return "backend_architect"
        elif "FAIL_FRONTEND_ARCH" in test_results:
            print("   -> 🎨 [System]: 프론트엔드 구조 결함. Frontend Architect에게 반환합니다.")
            return "frontend_architect"
        elif "FAIL_FRONTEND_DEV" in test_results:
            print("   -> ⚛️ [System]: 프론트엔드 버그 감지. Frontend Developer에게 반환합니다.")
            return "frontend_developer"
        else:
            # 기본값은 백엔드 개발자
            print("   -> 🐍 [System]: 백엔드 일반 버그 감지. Backend Developer에게 반환합니다.")
            return "backend_developer"
            
    print("   -> ✅ [System]: QA 통과. 공식 문서 작성 단계로 이동합니다.")
    return "docs"

def route_after_supervisor(state: AgentState):
    decision = state.get("supervisor_decision", "backend_developer")
    print(f"   -> 👨‍⚖️ [System]: Supervisor의 결정에 따라 '{decision}'(으)로 이동합니다.")
    # [추가됨] Supervisor가 인간의 개입을 요청한 경우 파이프라인 일시 정지(END)
    if decision == "human_approval":
        print("   -> 🛑 [System]: Supervisor가 인간의 개입을 요청했습니다. 파이프라인을 일시 정지합니다.")
        return END 
    return decision


def route_after_human(state: AgentState):
    decision = state.get("human_decision", "cancel")
    
    if decision == "retry":
        print("   -> ♻️ [System]: 인간의 명령으로 QA 카운터를 초기화하고 수정 루프를 재개합니다.")
        # 프론트/백엔드 중 어디를 고칠지 Supervisor가 판단하도록 넘김
        return "supervisor" 
        
    elif decision == "deploy":
        print("   -> 📦 [System]: 프로덕션 배포 절차를 시작합니다 (또는 종료).")
        return END
        
    elif decision == "new_feature":
        print("   -> 🚀 [System]: 새로운 요구사항이 접수되었습니다! PM Agent에게 스프린트 계획을 지시합니다.")
        return "pm" 
        
    else:
        print("   -> 🛑 [System]: 프로세스를 완전히 종료합니다.")
        return END

# --- LangGraph 워크플로우 구성 ---
workflow = StateGraph(AgentState)

# 1. 노드 등록
workflow.add_node("pm", pm_agent)
workflow.add_node("backend_architect", backend_architect_agent)
workflow.add_node("backend_developer", backend_developer_agent)
workflow.add_node("frontend_architect", frontend_architect_agent)
workflow.add_node("frontend_developer", frontend_developer_agent)
workflow.add_node("qa", security_qa_agent)
workflow.add_node("docs", documentation_agent)
workflow.add_node("supervisor", supervisor_agent)

# 2. 메인 엣지 (실행 흐름 연결)
workflow.set_entry_point("pm")

# PM -> 백엔드
workflow.add_edge("pm", "backend_architect")
workflow.add_edge("backend_architect", "backend_developer")

# 백엔드 완료 -> 프론트엔드
workflow.add_edge("backend_developer", "frontend_architect")
workflow.add_edge("frontend_architect", "frontend_developer")

# 프론트엔드 완료 -> QA 통합 테스트
workflow.add_edge("frontend_developer", "qa")

# 3. 조건부 엣지 (루프백 / 피드백 처리)
workflow.add_conditional_edges("qa", route_after_qa)
workflow.add_conditional_edges("supervisor", route_after_supervisor)
workflow.add_conditional_edges("docs", route_after_human)

# 체크포인터 설정
memory = MemorySaver()
app = workflow.compile(checkpointer=memory)


# --- 메인 실행 로직 ---
if __name__ == "__main__":
    print("🚀 Auto Dev Factory (MSA Version) Started!")
    project_name = input("프로젝트 이름을 입력하세요: ").strip()
    
    # 워크스페이스(물리적 폴더) 생성
    project_dir = os.path.join(WORKSPACE_DIR, project_name)
    os.makedirs(os.path.join(project_dir, "backend"), exist_ok=True)
    os.makedirs(os.path.join(project_dir, "frontend"), exist_ok=True)
    os.makedirs(os.path.join(project_dir, "docs"), exist_ok=True)

    config = {"configurable": {"thread_id": project_name}, "recursion_limit": RECURSION_LIMIT}
    
    try:
        current_state = app.get_state(config)
    except Exception:
        current_state = None

    # 기존 히스토리가 있는 경우 (인간 개입 루프)
    if current_state and current_state.values.get("messages"):
        print(f"\n[System] '{project_name}' 프로젝트의 기존 히스토리를 발견했습니다.")
        current_reqs = current_state.values.get("requirements", "명세서 정보가 없습니다.")
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
            new_message = HumanMessage(content=f"[추가 요구사항 업데이트]: {user_input}")
            
            # 메시지를 안전하게 이어붙이고 상태 업데이트
            current_messages = current_state.values.get("messages", [])
            app.update_state(config, {
                "human_decision": "new_feature",
                "qa_attempts": 0,
                "messages": current_messages + [new_message] 
            })
        
        # 인간의 결정에 따라 그래프 재개
        for output in app.stream(None, config=config):
            pass
        print("\n🎉 [System]: 후속 파이프라인 처리가 완료되었습니다!")

    # 프로젝트 최초 실행인 경우
    else:
        user_input = input("구현할 소프트웨어의 요구사항을 자세히 입력하세요: ")
        initial_state = {
            "messages": [HumanMessage(content=user_input)],
            "project_name": project_name,
            "qa_attempts": 0
        }
        for output in app.stream(initial_state, config=config):
            pass
        print("\n🎉 [System]: 모든 파이프라인(PM->Backend->Frontend->QA->Docs)이 완료되었습니다!")
