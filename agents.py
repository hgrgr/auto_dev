# agents.py
import os
import sys
import subprocess
import datetime
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from state import AgentState
from tools import write_code_to_workspace, read_file_from_workspace

# 환경변수 로드 및 LLM 세팅
load_dotenv()
llm = ChatOpenAI(model="gpt-4o", temperature=0)
llm_with_tools = llm.bind_tools([write_code_to_workspace, read_file_from_workspace])

MAX_QA_ATTEMPTS = 3

def pm_agent(state: AgentState):
    project_name = state.get("project_name", "unknown_project")
    print(f"\n🤖 [PM Agent]: '{project_name}'의 사용자 요구사항을 분석하여 명세서를 작성합니다...")
    
    if state.get("messages"):
        first_msg = state["messages"][0]
        user_message = first_msg.content if hasattr(first_msg, 'content') else first_msg[1]
    else:
        user_message = "요구사항 없음"
        
    system_prompt = SystemMessage(content="""당신은 뛰어난 역량을 가진 IT 프로덕트 매니저(PM)이자 시스템 아키텍트입니다.
사용자의 모호한 요구사항을 분석하여 개발자가 즉시 코딩을 시작할 수 있는 수준의 '기술 명세서(PRD)'를 작성해야 합니다.
프로젝트 개요, 기능 목록, API 엔드포인트 스펙, 보안 요구사항 등을 마크다운 형식으로 정리하세요.""")
    user_prompt = HumanMessage(content=f"최초 사용자 요구사항: {user_message}")
    
    response = llm.invoke([system_prompt, user_prompt])
    print("   -> 📝 명세서 작성 완료.")
    return {"requirements": response.content}
# 개발 에이전트
def developer_agent(state: AgentState):
    project_name = state.get("project_name", "default_project")
    print(f"\n🤖 [Dev Agent]: '{project_name}' 프로젝트의 코드를 작성 중입니다...")
    
    requirements = state.get("requirements", "요구사항이 없습니다.")
    error_feedback = ""
    if state.get("test_results", "").startswith("FAIL"):
        error_feedback = f"\n이전 코드 검사에서 다음 오류/취약점이 발견되었습니다. 이를 수정하여 다시 작성하세요:\n{state['messages'][-1].content}"

    system_prompt = SystemMessage(content=f"""당신은 수석 소프트웨어 엔지니어입니다. 
주어진 요구사항에 맞는 코드를 작성하고 도구를 사용해 저장하세요. 
도구를 호출할 때 'project_name' 파라미터 값으로 반드시 '{project_name}'을 입력해야 합니다.

[중요 지침] 
1. 도구를 여러 번 호출하여 **반드시 메인 파이썬 코드(.py)와 requirements.txt를 모두** 생성하고 저장해야 합니다. 파이썬 코드 없이 requirements.txt만 저장하면 절대 안 됩니다.
2. 현재 시스템은 Python 3.13 환경입니다. requirements.txt 작성 시 반드시 최신 안정화 버전(예: Flask>=3.0, FastAPI 최신 등)을 사용하세요.
3. 실행 중 'ImportError'나 버전 충돌 에러가 발생하면, requirements.txt와 파이썬 코드를 모두 최신 버전에 맞게 수정하여 도구로 다시 덮어쓰세요.
4. 추가 수정 요청이 들어온 경우, 'read_file_from_workspace' 도구를 사용해 반드시 'docs/specification.md'를 먼저 읽고 기존 시스템 규칙을 위반하지 않도록 코드를 작성하세요.""")

    user_prompt = HumanMessage(content=f"요구사항: {requirements} {error_feedback}")
    
    response = llm_with_tools.invoke([system_prompt, user_prompt])
    
    code_files_updated = {}
    if response.tool_calls:
        for tool_call in response.tool_calls:
            if tool_call["name"] == "write_code_to_workspace":
                result = write_code_to_workspace.invoke(tool_call["args"])
                print(f"   -> 💾 {result}")
                code_files_updated[tool_call["args"]["filename"]] = tool_call["args"]["code"]
    
    return {"code_files": code_files_updated}
