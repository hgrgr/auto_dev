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
다음의 '절대 규칙'을 반드시 준수하며 시스템 설계도(architecture.md)를 작성하거나 업데이트하세요.

[절대 규칙 - 엄수]
1. 환경 제약: 오직 Python 3.13 생태계만을 사용합니다. (Node.js, JS 절대 금지)
2. 파일 형식: 모든 디렉토리 구조와 파일명은 반드시 파이썬 확장자(.py)를 가져야 합니다.
3. 증분 설계(Incremental Update): 이미 개발된 기능이 있다면 절대 기존 구조를 완전히 갈아엎지 마세요. 기존 시스템의 무결성을 유지하면서 새로운 파일이나 함수만 '추가'하거나 최소한으로 '변경'하세요.

[Supervisor 특수 지시 반영]
- 만약 Supervisor가 특정 파일의 누락이나 임포트 경로 오류를 지적했다면, 이를 당신의 설계 결함으로 인정하고 'architecture.md'의 파일 트리와 모듈 연결 관계를 즉시 수정하세요.

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

위 정보를 바탕으로, 실제 파일 목록과 설계도 사이의 간극을 메우고 새로운 요구사항을 반영한 '완전한 파일 트리'를 포함하여 설계도를 업데이트하세요.
""")

    response = llm_with_tools.invoke([system_prompt, user_prompt])
    
    if response.tool_calls:
        for tool_call in response.tool_calls:
            if tool_call["name"] == "write_code_to_workspace":
                result = write_code_to_workspace.invoke(tool_call["args"])
                print(f"   -> 📐 {result}")
                
    return {"architecture": response.content, "qa_attempts": 0}
