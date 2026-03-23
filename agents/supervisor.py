import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_community.tools import DuckDuckGoSearchRun
from state import AgentState
from config import DEFAULT_MODEL, TEMPERATURE

llm = ChatOpenAI(model=DEFAULT_MODEL, temperature=TEMPERATURE)
search_tool = DuckDuckGoSearchRun()

def supervisor_agent(state: AgentState):
    print("\n🧐 [Supervisor Agent]: 교착 상태를 분석합니다...")
    
    test_results = state.get("test_results", "")
    requirements = state.get("requirements", "")
    
    # ---------------------------------------------------------
    # Step 1. 에러 로그를 보고 검색이 필요한지 스스로 판단 & 검색
    # ---------------------------------------------------------
    print("   -> 🔍 에러 원인 파악을 위해 최신 해결책을 검색할지 판단 중...")
    
    search_decision_prompt = SystemMessage(content="""당신은 시니어 개발팀장입니다.
아래 에러 로그를 보고, 이 에러가 프레임워크(React, Vite, FastAPI, Playwright 등)의 버전이나 설정 문제라서 최신 문법 검색이 필요한지 판단하세요.
검색이 필요하다면 영어로 검색 쿼리를 하나만 출력하고, 일반적인 오타나 로직 에러라서 검색이 필요 없다면 'NO_SEARCH'라고만 출력하세요.

예시 1: "Vite react index.html entry module not found"
예시 2: "Playwright get_by_text unexpected keyword argument timeout"
예시 3: NO_SEARCH""")

    search_decision_user = HumanMessage(content=f"[에러 로그]\n{test_results}")
    search_query_response = llm.invoke([search_decision_prompt, search_decision_user])
    search_query = search_query_response.content.strip()

    search_context = ""
    if search_query != "NO_SEARCH":
        print(f"   -> 🌐 인터넷 검색 중: '{search_query}'")
        try:
            search_result = search_tool.invoke(search_query)
            search_context = f"\n\n[웹 검색 결과 (참고용 최신 팩트)]\n{search_result}\n위 검색 결과를 바탕으로 에러의 '진짜 원인'을 파악하여 지시하세요."
            print("   -> 💡 최신 해결책을 찾아냈습니다! 이를 바탕으로 지시를 작성합니다.")
        except Exception as e:
            print(f"   -> ⚠️ 검색 실패 (무시하고 기존 지식으로 진행): {e}")
    else:
        print("   -> 🧠 검색 없이 코드 로직 문제로 판단하여 바로 분석합니다.")

    # ---------------------------------------------------------
    # Step 2. 검색 결과를 포함하여 팩트 기반의 지시사항 작성
    # ---------------------------------------------------------
    system_prompt = SystemMessage(content=f"""당신은 문제를 해결하는 시니어 개발 팀장(Supervisor)입니다.
현재 QA 테스트 또는 빌드 단계에서 교착 상태(반복되는 에러)가 발생했습니다.
{search_context}

아래 에러 내용을 분석하여 누구에게 책임을 묻고 어떤 지시를 내려야 할지 결정하세요.
🚨 [절대 규칙]
1. 프론트엔드 환경은 Vite 기반입니다. (index.html은 루트에 있어야 하며, CRA 방식의 훈수를 두지 마세요.)
2. Playwright 문법 등 프레임워크 에러라면 뇌피셜로 답하지 말고 반드시 검색 결과를 우선적으로 따르세요!
3. 지시사항은 상대방이 도구(write_code_to_workspace)를 어떻게 사용해서 고쳐야 할지 아주 구체적이고 단호하게 작성하세요.

반드시 아래 형식에 맞춰 답변하세요:
TARGET: [backend_architect, backend_developer, frontend_architect, frontend_developer 중 택 1]
INSTRUCTION: [구체적인 지시 내용]""")

    user_prompt = HumanMessage(content=f"[현재 에러 상황]\n{test_results}")
    
    response = llm.invoke([system_prompt, user_prompt])
    result_text = response.content.strip()
    
    # 파싱
    target = "backend_developer"
    instruction = result_text
    
    for line in result_text.split('\n'):
        if line.startswith("TARGET:"):
            target = line.replace("TARGET:", "").strip()
        elif line.startswith("INSTRUCTION:"):
            instruction = line.replace("INSTRUCTION:", "").strip()
            
    print(f"   -> 🎯 타겟: {target}")
    print(f"   -> 📝 지시(팩트 기반): {instruction[:100]}...")
    
    return {"supervisor_decision": target, "supervisor_instruction": instruction}
