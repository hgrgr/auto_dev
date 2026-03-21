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

    try:
        print(f"   -> 🚀 백엔드({BACKEND_PORT})와 프론트엔드({FRONTEND_PORT}) 서버를 부팅합니다...")
        
        backend_proc = subprocess.Popen(
            [venv_python, "main.py"], 
            cwd=backend_dir, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            preexec_fn=os.setsid if os.name != 'nt' else None
        )
        
        frontend_proc = subprocess.Popen(
            ["npm", "run", "dev"], 
            cwd=frontend_dir, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
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
            print("   -> 🚨 [Tester 발견 문제]: 일부 시나리오 테스트 실패 또는 통신 에러 감지!")

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

    # ---------------------------------------------------------
    # 4. 테스트 결과 분석 및 Docs(test_report.md) 생성
    # ---------------------------------------------------------
    log_summary = "\n".join(critical_errors)[:3000] if critical_errors else execution_logs[:3000]
    
    eval_sys_prompt = SystemMessage(content="""당신은 날카로운 E2E 테스터(QA)입니다.
API 명세서와 테스트 실행 로그를 분석하세요.
1. 결함이 없으면 'PASS' 라고만 답변하세요.
2. 프론트/백엔드 오류가 명확하다면 'FAIL_BACKEND_DEV: [이유]' 또는 'FAIL_FRONTEND_DEV: [이유]' 로 시작하는 피드백을 주세요.
3. 만약 화면(UI) 요소가 없어서 진행하지 못한 에러(Locator 에러)라면, 프론트엔드 개발자에게 해당 UI를 추가하라고 지시하세요.""")
    
    eval_usr_prompt = HumanMessage(
        content=f"[API Contract]\n{api_contract}\n\n[Test Logs]\n{log_summary}"
    )
    
    eval_response = llm.invoke([eval_sys_prompt, eval_usr_prompt])
    result_text = eval_response.content.strip()
    
    # --- Test Report Markdown 작성 ---
    report_path = os.path.join(project_dir, "docs", "test_report.md")
    status = "❌ FAILED" if "FAIL" in result_text else "✅ PASSED"
    
    # [핵심 수정] 파이썬 문자열 내부에 마크다운 백틱 3개가 들어가면 박스가 깨지므로 변수로 치환
    md_code_block = "```"
    
    report_content = f"""# E2E Test Report
- **Date:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- **Status:** {status}

## 🤖 Tester Feedback
{md_code_block}text
{result_text}
{md_code_block}

## 📝 Execution Logs
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