#qa 에이전트
def security_qa_agent(state: AgentState):
    print("\n🤖 [Security/QA Agent]: 코드 정적 분석 및 샌드박스 동적 테스트를 시작합니다...")
    project_name = state.get("project_name", "unknown_project")
    code_files = state.get("code_files", {})
    current_attempts = state.get("qa_attempts", 0) + 1
    
    if not code_files:
        return {"test_results": "FAIL: 검사할 코드가 없습니다.", "messages": [HumanMessage(content="코드가 생성되지 않았습니다.")], "qa_attempts": current_attempts}

    # [새로 추가된 방어 로직] .py 파일이 하나라도 있는지 확인
    has_py_files = any(filename.endswith(".py") for filename in code_files.keys())
    if not has_py_files:
        print("   -> 🚨 [QA 발견 문제]: 실행할 파이썬(.py) 파일이 하나도 없습니다!")
        return {
            "test_results": "FAIL", 
            "messages": [HumanMessage(content="파이썬 코드(.py)가 작성되지 않았습니다. 반드시 메인 애플리케이션 코드를 작성하고 도구를 사용해 저장하세요.")], 
            "qa_attempts": current_attempts
        } 




    code_content = "\n\n".join([f"--- {filename} ---\n{code}" for filename, code in code_files.items()])
    
    execution_logs = ""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.join(base_dir, "workspace", project_name)
    venv_dir = os.path.join(project_dir, "venv")
    
    if os.name == 'nt':
        venv_python = os.path.join(venv_dir, "Scripts", "python.exe")
        venv_pip = os.path.join(venv_dir, "Scripts", "pip.exe")
        venv_bin = os.path.join(venv_dir, "Scripts")
    else:
        venv_python = os.path.join(venv_dir, "bin", "python")
        venv_pip = os.path.join(venv_dir, "bin", "pip")
        venv_bin = os.path.join(venv_dir, "bin")

    if not os.path.exists(venv_dir):
        print(f"   -> 🛠️ 프로젝트 전용 가상환경(venv)을 '{venv_dir}'에 생성합니다...")
        subprocess.run([sys.executable, "-m", "venv", venv_dir], check=True)

    # 환경 변수 누수 차단
    isolated_env = os.environ.copy()
    isolated_env.pop("VIRTUAL_ENV", None)
    isolated_env.pop("PYTHONPATH", None)
    isolated_env["PATH"] = venv_bin + os.pathsep + isolated_env.get("PATH", "")

    # security_qa_agent 함수 내부의 pip install 실행 부분 수정
    req_path = os.path.join(project_dir, "requirements.txt")
    if os.path.exists(req_path):
        print("   -> 📦 완벽히 격리된 환경에 의존성 패키지 설치 중...")
        try:
            # [수정됨] "install" 뒤에 "--upgrade" 추가
            subprocess.run([venv_pip, "install", "--upgrade", "-r", "requirements.txt"], cwd=project_dir, env=isolated_env, capture_output=True, text=True, check=True)
            print("   -> ✅ 패키지 설치 완료.")
        except subprocess.CalledProcessError as e:
            print(f"   -> 🚨 패키지 설치 실패:\n{e.stderr}")
            execution_logs += f"\n[환경 셋업 에러] pip install 실패:\n{e.stderr}\n"
    
    for filename in code_files.keys():
        if filename.endswith(".py") and filename != "setup.py":
            filepath = os.path.join(project_dir, filename)
            print(f"   -> 🏃‍♂️ 샌드박스(격리 venv)에서 '{filename}' 실행 중...")
            try:
                result = subprocess.run([venv_python, filepath], cwd=project_dir, env=isolated_env, capture_output=True, text=True, timeout=3)
                execution_logs += f"\n--- {filename} 실행 결과 ---\n[STDOUT]\n{result.stdout}\n[STDERR]\n{result.stderr}\n"
            except subprocess.TimeoutExpired:
                execution_logs += f"\n--- {filename} 실행 결과 ---\n[INFO] 코드가 3초간 정상적으로 실행/대기 상태를 유지했습니다. (Timeout)\n"
            except Exception as e:
                execution_logs += f"\n--- {filename} 실행 결과 ---\n[시스템 에러] 실행 실패: {str(e)}\n"

    #2. security_qa_agent 내부의 system_prompt 수정 (함수 밑부분)
    system_prompt = SystemMessage(content="""당신은 엄격한 보안 감사자(Security Auditor)이자 QA 엔지니어입니다. 
주어진 코드와 '동적 실행 로그(Runtime Logs)'를 모두 분석하세요.
[주의사항] 현재 환경은 **Python 3.13**입니다. 패키지 버전 충돌(ImportError)을 발견하더라도, 절대로 옛날 버전(예: Flask 1.1.2 등)으로 다운그레이드하라고 조언하지 마세요. 반드시 최신 버전으로 업그레이드하여 호환성을 맞추도록 피드백하세요.
결함이 발견되면 'FAIL: [핵심 이유 한 줄 요약]'으로 시작하여 구체적인 취약점과 수정 방안을 제시하세요.
결함이 전혀 없고 배포 준비가 완료되었다면 'PASS'라고만 답변하세요.""") 

    user_prompt = HumanMessage(content=f"코드 내용:\n{code_content}\n\n동적 실행 로그:\n{execution_logs}")
    
    response = llm.invoke([system_prompt, user_prompt])
    review_result = response.content.strip()
    
    if review_result.startswith("FAIL"):
        fail_summary = review_result.split('\n')[0]
        print(f"   -> 🚨 [QA 발견 문제]: {fail_summary}")
        print(f"   -> 🔄 (현재 재시도: {current_attempts}회)")
        
        if current_attempts >= MAX_QA_ATTEMPTS:
            error_dir = os.path.join(project_dir, "unresolved_errors")
            os.makedirs(error_dir, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            error_file = os.path.join(error_dir, f"error_report_{timestamp}.md")
            with open(error_file, "w", encoding="utf-8") as f:
                f.write(f"# 🚨 미해결 에러 리포트\n\n## 📌 요약\n{fail_summary}\n\n## 🤖 QA 상세 분석\n{review_result}\n\n## 💻 실행 로그\n```text\n{execution_logs}\n```\n")
            print(f"   -> 📁 [System]: 미해결 에러 리포트가 '{error_file}'에 저장되었습니다.")

        return {"test_results": "FAIL", "messages": [HumanMessage(content=review_result)], "qa_attempts": current_attempts}
    else:
        print("   -> ✅ [QA 통과]: 실행 에러 및 보안 결함이 없습니다.")
        return {"test_results": "PASS", "qa_attempts": current_attempts}

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
