import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from state import AgentState
from tools import write_code_to_workspace, read_file_from_workspace
from config import DEFAULT_MODEL, TEMPERATURE, WORKSPACE_DIR

llm = ChatOpenAI(model=DEFAULT_MODEL, temperature=TEMPERATURE)
llm_with_tools = llm.bind_tools([write_code_to_workspace, read_file_from_workspace])

def developer_agent(state: AgentState):
    project_name = state.get("project_name", "default_project")
    print(f"\n🤖 [Dev Agent]: '{project_name}' 프로젝트의 코드를 작성 중입니다...")
    
    requirements = state.get("requirements", "요구사항이 없습니다.")
    architecture = state.get("architecture", "아키텍처 설계가 없습니다.")
    
    project_dir = os.path.join(WORKSPACE_DIR, project_name)
    existing_files = []
    
    # [핵심 추가 1] requirements.txt 내용 읽기
    req_content = "아직 requirements.txt가 생성되지 않았습니다."
    req_path = os.path.join(project_dir, "requirements.txt")
    if os.path.exists(req_path):
        with open(req_path, "r", encoding="utf-8") as f:
            req_content = f.read()

    # [핵심 추가 2] Dev 에이전트가 코드를 고칠 수 있도록 현재 작성된 전체 .py 코드 내용을 읽어옵니다.
    existing_code_content = ""
    if os.path.exists(project_dir):
        for root, _, files in os.walk(project_dir):
            if "venv" in root or "__pycache__" in root: 
                continue
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, project_dir)
                existing_files.append(rel_path)
                
                # 파이썬 파일인 경우 코드를 통째로 변수에 저장
                if file.endswith(".py"):
                    with open(file_path, "r", encoding="utf-8") as f:
                        existing_code_content += f"\n--- {rel_path} ---\n{f.read()}\n"
                
    existing_files_str = "\n".join(existing_files) if existing_files else "생성된 파일 없음"

    error_feedback = ""
    if state.get("test_results", "").startswith("FAIL"):
        error_feedback = f"\n[QA 에러 피드백]\n{state['messages'][-1].content}"
        
    # [추가됨] Supervisor의 특별 지시사항 주입
    supervisor_directive = state.get("supervisor_directive", "")
    if supervisor_directive:
        error_feedback += f"\n\n🚨 [SUPERVISOR 긴급 지시사항 (가장 최우선으로 따를 것)]\n{supervisor_directive}"


    # 프롬프트에 순환 참조(Circular Import) 해결 지침 강력 추가
    system_prompt = SystemMessage(content=f"""당신은 수석 소프트웨어 엔지니어입니다. 
주어진 요구사항과 '아키텍트의 설계도'를 완벽하게 준수하여 실제 구동 가능한 파이썬 코드를 작성하세요. 
도구를 호출할 때 'project_name' 파라미터 값으로 반드시 '{project_name}'을 입력해야 합니다.

[절대 규칙 - 반드시 지키세요] 
1. 'docs/architecture.md' 등 문서 파일은 절대 작성하거나 덮어쓰지 마세요.
2. [버그 수정 및 순환 참조 해결] 에러의 원인이 되는 파일들을 찾아내어, 임포트 위치를 옮기거나 의존성을 재설계하여 도구를 통해 덮어쓰세요.
3. 🚨 [환경 파일 누락 에러 우회 (핵심!!)] QA 피드백에서 'ssl/server.crt', '.env 파일', '데이터베이스 파일' 등이 없어서 실행이 안 된다고 하면, 사용자에게 파일을 만들라고 텍스트로 설명하지 마세요! 당신은 터미널 명령어를 칠 수 없습니다. 대신 메인 코드(예: main.py, config.py)를 수정하여 로컬 샌드박스 테스트 중에는 SSL(HTTPS) 적용을 임시로 해제(Bypass)하거나, 파이썬 코드 내에서 더미 파일/DB를 자동 생성하도록 로직을 변경한 뒤 도구로 저장하세요.
4. [도구 강제 호출] 어떤 오류 피드백을 받든, 말로만 설명하거나 텍스트만 반환하는 것은 '절대 금지'입니다. 무조건 하나 이상의 파이썬 코드를 수정하여 'write_code_to_workspace' 도구를 호출해야만 당신의 임무가 끝납니다.""")

    
    # Dev 에이전트에게 전체 파일 리스트, 패키지 버전, 그리고 '전체 코드 내용'을 몽땅 주입합니다.
    user_prompt = HumanMessage(content=f"요구사항:\n{requirements}\n\n아키텍처 설계도:\n{architecture}\n\n현재 디스크에 저장된 파일 목록:\n{existing_files_str}\n\n현재 requirements.txt 내용:\n{req_content}\n\n현재 작성된 전체 파이썬 코드:\n{existing_code_content}\n{error_feedback}")
    
    response = llm_with_tools.invoke([system_prompt, user_prompt])
    
    code_files_updated = {}
    if response.tool_calls:
        for tool_call in response.tool_calls:
            if tool_call["name"] == "write_code_to_workspace":
                result = write_code_to_workspace.invoke(tool_call["args"])
                print(f"   -> 💾 {result}")
                code_files_updated[tool_call["args"]["filename"]] = tool_call["args"]["code"]
    else:
        # LLM이 도구를 호출하지 않고 일반 텍스트만 뱉으며 턴을 넘기는 직무유기 현상 모니터링
        print("   -> ⚠️ [System Warning]: Dev Agent가 도구를 호출하지 않고 텍스트만 반환했습니다! (수동 개입 필요 혹은 코드 꼬임)")
        
    return {"code_files": code_files_updated}
