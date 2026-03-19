import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from state import AgentState
from tools import write_code_to_workspace
from config import DEFAULT_MODEL, TEMPERATURE, WORKSPACE_DIR

llm = ChatOpenAI(model=DEFAULT_MODEL, temperature=TEMPERATURE)
llm_with_tools = llm.bind_tools([write_code_to_workspace])

def architect_agent(state: AgentState):
    project_name = state.get("project_name", "unknown_project")
    print(f"\n🏗️ [Architect Agent]: '{project_name}'의 시스템 아키텍처를 업데이트합니다...")
    
    requirements = state.get("requirements", "요구사항이 없습니다.")
    existing_architecture = state.get("architecture", "")
    supervisor_directive = state.get("supervisor_directive", "")
    
    # [핵심 보완] 현재 실제 디스크에 어떤 파일들이 있는지 아키텍트에게 알려줍니다.
    project_dir = os.path.join(WORKSPACE_DIR, project_name)
    actual_files = []
    if os.path.exists(project_dir):
        for root, _, files in os.walk(project_dir):
            if "venv" in root or "__pycache__" in root: continue
            for f in files:
                actual_files.append(os.path.relpath(os.path.join(root, f), project_dir))
    
    actual_files_str = "\n".join(actual_files) if actual_files else "생성된 파일 없음"

    # [절대 규칙 통합 프롬프트]
    system_prompt = SystemMessage(content=f"""당신은 경험이 풍부한 수석 소프트웨어 아키텍트입니다.
다음의 '절대 규칙'을 위반할 경우 시스템 전체에 심각한 오류가 발생하므로, 반드시 준수하여 설계도(architecture.md)를 작성하세요.

[🚨 경로 작성 절대 규칙 - 위반 시 도구 작동 불가]
1. 'filename' 파라미터에는 프로젝트 루트 기준의 '순수 상대 경로'만 입력합니다.
2. 경로의 시작에 어떠한 접두사(Prefix)도 붙이지 마세요.
   - ✅ 올바른 예: "docs/architecture.md", "models/user.py", "main.py"
   - ❌ 잘못된 예: "project-root/docs/architecture.md", "./docs/architecture.md", "/shopping/main.py"
3. 당신이 관리하는 모든 파일 트리의 경로는 위 규칙을 따라야 합니다.

[설계 원칙]
1. 환경 제약: 오직 Python 3.13 생태계만을 사용합니다. (Node.js, JS 절대 금지)
2. 파일 형식: 모든 디렉토리 구조와 파일명은 반드시 파이썬 확장자(.py)를 가져야 합니다.
3. 증분 설계(Incremental Update): 기존 시스템의 무결성을 유지하면서 새로운 기능만 '추가'하거나 최소한으로 '변경'하세요. 기존 구조를 완전히 갈아엎는 것은 금지됩니다.

[Supervisor 특수 지시 반영]
- Supervisor가 지적한 결함(누락, 임포트 오류 등)은 최우선적으로 수정하여 'architecture.md'에 반영해야 합니다.

작성된 설계도는 반드시 도구를 사용하여 'docs/architecture.md' 파일로 저장해야 합니다.""")

    user_prompt = HumanMessage(content=f"""
[현재 요구사항]
{requirements}

[기존 설계도]
{existing_architecture}

[현재 실제 디스크 파일 목록]
{actual_files_str}

🚨 [SUPERVISOR 긴급 지시사항]
{supervisor_directive}

위 정보를 바탕으로 설계도를 업데이트하세요. 실제 파일 목록과 설계도 사이의 간극을 메우고, 요구사항을 반영한 '완전한 파일 트리'를 포함해야 합니다.

⚠️ [최종 확인 지시]
도구(write_code_to_workspace)를 호출하기 전, 저장할 파일 경로(filename)를 다시 확인하세요. 
'project-root/'와 같은 접두사가 포함되어 있다면 즉시 제거하고 'docs/architecture.md'와 같이 작성하세요.
""")

    response = llm_with_tools.invoke([system_prompt, user_prompt])
    
    if response.tool_calls:
        for tool_call in response.tool_calls:
            if tool_call["name"] == "write_code_to_workspace":
                result = write_code_to_workspace.invoke(tool_call["args"])
                print(f"   -> 📐 {result}")
                
    return {"architecture": response.content, "qa_attempts": 0}
