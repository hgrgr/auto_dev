# agents/supervisor.py 전체 교체 (보완된 버전)
import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from state import AgentState
from config import DEFAULT_MODEL, TEMPERATURE, AGENT_CAPABILITIES, WORKSPACE_DIR

llm = ChatOpenAI(model=DEFAULT_MODEL, temperature=TEMPERATURE)

def supervisor_agent(state: AgentState):
    project_name = state.get("project_name", "unknown")
    print(f"\n🧐 [Supervisor Agent]: '{project_name}' 프로젝트의 교착 상태를 분석합니다...")
    
    # [핵심 보완 1] 실제 디스크상의 파일 목록을 직접 스캔합니다.
    project_dir = os.path.join(WORKSPACE_DIR, project_name)
    actual_files = []
    if os.path.exists(project_dir):
        for root, _, files in os.walk(project_dir):
            if "venv" in root or "__pycache__" in root: continue
            for f in files:
                rel_path = os.path.relpath(os.path.join(root, f), project_dir)
                actual_files.append(rel_path)
    
    actual_files_str = "\n".join(actual_files) if actual_files else "생성된 파일 없음"
    qa_feedback = state["messages"][-1].content if state.get("messages") else "피드백 없음"
    
    # [핵심 보완 2] 프롬프트에 '실제 파일 목록'과 '진단 가이드'를 강화합니다.
    system_prompt = SystemMessage(content=f"""당신은 AI 소프트웨어 팩토리의 수석 문제 해결사(Supervisor)입니다.
현재 발생한 에러를 분석하여 '누구의 영역'인지 판단하고 정석적인 소프트웨어 공학 절차에 따라 지시하세요.

[에이전트 권한 및 능력]
{AGENT_CAPABILITIES}

[현재 디스크 상의 실제 파일 목록]
{actual_files_str}

[판단 및 지시 가이드 (정석 아키텍처 루프)]
1. QA가 'ModuleNotFoundError'나 '임포트 에러'를 보고했는데, 실제 파일 목록에 해당 파일이 없다면?
   -> 진단: 아키텍트의 설계 누락 혹은 경로 설정 오류.
   -> TARGET: architect
   -> DIRECTIVE: "현재 실제 파일 목록에 'OOO' 파일이 누락되어 임포트 에러가 발생합니다. 아키텍처 설계도(architecture.md)에 이 파일을 명시적으로 추가하고, 폴더 구조와 __init__.py 연결 관계를 올바르게 수정하세요."

2. 파일은 존재하는데 실행 에러(Syntax, Logic, 패키지 미설치 등)가 난다면?
   -> 진단: 개발자의 구현 실수.
   -> TARGET: developer
   -> DIRECTIVE: "파일은 존재하나 내부 로직이나 패키지 설정에 문제가 있습니다. 에러 로그를 분석하여 코드를 수정하세요."

[응답 포맷]
TARGET: [architect 또는 developer 또는 human_approval]
DIRECTIVE: [구체적인 지시 내용]""")

    user_prompt = HumanMessage(content=f"최종 QA 에러 리포트:\n{qa_feedback}")
    
    response = llm.invoke([system_prompt, user_prompt])
    result_text = response.content.strip()
    
    # 파싱 로직 (기존과 동일)
    target = "developer"
    directive = "이전 에러를 확인하고 코드를 수정하세요."
    for line in result_text.split('\n'):
        if line.startswith("TARGET:"):
            t_val = line.replace("TARGET:", "").strip().lower()
            if "architect" in t_val: target = "architect"
            elif "human" in target_val: target = "human_approval"
            else: target = "developer"
        elif line.startswith("DIRECTIVE:"):
            directive = line.replace("DIRECTIVE:", "").strip()

    print(f"   -> 🎯 타겟: {target}\n   -> 📝 지시: {directive}")
    return {"qa_attempts": 0, "supervisor_decision": target, "supervisor_directive": directive}
