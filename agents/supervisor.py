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
            if "venv" in root or "__pycache__" in root or "node_modules" in root: continue
            for f in files:
                rel_path = os.path.relpath(os.path.join(root, f), project_dir)
                actual_files.append(rel_path)
    
    actual_files_str = "\n".join(actual_files) if actual_files else "생성된 파일 없음"
    qa_feedback = state["messages"][-1].content if state.get("messages") else "피드백 없음"
    
    system_prompt = SystemMessage(content=f"""당신은 AI 소프트웨어 팩토리의 수석 문제 해결사(Supervisor)입니다.
현재 발생한 에러를 분석하여 '누구의 영역'인지 정확히 판단하고 정석적인 소프트웨어 공학 절차에 따라 지시하세요.

{AGENT_CAPABILITIES}

[현재 디스크 상의 실제 파일 목록]
{actual_files_str}

[판단 및 지시 가이드 - MSA 대응 버전]
1. [백엔드 구조 결함] 파이썬 패키지 구조상 필수적인 모듈(.py)이 실제 파일 목록에 아예 없거나, DB 스키마 설계에 근본적인 문제가 있는 경우?
   -> TARGET: backend_architect
   -> DIRECTIVE: 백엔드 설계도(backend_architecture.md)에 누락된 파이썬 파일을 추가하고 모듈 구조를 재설계하라.

2. [백엔드 구현/환경 결함] FastAPI/Flask 등의 라이브러 부재(ModuleNotFoundError), 버전 충돌, 또는 파이썬 코드(.py) 내부의 로직 에러나 런타임 에러인 경우?
   -> TARGET: backend_developer
   -> DIRECTIVE: 'backend/requirements.txt'에 패키지 버전을 고정(Pinning)하여 추가하거나, 에러 로그를 바탕으로 해당 파이썬 코드를 수정하라. (주의: 설치 경로는 반드시 backend/ 하위임을 명시할 것)

3. [프론트엔드 구조 결함] React 컴포넌트 설계 누락, 라우팅(페이지 이동) 구조의 근본적인 문제, 혹은 필수 화면 파일(.jsx)이 아예 없는 경우?
   -> TARGET: frontend_architect
   -> DIRECTIVE: 프론트엔드 설계도(frontend_architecture.md)에 누락된 컴포넌트를 정의하고 화면 흐름을 재설계하라.

4. [프론트엔드 구현/환경 결함] npm 패키지 누락, React 문법 에러, 백엔드 API와의 통신 실패(CORS 제외, fetch/axios 로직 오류), 또는 UI 렌더링 에러인 경우?
   -> TARGET: frontend_developer
   -> DIRECTIVE: 'frontend/package.json'에 필요한 의존성을 추가하거나, 문제가 발생한 React 컴포넌트 코드를 수정하라.

5. [파일 위치 오류 및 Import Mismatch] 파일은 `actual_files_str`에 존재하지만, 코드에서 경로를 찾지 못해 에러가 나는 경우?
   -> 진단: 모듈 임포트 경로 오류 (Path Mismatch)
   -> TARGET: [문제가 발생한 진영의 developer (예: backend_developer)]
   -> DIRECTIVE: "실제 파일은 [경로]에 존재하지만 임포트 문이 잘못되었습니다. 상대 경로 또는 절대 경로를 기준 폴더(backend/ 또는 frontend/)에 맞게 수정하세요."

[응답 포맷]
TARGET: [반드시 다음 5개 중 하나만 선택: backend_architect, backend_developer, frontend_architect, frontend_developer, human_approval]
DIRECTIVE: [구체적인 지시 내용]""")

    user_prompt = HumanMessage(content=f"최종 QA 에러 리포트:\n{qa_feedback}")
    
    response = llm.invoke([system_prompt, user_prompt])
    result_text = response.content.strip()
    
    target = "backend_developer"
    directive = "이전 에러를 확인하고 코드를 수정하세요."
    
    for line in result_text.split('\n'):
        if line.startswith("TARGET:"):
            target = line.replace("TARGET:", "").strip()
        elif line.startswith("DIRECTIVE:"):
            directive = line.replace("DIRECTIVE:", "").strip()
            
    print(f"   -> 🎯 타겟: {target}")
    print(f"   -> 📝 지시: {directive}")
    
    return {"supervisor_decision": target, "supervisor_directive": directive}
