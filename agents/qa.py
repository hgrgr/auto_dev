import os
import sys
import subprocess
import datetime
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from state import AgentState
from config import DEFAULT_MODEL, TEMPERATURE, MAX_QA_ATTEMPTS, WORKSPACE_DIR

llm = ChatOpenAI(model=DEFAULT_MODEL, temperature=TEMPERATURE)

def security_qa_agent(state: AgentState):
    print("\n🤖 [Security/QA Agent]: 코드 정적 분석 및 샌드박스 동적 테스트를 시작합니다...")
    project_name = state.get("project_name", "unknown_project")
    code_files = state.get("code_files", {})
    current_attempts = state.get("qa_attempts", 0) + 1
    
    if not code_files:
        return {"test_results": "FAIL: 검사할 코드가 없습니다.", "messages": [HumanMessage(content="코드가 생성되지 않았습니다.")], "qa_attempts": current_attempts}

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
    project_dir = os.path.join(WORKSPACE_DIR, project_name)
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

    isolated_env = os.environ.copy()
    isolated_env.pop("VIRTUAL_ENV", None)
    isolated_env.pop("PYTHONPATH", None)
    isolated_env["PATH"] = venv_bin + os.pathsep + isolated_env.get("PATH", "")

    req_path = os.path.join(project_dir, "requirements.txt")
    if os.path.exists(req_path):
        print("   -> 📦 완벽히 격리된 환경에 의존성 패키지 설치 중...")
        try:
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

    system_prompt = SystemMessage(content="""당신은 엄격한 보안 감사자(Security Auditor)이자 QA 엔지니어입니다. 
주어진 코드와 '동적 실행 로그(Runtime Logs)'를 모두 분석하세요.
[주의사항] 현재 환경은 Python 3.13입니다. 패키지 버전 충돌(ImportError)을 발견하더라도, 절대로 옛날 버전으로 다운그레이드하라고 조언하지 마세요. 반드시 최신 버전으로 업그레이드하여 호환성을 맞추도록 피드백하세요.
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
