import os
from config import RECURSION_LIMIT, WORKSPACE_DIR
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
    print("=== 🏭 AI 소프트웨어 팩토리 가동 ===")

    # [기능 1] Workspace 내의 기존 프로젝트 목록 스캔 및 출력
    os.makedirs(WORKSPACE_DIR, exist_ok=True) # 폴더가 없으면 생성
    existing_projects = [d for d in os.listdir(WORKSPACE_DIR) if os.path.isdir(os.path.join(WORKSPACE_DIR, d))]
    existing_projects.sort() # 이름순 정렬

    if not existing_projects:
        print("\n📂 현재 생성된 프로젝트가 없습니다. (비어 있음)")
    else:
        print("\n📂 [현재 존재하는 프로젝트 목록]")
        for i, proj in enumerate(existing_projects):
            print(f"  [{i+1}] {proj}")

    print("\n새로 만들 프로젝트 이름을 입력하거나, 기존 프로젝트를 이어서 하려면 '번호'를 입력하세요.")
    user_choice = input("선택 또는 새 프로젝트명 입력: ").strip()

    # 번호를 입력했는지, 새로운 텍스트를 입력했는지 판별
    project_id = user_choice
    if user_choice.isdigit():
        idx = int(user_choice) - 1
        if 0 <= idx < len(existing_projects):
            project_id = existing_projects[idx]

    config = {
        "configurable": {"thread_id": project_id},
        "recursion_limit": RECURSION_LIMIT
    }

    project_dir = os.path.join(WORKSPACE_DIR, project_id)

    existing_reqs = ""
    existing_arch = ""
    is_resume = False

    if os.path.exists(project_dir):
        print(f"\n🔄 기존 프로젝트 '{project_id}'를 감지했습니다. 컨텍스트를 복원합니다...")
        is_resume = True

        spec_path = os.path.join(project_dir, "docs", "specification.md")
        if os.path.exists(spec_path):
            with open(spec_path, "r", encoding="utf-8") as f:
                existing_reqs = f.read()

        arch_path = os.path.join(project_dir, "docs", "architecture.md")
        if os.path.exists(arch_path):
            with open(arch_path, "r", encoding="utf-8") as f:
                existing_arch = f.read()

    # [기능 2 & 3] 기존 프로젝트 로딩 시 명세서 출력 및 사용자 관점 요약
    if is_resume:
        if existing_reqs:
            print("\n📋 [현재 프로젝트의 기술 명세서]")
            print("=" * 60)
            print(existing_reqs)
            print("=" * 60)
            
            # [수정된 로직] LLM을 호출하여 명세서 요약 및 다음 스프린트 기능 추천
            print("\n🔍 [사용자 관점 기능 요약 및 고도화 방향 분석 중...]")
            try:
                from langchain_openai import ChatOpenAI
                from config import DEFAULT_MODEL, TEMPERATURE
                
                summary_llm = ChatOpenAI(model=DEFAULT_MODEL, temperature=TEMPERATURE)
                summary_prompt = f"""당신은 통찰력 있는 프로덕트 매니저(PM)입니다. 
다음 기술 명세서를 분석하여 다음 두 가지 섹션을 작성해 주세요. 
(절대 함수명, DB 스키마 같은 기술 용어를 쓰지 말고, '일반 사용자'나 '비즈니스 관리자'가 이해하기 쉬운 언어로 작성하세요.)

1. [현재 구현된 핵심 기능]: 현재 이 서비스가 제공하는 주요 기능을 3~5줄의 글머리 기호로 요약하세요.
2. [🚀 넥스트 스텝 추천 기능]: 이 서비스의 가치를 한 단계 높이거나 사용자 경험을 극대화하기 위해, 다음 개발 단계에서 추가하면 좋을 만한 '핵심 추천 기능' 3가지를 제안하고 짧은 이유를 덧붙여주세요.

[기술 명세서 내용]
{existing_reqs}"""
                
                summary_result = summary_llm.invoke(summary_prompt).content
                print("\n" + "=" * 60)
                print(summary_result)
                print("=" * 60)
            except Exception as e:
                print(f"요약 및 추천 생성 중 오류가 발생했습니다: {e}")
                
        else:
            print("\n⚠️ 기존 프로젝트 폴더는 있으나, 명세서(specification.md)를 찾을 수 없습니다.")
            
        user_prompt = input("\n📝 위 추천을 참고하여 추가하거나 수정할 요구사항을 자유롭게 입력하세요: ").strip()


    else:
        user_prompt = input(f"\n✨ 새 프로젝트 '{project_id}'의 요구사항을 입력하세요: ").str
    
    initial_input = {
        "project_name": project_id,
        "requirements": existing_reqs,
        "architecture": existing_arch,
        "messages": [HumanMessage(content=user_prompt)]
    }

    print(f"\n=== 🚀 팩토리 가동 시작 (프로젝트: {project_id}) ===")

    try:
        for event in app.stream(initial_input, config=config, stream_mode="updates"):
            node_name = list(event.keys())[0]
            print(f"   ⚙️ [System Debug]: '{node_name}' 노드 작업 완료")
    except Exception as e:
        print(f"\n🚨 [치명적 에러 발생]: {e}")

    # --- 기존의 while True: 무한 루프 영역 (그대로 유지) ---
    while True:
        state = app.get_state(config)

        if not state.next:
            print("\n🏁 [System]: 프로세스가 완료되었거나 더 이상 진행할 노드가 없습니다.")
            break

        if state.next[0] == "human_approval":
            print("\n=======================================================")
            print("✨ [개발 및 QA 완료] 배포 승인 대기 중입니다.")
            print("=======================================================")

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
                new_message = HumanMessage(content=f"[추가 요구사항 업데이트]: {user_input}")
                app.update_state(config, {
                    "human_decision": "new_feature",
                    "qa_attempts": 0,
                    "messages": [new_message]
                })

            for event in app.stream(None, config=config, stream_mode="updates"):
                node_name = list(event.keys())[0]
                print(f"   ⚙️ [System Debug]: '{node_name}' 노드 작업 완료")
