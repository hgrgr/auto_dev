import os
import time
import signal
import subprocess
import re
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from state import AgentState
from config import DEFAULT_MODEL, TEMPERATURE, WORKSPACE_DIR, BACKEND_PORT, FRONTEND_PORT

llm = ChatOpenAI(model=DEFAULT_MODEL, temperature=TEMPERATURE)

def extract_python_code(text):
    """LLM 응답에서 파이썬 코드만 깔끔하게 추출합니다."""
    match = re.search(r'```python\n(.*?)\n```', text, re.DOTALL)
    if match:
        return match.group(1)
    return text.strip()

def e2e_tester_agent(state: AgentState):
    print("\n🕵️ [Tester Agent]: 문서를 참조하여 동적 E2E 테스트 시나리오를 설계하고 실행합니다...")
    project_name = state.get("project_name", "unknown_project")
    project_dir = os.path.join(WORKSPACE_DIR, project_name)
    
    requirements = state.get("requirements", "")
    api_contract = state.get("api_contract", "")
    
    # ---------------------------------------------------------
    # 1. 문서 기반 '동적 Playwright 스크립트' 생성 (LLM 호출)
    # ---------------------------------------------------------
    print("   -> 🧠 API 명세서와 기획서를 분석하여 맞춤형 테스트 코드를 작성 중...")
    
    # 마크다운 렌더링 오류를 막기 위해 백틱을 변수로 분리 (프롬프트용)
    md_ticks = "```"
    
    gen_system_prompt = SystemMessage(content=f"""당신은 천재적인 QA 자동화 엔지니어입니다.
주어진 PRD와 API 명세서를 읽고, 실제 브라우저(Playwright)를 조작하여 
주요 기능을 검증하는 파이썬 테스트 스크립트를 작성하세요.

[스크립트 작성 규칙]
1. 프론트엔드 주소는 `http://localhost:{FRONTEND_PORT}` 입니다.
2. 🚨 [매우 중요]: `playwright.sync_api`를 사용하되, GUI가 없는 서버 환경이므로 반드시 브라우저를 헤드리스 모드로 실행하세요! (예: `browser = p.chromium.launch(headless=True)`)
3. 소스 코드를 볼 수 없는 상태이므로, 화면의 텍스트나 placeholder를 기반으로 요소를 찾으세요.
   (예: `page.get_by_placeholder('Email').fill(...)`, `page.get_by_role('button', name='Login').click()`)
4. 각 기능(회원가입, 로그인 등)을 테스트할 때 `try-except`로 감싸서, 
   특정 버튼이 없더라도 스크립트가 멈추지 않고 다음 테스트로 넘어가도록 견고하게 작성하세요.
5. 브라우저 콘솔 에러(`page.on("console")`)와 네트워크 에러를 반드시 수집하여 마지막에 print 하세요.
6. 응답은 반드시 {md_ticks}python ... {md_ticks} 블록 안에 실행 가능한 파이썬 코드만 작성하세요.""")

    gen_user_prompt = HumanMessage(
        content=f"[PRD]\n{requirements}\n\n[API Contract]\n{api_contract}"
    )
    
    script_response = llm.invoke([gen_system_prompt, gen_user_prompt])
    test_code = extract_python_code(script_response.content)
    
    # 생성된 스크립트 저장
    test_script_path = os.path.join(project_dir, "dynamic_e2e_runner.py")
    with open(test_script_path, "w", encoding="utf-8") as f:
        f.write(test_code)

    # ---------------------------------------------------------
    # 2. 샌드박스 서버 구동 및 테스트 환경 세팅
    # ---------------------------------------------------------
    backend_dir = os.path.join(project_dir, "backend")
    frontend_dir = os.path.join(project_dir, "frontend")
    
    if os.name == 'nt':
        venv_python = os.path.join(project_dir, "venv", "Scripts", "python")
        venv_pip = os.path.join(project_dir, "venv", "Scripts", "pip")
    else:
        venv_python = os.path.join(project_dir, "venv", "bin", "python")
        venv_pip = os.path.join(project_dir, "venv", "bin", "pip")
    
    print("   -> 📦 샌드박스(venv)에 Playwright 환경을 세팅합니다...")
    subprocess.run([venv_pip, "install", "playwright"], capture_output=True)
    subprocess.run([venv_python, "-m", "playwright", "install", "chromium"], capture_output=True)

    backend_proc = None
    frontend_proc = None
    execution_logs = ""
    critical_errors = []

    # [수정됨] 서버 로그를 디스크에 기록하기 위해 파일 객체 오픈
    backend_log_path = os.path.join(project_dir, "backend_run.log")
    frontend_log_path = os.path.join(project_dir, "frontend_run.log")
    b_log_file = open(backend_log_path, "w", encoding="utf-8")
    f_log_file = open(frontend_log_path, "w", encoding="utf-8")

    run_env = os.environ.copy()
    run_env["PYTHONUNBUFFERED"] = "1"

    try:
        print(f"   -> 🚀 백엔드({BACKEND_PORT})와 프론트엔드({FRONTEND_PORT}) 서버를 부팅합니다...")
        
        # [수정됨] stdout과 stderr를 물리적 로그 파일로 리다이렉션
        backend_proc = subprocess.Popen(
            [venv_python, "main.py"], 
            cwd=backend_dir, 
            stdout=b_log_file, 
            stderr=subprocess.STDOUT, 
            env=run_env,  # <--- [추가됨] 환경변수 주입
            preexec_fn=os.setsid if os.name != 'nt' else None
        )
        
        frontend_proc = subprocess.Popen(
            ["npm", "run", "dev"], 
            cwd=frontend_dir, 
            stdout=f_log_file, 
            stderr=subprocess.STDOUT, 
            preexec_fn=os.setsid if os.name != 'nt' else None
        )

        time.sleep(6) # 서버 구동 대기
        
        # ---------------------------------------------------------
        # 3. 생성된 동적 테스트 실행
        # ---------------------------------------------------------
        print("   -> 🏃‍♂️ 동적 생성된 브라우저 시나리오 테스트를 실행합니다...")
        
        tester_proc = subprocess.run(
            [venv_python, test_script_path], 
            capture_output=True, 
            text=True, 
            timeout=60
        )
        
        execution_logs += f"\n[E2E TEST STDOUT]\n{tester_proc.stdout}\n[E2E TEST STDERR]\n{tester_proc.stderr}"
        
        if tester_proc.returncode != 0 or "Error" in tester_proc.stdout or "Exception" in tester_proc.stderr:
            critical_errors.append(tester_proc.stdout + "\n" + tester_proc.stderr)
            print("   -> 🚨 [Tester 발견 문제]: 시나리오 테스트 실패 또는 서버 통신 에러 감지!")

    except subprocess.TimeoutExpired:
        critical_errors.append(f"테스트 인프라 타임아웃 에러: Playwright 스크립트 실행이 60초를 초과했습니다. 서버가 제대로 켜지지 않았을 확률이 높습니다.")
    except Exception as e:
        critical_errors.append(f"테스트 인프라 에러: {str(e)}")
    finally:
        print("   -> 🧹 테스트 완료. 서버를 안전하게 종료합니다.")
        if backend_proc: 
            if os.name != 'nt':
                os.killpg(os.getpgid(backend_proc.pid), signal.SIGTERM)
            else:
                backend_proc.terminate()
        if frontend_proc: 
            if os.name != 'nt':
                os.killpg(os.getpgid(frontend_proc.pid), signal.SIGTERM)
            else:
                frontend_proc.terminate()
                
        # 로그 파일 닫기
        b_log_file.close()
        f_log_file.close()
 

    # ---------------------------------------------------------
    # 4. 테스트 결과 분석 및 Docs(test_report.md) 생성
    # ---------------------------------------------------------
    # [핵심 추가] 저장된 백엔드/프론트엔드 서버 로그를 읽어와서 에이전트에게 전달
    server_logs_context = ""
    try:
        with open(backend_log_path, "r", encoding="utf-8") as bf:
            server_logs_context += f"\n\n[BACKEND SERVER LOGS]\n{bf.read()[-2000:]}"
        with open(frontend_log_path, "r", encoding="utf-8") as ff:
            server_logs_context += f"\n\n[FRONTEND SERVER LOGS]\n{ff.read()[-2000:]}"
    except Exception:
        pass

    log_summary = ("\n".join(critical_errors)[:3000] if critical_errors else execution_logs[:3000]) + server_logs_context
    
    eval_sys_prompt = SystemMessage(content="""당신은 날카로운 E2E 테스터(QA)입니다.
API 명세서와 테스트 실행 로그, 그리고 백엔드/프론트엔드 서버 구동 로그를 종합적으로 분석하세요.

[분석 가이드라인]
1. 🚨 [가장 중요]: 실행 로그(Execution Logs)에 에러나 실패가 없다면 무조건 'PASS' 라고만 답변하세요. (서버 로그가 비어있는 것은 서버가 에러 없이 조용히 잘 돌아갔다는 뜻입니다. 절대 로그가 없다고 꼬투리 잡거나 FAIL 처리하지 마세요!)
2. 타임아웃이나 실제 에러가 발생했을 때만 [BACKEND/FRONTEND SERVER LOGS]를 확인하여 원인을 파악하세요.
3. 서버 에러가 원인이라면 'FAIL_BACKEND_DEV: [원인]' 또는 'FAIL_FRONTEND_DEV: [원인]'으로 피드백을 주세요.
4. 만약 화면(UI) 요소가 없어서 진행하지 못한 에러라면, 프론트엔드 개발자에게 해당 UI를 추가하라고 지시하세요.""")

    eval_usr_prompt = HumanMessage(
        content=f"[API Contract]\n{api_contract}\n\n[Test & Server Logs]\n{log_summary}"
    )
    
    eval_response = llm.invoke([eval_sys_prompt, eval_usr_prompt])
    result_text = eval_response.content.strip()

    # 파이썬 레벨의 강제 에러 할당 (LLM이 FAIL을 안 뱉을 경우 방어)
    if critical_errors and "FAIL" not in result_text:
        result_text = f"FAIL_FRONTEND_DEV: [시스템 강제 에러 할당] 테스트 중 오류가 발생했습니다. 로그를 확인하세요.\n{result_text}"
    
    # --- Test Report Markdown 작성 ---
    report_path = os.path.join(project_dir, "docs", "test_report.md")
    status = "❌ FAILED" if "FAIL" in result_text else "✅ PASSED"
    
    md_code_block = "```"
    
    report_content = f"""# E2E Test Report
- **Date:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- **Status:** {status}

## 🤖 Tester Feedback
{md_code_block}text
{result_text}
{md_code_block}

## 📝 Execution & Server Logs
{md_code_block}text
{log_summary}
{md_code_block}
"""
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    print(f"   -> 📝 훌륭합니다! [docs/test_report.md]에 테스트 리포트가 기록되었습니다.")

    if "FAIL" in result_text:
        short_error = result_text.split("\n")[0]
        print(f"   -> 🚨 [Tester 판독 결과]: {short_error}")
    else:
        print("   -> ✅ [Tester 통과]: 모든 시나리오 및 프론트-백엔드 연동이 완벽합니다!")
        
    return {"test_results": result_text, "qa_attempts": state.get("qa_attempts", 0) + 1}
