from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from state import AgentState
from tools import write_code_to_workspace, read_file_from_workspace
from config import DEFAULT_MODEL, TEMPERATURE

llm = ChatOpenAI(model=DEFAULT_MODEL, temperature=TEMPERATURE)
llm_with_tools = llm.bind_tools([write_code_to_workspace, read_file_from_workspace])

def documentation_agent(state: AgentState):
    project_name = state.get("project_name", "unknown_project")
    print("\n🤖 [Tech Writer Agent]: QA를 통과한 코드를 바탕으로 공식 문서를 작성합니다...")
    code_files = state.get("code_files", {})
    code_content = "\n\n".join([f"--- {filename} ---\n{code}" for filename, code in code_files.items()])
    
    system_prompt = SystemMessage(content=f"""당신은 시니어 테크니컬 라이터입니다. 
주어진 최종 코드를 분석하여 README.md와 docs/specification.md 문서를 작성하고 도구를 사용하여 저장하세요.
도구 호출 시 'project_name'은 '{project_name}'을 사용하세요.""")
    user_prompt = HumanMessage(content=f"최종 완성된 코드:\n{code_content}")
    
    response = llm_with_tools.invoke([system_prompt, user_prompt])
    if response.tool_calls:
        for tool_call in response.tool_calls:
            if tool_call["name"] == "write_code_to_workspace":
                result = write_code_to_workspace.invoke(tool_call["args"])
                print(f"   -> 📝 {result}")
    return state
