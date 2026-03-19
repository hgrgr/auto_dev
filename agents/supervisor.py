import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from state import AgentState
from config import DEFAULT_MODEL, TEMPERATURE, AGENT_CAPABILITIES, WORKSPACE_DIR

llm = ChatOpenAI(model=DEFAULT_MODEL, temperature=TEMPERATURE)

def supervisor_agent(state: AgentState):
    project_name = state.get("project_name", "unknown")
    print(f"\n🧐 [Supervisor Agent]: '{project_name}' 프로젝트의 교착 상태를 분석합니다...")
    
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
    
    system_prompt = SystemMessage(content=f"""당신은 AI 소프트웨어 팩토리의 수석 문제 해결사(Supervisor)입니다.
현재 발생한 에러를 분석하여 '누구의 영역'인지 판단하고 정석적인 소프트웨어 공학 절차에 따라 지시하세요.

{AGENT_CAPABILITIES}

[현재 디스크 상의 실제 파일 목록]
{actual_files_str}

[판단 및 지시 가이드]
1. QA가 'ModuleNotFoundError'나 '임포트 에러'를 보고했는데, 실제 파일 목록에 해당 파일이 없다면?
   -> TARGET: architect
   -> DIRECTIVE: 설계도에 누락된 파일을 추가하고 모듈 구조를 수정하라.
2. 특정 라이브러리 버전 문제(예: Werkzeug, Flask 등)나 코드 로직 에러라면?
   -> TARGET: developer
   -> DIRECTIVE: 라이브러리 버전을 고정(Pinning)하거나 최신 API에 맞게 코드를 수정하라.
3. 파일은 존재하지만 QA가 모듈을 못 찾는다면?
   -> 진단: 파일 위치 오류 (Path Mismatch).
   -> 지시: "현재 requirements.txt가 하위 폴더에 있습니다. 이를 프로젝트 루트 디렉토리(예: {project_name}/requirements.txt)로 옮겨서 다시 작성하세요."

[응답 포맷]
TARGET: [architect 또는 developer 또는 human_approval]
DIRECTIVE: [구체적인 지시 내용]""")

    user_prompt = HumanMessage(content=f"최종 QA 에러 리포트:\n{qa_feedback}")
    
    response = llm.invoke([system_prompt, user_prompt])
    result_text = response.content.strip()
    
    target = "developer"
    directive = "이전 에러를 확인하고 코드를 수정하세요."
    
    # [수정됨] t_val 변수명 불일치 해결
    for line in result_text.split('\n'):
        if line.startswith("TARGET:"):
            t_val = line.replace("TARGET:", "").strip().lower()
            if "architect" in t_val: 
                target = "architect"
            elif "human" in t_val: # 기존에 target_val로 되어있던 오타 수정
                target = "human_approval"
            else: 
                target = "developer"
        elif line.startswith("DIRECTIVE:"):
            directive = line.replace("DIRECTIVE:", "").strip()

    print(f"   -> 🎯 타겟: {target}\n   -> 📝 지시: {directive}")
    return {"qa_attempts": 0, "supervisor_decision": target, "supervisor_directive": directive}
