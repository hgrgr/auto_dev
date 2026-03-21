import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from state import AgentState
from tools import write_code_to_workspace
from config import DEFAULT_MODEL, TEMPERATURE, WORKSPACE_DIR

llm = ChatOpenAI(model=DEFAULT_MODEL, temperature=TEMPERATURE)
llm_with_tools = llm.bind_tools([write_code_to_workspace])

def documentation_agent(state: AgentState):
    project_name = state.get("project_name", "unknown_project")
    print("\n🤖 [Tech Writer Agent]: QA를 통과한 전체 코드를 바탕으로 극도로 상세한 공식 문서를 작성합니다...")
    
    # PM이 작성한 기획서와 API 명세서를 가져옵니다 (문서 작성의 뼈대가 됨)
    requirements = state.get("requirements", "")
    api_contract = state.get("api_contract", "")
    
    project_dir = os.path.join(WORKSPACE_DIR, project_name)
    
    # [핵심 수정 1] 백엔드(.py)와 프론트엔드(.js, .jsx, .json 등) 파일을 모두 읽어옵니다.
    code_files = {}
    if os.path.exists(project_dir):
        for root, _, files in os.walk(project_dir):
            if "venv" in root or "__pycache__" in root or "node_modules" in root or "dist" in root or ".git" in root:
                continue
            for file in files:
                # 문서화에 필요한 프론트/백엔드 주요 확장자 모두 포함
                if file.endswith((".py", ".js", ".jsx", ".json", ".html")):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, project_dir)
                    with open(file_path, "r", encoding="utf-8") as f:
                        code_files[rel_path] = f.read()
                        
    code_content = "\n\n".join([f"--- {filename} ---\n{code}" for filename, code in code_files.items()])
    
    system_prompt = SystemMessage(content=f"""당신은 시니어 테크니컬 라이터입니다. 
PM의 기획서(PRD)와 API 명세서, 그리고 최종 완성된 코드를 분석하여 프로젝트 전체를 아우르는 공식 문서를 작성하세요.

[🚨 도구 호출 절대 규칙]
1. 도구(write_code_to_workspace) 호출 시 'project_name' 파라미터는 "{project_name}"으로 고정하세요.
2. 'module_type' 파라미터는 무조건 "docs"로 지정하세요.
3. 반드시 아래 2개의 파일을 각각 도구를 호출하여 생성해야 합니다!

[작성해야 할 파일 목록]
1. 파일명: 'README.md'
   - 목적: 이 프로젝트를 처음 보는 사람이 전체 구조를 이해하고 실행할 수 있도록 돕는 완벽한 통합 가이드.
   - [필수 포함 내용]:
     * 프로젝트 개요 및 주요 기능 (PM의 PRD 참조)
     * 기술 스택 (백엔드 및 프론트엔드 분리하여 설명)
     * 🐍 백엔드 실행 방법 (가상환경 설정, requirements.txt 패키지 설치, 실행 명령어, 서버 접속 URL 및 포트)
     * ⚛️ 프론트엔드 실행 방법 (npm install, npm run dev 등 실행 명령어, 클라이언트 접속 URL 및 포트)
     * 연동 시 주의사항 (CORS 등)
     
2. 파일명: 'specification.md'
   - 목적: 향후 유지보수를 위한 '단일 진실 공급원(SSOT)'.
   - [필수 포함 내용]:
     * 프로젝트 전체 디렉토리 구조도
     * 백엔드 API 명세 (API Contract 참조 - Endpoint, Request/Response 구조)
     * 주요 프론트엔드 컴포넌트 구조 및 역할 설명
""")

    user_prompt = HumanMessage(content=f"""
[PM 기획서 (PRD)]
{requirements}

[API 명세서 (Contract)]
{api_contract}

[전체 프로젝트 코드]
{code_content}

위 정보를 바탕으로 완벽한 README.md와 specification.md를 작성하고 도구를 사용해 저장해주세요.
""")

    response = llm_with_tools.invoke([system_prompt, user_prompt])
    
    # 도구 호출 실행 (파일 저장)
    if response.tool_calls:
        for tool_call in response.tool_calls:
            if tool_call["name"] == "write_code_to_workspace":
                result = write_code_to_workspace.invoke(tool_call["args"])
                print(f"   -> 📝 {result}")

    return {}
