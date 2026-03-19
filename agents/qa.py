# agents/qa.py 전체 교체
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
    current_attempts = state.get("qa_attempts", 0) + 1
    
    project_dir = os.path.join(WORKSPACE_DIR, project_name)
    
    code_files = {}
    if os.path.exists(project_dir):
        for root, _, files in os.walk(project_dir):
            if "venv" in root or "__pycache__" in root: 
                continue
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, project_dir)
                    with open(file_path, "r", encoding="utf-8") as f:
                        code_files[rel_path] = f.read()

    has_py_files = any(filename.endswith(".py") for filename in code_files.keys())
    if not has_py_files:
        print("   -> 🚨 [QA 발견 문제]: 실행할 파이썬(.py) 파일이 하나도 없습니다! 아키텍처 재설계 요청.")
        return {
            "test_results": "FAIL_ARCH: 파이썬 파일 누락", 
            "messages": [HumanMessage(content="파이썬 코드(.py)가 작성되지 않았거나 타 언어(Node.js 등)로 설계되었습니다. 아키텍처를 Python 3.13 기준으로 전면 재설계하세요.")], 
            "qa_attempts": current_attempts
        }

    code_content = "\n\n".join([f"--- {filename} ---\n{code}" for filename, code in code_files.items()])
    execution_logs = ""
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
    isolated_env["PATH"] = venv_bin + os.pathsep + isolated_env.get("PATH", "")
    isolated_env["PYTHONPATH"] = project_dir

    req_path = os.path.join(project_dir, "requirements.txt")
    if os.path.exists(req_path):
        print("   -> 📦 완벽히 격리된 환경에 의존성 패키지 설치 중...")
        try:
            # check=True로 인해 실패 시 바로 except 블록으로 넘어감
            subprocess.run([venv_pip, "install", "--upgrade", "-r", "requirements.txt"], cwd=project_dir, env=isolated_env, capture_output=True, text=True, check=True)
            print("   -> ✅ 패키지 설치 완료.")
        except subprocess.CalledProcessError as e:
            # [핵심 수정 1] pip install 실패 시 즉시 실행 중단 및 Dev 에이전트에게 반송 (LLM 안 거침)
            print(f"   -> 🚨 패키지 설치 실패 (치명적 오류):\n{e.stderr}")
            return {
                "test_results": "FAIL_DEV: 패키지 설치 실패", 
                "messages": [HumanMessage(content=f"[패키지 설치 치명적 오류]\nrequirements.txt의 패키지를 설치할 수 없습니다. 즉시 requirements.txt를 수정하세요.\n(예: psycopg2 설치 에러 시 psycopg2-binary로 교체)\n\n[에러 로그]\n{e.stderr}")], 
                "qa_attempts": current_attempts
            }

    # [핵심 수정 2] 개별 파일 실행 중 발생한 런타임 에러 추적
    critical_runtime_errors = []
    for filename in code_files.keys():
        if filename != "setup.py":
            filepath = os.path.join(project_dir, filename)
            print(f"   -> 🏃‍♂️ 샌드박스(격리 venv)에서 '{filename}' 실행 중...")
            try:
                result = subprocess.run([venv_python, filepath], cwd=project_dir, env=isolated_env, capture_output=True, text=True, timeout=3)
                
                # exit code가 0이 아니면 (비정상 종료) 강제로 에러로 간주
                if result.returncode != 0:
                    critical_runtime_errors.append(f"[{filename} 런타임 에러]\n{result.stderr}")
                    execution_logs += f"\n[❌ 치명적 런타임 에러 발생: {filename}]\n{result.stderr}\n"
                else:
                    execution_logs += f"\n--- {filename} 정상 실행됨 ---\n"
            except subprocess.TimeoutExpired:
                execution_logs += f"\n--- {filename} 정상 대기 (Timeout) ---\n"
            except Exception as e:
                critical_runtime_errors.append(f"[{filename} 시스템 에러]\n{str(e)}")

    # [수정 1] 치명적 런타임 에러 처리 프롬프트 확장
    if critical_runtime_errors:
        error_summary = "\n".join(critical_runtime_errors)
        system_prompt = SystemMessage(content="""당신은 엄격한 보안 감사자(Security Auditor)입니다.
현재 코드 실행 중 '치명적인 런타임 에러'가 발생했습니다.
오류의 성격을 분석하여 다음 두 가지 중 하나로 반드시 시작하여 해결책을 제시하세요:

1. 'FAIL_ARCH: [이유]' - (매크로 루프) 파이썬 버전(3.13)과 외부 라이브러리(SQLAlchemy 등) 간의 근본적 호환성 충돌, 프레임워크 교체 필요, 또는 데이터베이스/디렉토리 구조가 잘못된 경우.
2. 'FAIL_DEV: [이유]' - (마이크로 루프) 단순 오타, 모듈 임포트 경로 누락, 로직 에러 등 개발자가 코드만 수정하면 해결되는 경우.

절대 PASS를 반환해서는 안 됩니다.""")
        user_prompt = HumanMessage(content=f"발생한 에러 로그:\n{error_summary}")
    else:
        # [수정 2] 정상 실행 시 일반 분석 프롬프트도 기준을 명확히 확장
        system_prompt = SystemMessage(content="""당신은 엄격한 보안 감사자(Security Auditor)이자 QA 엔지니어입니다. 
주어진 프로젝트의 전체 코드와 '동적 실행 로그(Runtime Logs)'를 모두 분석하세요.
[주의사항] 현재 환경은 Python 3.13입니다.

결함이 발견되면 오류의 성격에 따라 다음 두 가지 중 하나로 시작하세요:
1. 'FAIL_ARCH: [이유]' - 파이썬 3.13 환경과 호환되지 않는 라이브러리 충돌, 프레임워크 전면 교체, 스키마/파일 구조 변경이 필요한 경우.
2. 'FAIL_DEV: [이유]' - 단순 버그, 오타, 누락 등 코딩 실수인 경우.

결함이 전혀 없고 배포 준비가 완료되었다면 'PASS'라고만 답변하세요.""")
        user_prompt = HumanMessage(content=f"전체 프로젝트 코드 내용:\n{code_content}\n\n동적 실행 로그:\n{execution_logs}")
    


    response = llm.invoke([system_prompt, user_prompt])
    review_result = response.content.strip()
    
    if review_result.startswith("FAIL_ARCH") or review_result.startswith("FAIL_DEV"):
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

        return {"test_results": fail_summary, "messages": [HumanMessage(content=review_result)], "qa_attempts": current_attempts}
    else:
        print("   -> ✅ [QA 통과]: 실행 에러 및 보안 결함이 없습니다.")
        return {"test_results": "PASS", "qa_attempts": current_attempts}
