# agents/pm.py
import re
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from state import AgentState
from config import DEFAULT_MODEL, TEMPERATURE

llm = ChatOpenAI(model=DEFAULT_MODEL, temperature=TEMPERATURE)

def pm_agent(state: AgentState):
    project_name = state.get("project_name", "unknown_project")
    existing_requirements = state.get("requirements", "")
    
    # 처음 실행인지, 추가 스프린트인지 확인
    is_update = bool(existing_requirements)
    
    if is_update:
        print(f"\n🤖 [PM Agent]: '{project_name}'의 기존 시스템에 사용자 피드백을 반영하여 명세서와 API 통신 규약을 업데이트합니다...")
        context_prompt = f"[기존 명세서]\n{existing_requirements}\n\n[사용자의 새로운 추가/수정 요구사항]\n{state['messages'][-1].content}"
    else:
        print(f"\n🤖 [PM Agent]: '{project_name}'의 요구사항을 분석하여 기획서(PRD)와 API Contract를 작성합니다...")
        first_msg = state["messages"][0]
        user_message = first_msg.content if hasattr(first_msg, 'content') else first_msg[1]
        context_prompt = f"최초 사용자 요구사항: {user_message}"

    system_prompt = SystemMessage(content=f"""당신은 뛰어난 역량을 가진 IT 프로덕트 매니저(PM)입니다.
우리의 개발 조직은 '백엔드 전담 파트(Python)'와 '프론트엔드 전담 파트'로 완전히 분리되어 독립적으로 작업합니다.
따라서 당신은 두 파트가 서로 묻지 않고도 즉각 개발에 착수할 수 있도록 완벽한 '기획서(PRD)'와 'API 명세서(Contract)'를 작성해야 합니다.

[작성 규칙]
1. 응답은 반드시 두 부분으로 나누어 작성해야 합니다.
2. 첫 번째 부분은 전체 프로젝트 개요와 화면/기능 요구사항을 담은 기획서입니다. 반드시 <PRD> 와 </PRD> 태그로 내용을 감싸주세요.
3. 두 번째 부분은 프론트/백엔드 통신 규약입니다. 반드시 <API_CONTRACT> 와 </API_CONTRACT> 태그로 감싸주세요.
4. 🚨 [핵심] API Contract에는 다음 통신 환경 규약이 **반드시** 명시되어야 합니다:
   - 백엔드 로컬 서버 주소 및 포트 (예: http://localhost:8000)
   - 프론트엔드 로컬 서버 주소 및 포트 (예: Vite의 경우 http://localhost:5173, CRA의 경우 http://localhost:3000)
   - CORS 허용 정책 (백엔드 서버는 반드시 프론트엔드의 접근을 허용해야 함)
   - 각 엔드포인트의 목적, URL, HTTP Method, Request/Response 데이터 형식 예시
5. (추가/수정의 경우) 기존 기능의 무결성을 유지하며 증분(Incremental) 업데이트를 수행하세요.
""")

    user_prompt = HumanMessage(content=context_prompt)
    
    response = llm.invoke([system_prompt, user_prompt])
    full_content = response.content
    
    # 정규표현식을 사용하여 PRD와 API Contract 파트를 추출
    prd_match = re.search(r"<PRD>(.*?)</PRD>", full_content, re.DOTALL)
    api_match = re.search(r"<API_CONTRACT>(.*?)</API_CONTRACT>", full_content, re.DOTALL)
    
    # 추출 실패 시 Fallback (전체 내용을 requirements로)
    prd_text = prd_match.group(1).strip() if prd_match else full_content
    api_text = api_match.group(1).strip() if api_match else "API 명세가 명확히 분리되지 않았습니다. 개발자는 PRD를 참조하여 API를 자율 설계하세요."
    
    print("   -> 📝 기획서(PRD) 및 API 명세서(Contract) 작성 완료.")
    
    return {
        "requirements": prd_text,
        "api_contract": api_text, 
        "human_decision": "processed"
    }
