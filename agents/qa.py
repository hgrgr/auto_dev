import os
import sys
import subprocess
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from state import AgentState
from config import DEFAULT_MODEL, TEMPERATURE, WORKSPACE_DIR

llm = ChatOpenAI(model=DEFAULT_MODEL, temperature=TEMPERATURE)

def security_qa_agent(state: AgentState):
    print("\n🤖 [Security/QA Agent]: 코드 정적 분석 및 샌드박스 동적 테스트를 시작합니다...")
    project_name = state.get("project_name", "unknown_project")
    current_attempts = state.get("qa_attempts", 0) + 1
    
    project_dir = os.path.join(WORKSPACE_DIR, project_name)
    
    code_files = {}
    if os.path.exists(project_dir):
        for root, _, files in os.walk(project_dir):
            # venv, node_modules 등 무거운 폴더는 제외
            if "venv" in root or "__pycache__" in root or "node_modules" in root: 
                continue
            for file in files:
                if file.endswith((".py", ".js", ".jsx", ".json")) and file not in ["package-lock.json", "yarn.lock"]:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, project_dir)
                    with open(file_path, "r", encoding="utf-8") as f:
                        code_files[rel_path] = f.read()

    has_py_files = any(filename.endswith(".py") for filename in code_files.keys())
    if not has_py_files:
        print("   -> 🚨 [QA 발견 문제]: 실행할 파이썬(.py) 파일이 하나도 없습니다! 아키텍처 재설계 요청.")
        return {"test_results": "FAIL_BACKEND_ARCH: 파이썬 코드가 전혀 존재하지 않습니다.", "qa_attempts": current_attempts}

    code_content = "\n\n".join([f"--- {filename} ---\n{code}" for filename, code in code_files.items()])
    
    # --- 샌드박스(가상환경) 생성 ---
    venv_dir = os.path.join(project_dir, "venv")
    if not os.path.exists(venv_dir):
        print(f"   -> 🛠️ 프로젝트 전용 가상환경(venv)을 '{venv_dir}'에 생성합니다...")
        subprocess.run([sys.executable, "-m", "venv", venv_dir], capture_output=True)
        
    if os.name == 'nt':
        venv_bin = os.path.join(venv_dir, "Scripts")
    else:
        venv_bin = os.path.join(venv_dir, "bin")
        
    pip_exe = os.path.join(venv_bin, "pip")
    python_exe = os.path.join(venv_bin, "python")

    # --- [핵심 수정 1] 백엔드 경로의 requirements.txt 설치 ---
    req_path = os.path.join(project_dir, "backend", "requirements.txt")
    if os.path.exists(req_path):
        print("   -> 📦 'backend/requirements.txt'를 발견하여 의존성을 설치합니다...")
        subprocess.run([pip_exe, "install", "-r", req_path], capture_output=True)
    
    execution_logs = ""
    critical_runtime_errors = []
    
    # --- [핵심 수정 2] 백엔드 경로의 main.py 실행 ---
    target_exec_file = None
    main_file = os.path.join(project_dir, "backend", "main.py")
    app_file = os.path.join(project_dir, "backend", "app.py")
    
    if os.path.exists(main_file):
        target_exec_file = main_file
    elif os.path.exists(app_file):
        target_exec_file = app_file

    if target_exec_file:
        rel_target_path = os.path.relpath(target_exec_file, project_dir)
        print(f"   -> 🏃‍♂️ 샌드박스(격리 venv)에서 '{rel_target_path}' 실행 중...")
        try:
            # 5초 타임아웃으로 실행
            result = subprocess.run([python_exe, target_exec_file], capture_output=True, text=True, timeout=5)
            execution_logs += f"\n[STDOUT]\n{result.stdout}\n[STDERR]\n{result.stderr}"
            
            if result.returncode != 0 and ("ModuleNotFoundError" in result.stderr or "SyntaxError" in result.stderr or "Traceback" in result.stderr):
                 critical_runtime_errors.append(result.stderr)
        except subprocess.TimeoutExpired:
            execution_logs += f"\n[INFO] '{rel_target_path}'가 5초 동안 에러 없이 실행되었습니다. (정상 구동 간주)"
    else:
        critical_runtime_errors.append("'backend/main.py' 또는 'backend/app.py' 파일이 존재하지 않아 서버를 실행할 수 없습니다.")

    # =====================================================================
    # [새로 추가할 부분 👇] 프론트엔드 동적 검증 (npm install & build 테스트)
    # =====================================================================
    frontend_dir = os.path.join(project_dir, "frontend")
    package_json_path = os.path.join(frontend_dir, "package.json")
    
    if os.path.exists(package_json_path):
        print("   -> 📦 'frontend/package.json'을 발견하여 npm 의존성을 설치합니다... (시간이 다소 소요될 수 있습니다)")
        try:
            # 1. npm install 실행 (의존성 설치)
            # 윈도우 환경이면 shell=True가 필요할 수 있으나, 리눅스/맥 환경을 상정하여 작성
            npm_install = subprocess.run(["npm", "install"], cwd=frontend_dir, capture_output=True, text=True, timeout=120)
            
            if npm_install.returncode != 0:
                critical_runtime_errors.append(f"[FAIL_FRONTEND_DEV: npm install 에러]\n{npm_install.stderr}")
            else:
                print("   -> 🏃‍♂️ 프론트엔드 빌드(npm run build) 테스트를 통해 문법/임포트 에러를 검증합니다...")
                # 2. npm run build 실행 (React 코드 트랜스파일링 및 문법/경로 오류 검출)
                npm_build = subprocess.run(["npm", "run", "build"], cwd=frontend_dir, capture_output=True, text=True, timeout=60)
                execution_logs += f"\n[FRONTEND BUILD STDOUT]\n{npm_build.stdout}\n[FRONTEND BUILD STDERR]\n{npm_build.stderr}"
                
                if npm_build.returncode != 0:
                    critical_runtime_errors.append(f"[FAIL_FRONTEND_DEV: React 빌드 에러]\n{npm_build.stderr}")
                else:
                    execution_logs += "\n[INFO] 프론트엔드 컴포넌트가 성공적으로 빌드되었습니다. (문법 및 임포트 정상)"
                    
        except FileNotFoundError:
            critical_runtime_errors.append("[FAIL_FRONTEND_ARCH: OS 환경 에러] 시스템에 'npm'이 설치되어 있지 않아 프론트엔드 테스트를 진행할 수 없습니다.")
        except subprocess.TimeoutExpired:
             critical_runtime_errors.append("[FAIL_FRONTEND_DEV: 빌드 타임아웃] 프론트엔드 설치/빌드 시간이 초과되었습니다.")
    else:
        critical_runtime_errors.append("[FAIL_FRONTEND_ARCH: 구조 결함] 'frontend/package.json' 파일이 없어 React 앱을 테스트할 수 없습니다.")


    # --- [핵심 수정 3] MSA 대응 프롬프트 분기 ---
    if critical_runtime_errors:
        error_summary = "\n".join(critical_runtime_errors)
        system_prompt = SystemMessage(content="""당신은 엄격한 보안 감사자(Security Auditor)이자 QA 엔지니어입니다.
현재 코드 실행 중 '치명적인 런타임 에러'가 발생했습니다.
오류의 성격과 발생 위치를 분석하여 다음 네 가지 중 하나로 반드시 시작하여 해결책을 제시하세요:

1. 'FAIL_BACKEND_ARCH: [이유]' - 파이썬 3.13 환경과 호환되지 않는 라이브러리 충돌, 프레임워크 전면 교체, 백엔드 스키마/파일 구조 변경이 필요한 경우.
2. 'FAIL_BACKEND_DEV: [이유]' - 백엔드 파이썬 코드(.py)의 단순 오타, 임포트 누락, 라이브러리 미설치(requirements.txt 누락) 등 백엔드 개발자가 코드만 수정하면 해결되는 경우.
3. 'FAIL_FRONTEND_ARCH: [이유]' - React 프론트엔드 컴포넌트의 근본적인 라우팅 구조 결함, 화면 설계 누락 등 프론트 아키텍처 변경이 필요한 경우.
4. 'FAIL_FRONTEND_DEV: [이유]' - React/JS 문법 에러, npm 패키지 누락(package.json), UI 렌더링 실패, 백엔드 API 호출 주소 매칭 오류 등 프론트엔드 개발자가 수정해야 할 경우.""")
        user_prompt = HumanMessage(content=f"발생한 에러 로그:\n{error_summary}")
        
    else:
        system_prompt = SystemMessage(content="""당신은 엄격한 보안 감사자(Security Auditor)이자 QA 엔지니어입니다. 
주어진 프로젝트의 전체 코드(백엔드 및 프론트엔드)와 '동적 실행 로그(Runtime Logs)'를 모두 분석하세요.
[주의사항] 백엔드 환경은 Python 3.13이며, 프론트엔드는 React 기반입니다.

[🚨 절대 규칙 - 과도한 정적 분석 금지]
1. 동적 실행 로그에서 '치명적 런타임 에러'가 발생하지 않았다면, 정적 분석 과정에서 가설적인 에러(예: 로깅 포맷 불일치, KeyError 발생 가능성 추측, 단순 코드 스타일 등)를 지적하여 FAIL을 주지 마세요.
2. 오직 명백한 문법 에러(SyntaxError), 심각한 보안 취약점(SQL Injection, 하드코딩된 비밀번호, CORS 설정 누락 등), 또는 애플리케이션 구동을 즉각적으로 불가능하게 만드는 치명적 결함만 지적하세요.
3. 사소한 경고(Warning)나 로깅, 타입 힌팅 문제는 무조건 무시하고 PASS 처리하세요.

결함이 발견되면 오류의 성격과 발생 위치에 따라 반드시 아래 4가지 접두사 중 하나로 시작하여 답변하세요.
- 'FAIL_BACKEND_ARCH: [이유]'
- 'FAIL_BACKEND_DEV: [이유]'
- 'FAIL_FRONTEND_ARCH: [이유]'
- 'FAIL_FRONTEND_DEV: [이유]'

위 기준에 부합하는 치명적 결함이 없다면, 다른 말은 일절 덧붙이지 말고 오직 'PASS' 라고만 답변하세요.""")

        user_prompt = HumanMessage(content=f"전체 프로젝트 코드 내용:\n{code_content}\n\n동적 실행 로그:\n{execution_logs}")

    response = llm.invoke([system_prompt, user_prompt])
    result_text = response.content.strip()
    
    if "FAIL" in result_text:
        # 줄바꿈이 포함될 수 있으므로 첫 줄의 에러 유형만 깔끔하게 출력
        short_error = result_text.split("\n")[0]
        print(f"   -> 🚨 [QA 발견 문제]: {short_error}")
    else:
        print("   -> ✅ [QA 통과]: 치명적 결함이 발견되지 않았습니다.")
        
    return {"test_results": result_text, "qa_attempts": current_attempts}
