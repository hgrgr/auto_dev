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
    md_ticks = "```"
    
    # ---------------------------------------------------------
    # 1. 테스트 환경 세팅 및 서버 구동
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

    backend_log_path = os.path.join(project_dir, "backend_run.log")
    frontend_log_path = os.path.join(project_dir, "frontend_run.log")
    b_log_file = open(backend_log_path, "w", encoding="utf-8")
    f_log_file = open(frontend_log_path, "w", encoding="utf-8")

    # 파이썬 로그 즉시 출력 강제 (버퍼링 무시)
    run_env = os.environ.copy()
    run_env["PYTHONUNBUFFERED"] = "1"

    try:
        print(f"   -> 🚀 백엔드({BACKEND_PORT})와 프론트엔드({FRONTEND_PORT}) 서버를 부팅합니다...")
        backend_proc = subprocess.Popen(
            [venv_python, "main.py"], 
            cwd=backend_dir, stdout=b_log_file, stderr=subprocess.STDOUT, 
            env=run_env, preexec_fn=os.setsid if os.name != 'nt' else None
        )
        
        frontend_proc = subprocess.Popen(
            ["npm", "run", "dev"], 
            cwd=frontend_dir, stdout=f_log_file, stderr=subprocess.STDOUT, 
            preexec_fn=os.setsid if os.name != 'nt' else None
        )
        time.sleep(6) # 서버 구동 대기
        
        # ---------------------------------------------------------
        # 2. [핵심] 동적 스크립트 작성 및 자가 치유(Reflexion) 루프
        # ---------------------------------------------------------
        max_retries = 3
        script_feedback = ""
        test_script_path = os.path.join(project_dir, "dynamic_e2e_runner.py")
        
        for attempt in range(max_retries):
            print(f"   -> 🧠 (시도 {attempt+1}/{max_retries}) 맞춤형 E2E 테스트 코드를 설계/수정 중...")

            gen_system_prompt = SystemMessage(content=f"""당신은 천재적인 QA 자동화 엔지니어입니다.
주어진 PRD와 API 명세서를 읽고, 실제 브라우저(Playwright sync)를 조작하여 기능을 검증하는 파이썬 스크립트를 작성하세요.

[스크립트 작성 규칙]
1. 프론트엔드 주소는 `http://localhost:{FRONTEND_PORT}` 입니다.
2. 🚨 반드시 `browser = p.chromium.launch(headless=True)` 로 실행하세요.
3. 🚨 [Playwright 타임아웃 문법 - 엄수]: 요소를 찾는 대기 시간은 짧게 설정하세요. 
   - ❌ [절대 금지]: `page.get_by_role('button', timeout=3000)` (get_by_role 등 로케이터에는 timeout 인자가 없습니다!)
   - ✅ [권장 방법]: `page.get_by_role('button').click(timeout=3000)`
4. 🚨 [매우 중요: 데이터 검증 및 올바른 로케이터 규칙]: 
   - 백엔드에서 받아온 데이터를 검증할 때는 반드시 API 명세서의 **응답 예시 데이터(예: "Cute Plush Toy", 15000 등)**가 화면에 렌더링되었는지 확인하세요! 절대 "Product Name", "Product Image" 같은 추상적인 필드명이나 플레이스홀더를 화면에서 찾으려 하지 마세요.
   - `get_by_role`의 첫 번째 인자는 반드시 유효한 HTML ARIA role(`button`, `link`, `img`, `textbox`, `heading` 등)만 사용하세요. 'Product Image' 같은 임의의 역할을 넣으면 절대 안 됩니다.
5. 🚨 [매우 중요: 예외 처리 규칙]: UI 요소가 없어서 발생하는 에러(TimeoutError)에 대비해 `try-except`를 사용하고, 예외 발생 시 구체적인 요소를 명시하여 `print("[Frontend Error] 'Cute Plush Toy' 텍스트를 가진 요소를 찾을 수 없습니다.")` 라고 출력하세요. 
   - ⚠️ [경고]: 단, `TypeError`나 파이썬 문법 에러는 절대 `except`로 조용히 넘기지 마세요! Traceback이 발생해야 당신의 코드를 스스로 고치는 자가 치유 루프가 작동합니다!
6. 오직 {md_ticks}python ... {md_ticks} 블록 안에 파이썬 코드만 작성하세요.""")
            
            gen_user_prompt = HumanMessage(
                content=f"[PRD]\n{requirements}\n[API Contract]\n{api_contract}\n{script_feedback}"
            )
            
            script_response = llm.invoke([gen_system_prompt, gen_user_prompt])
            test_code = extract_python_code(script_response.content)
            
            with open(test_script_path, "w", encoding="utf-8") as f:
                f.write(test_code)
                
            print(f"   -> 🏃‍♂️ 테스트 스크립트를 실행하고 자가 검증합니다...")
            tester_proc = subprocess.run([venv_python, test_script_path], capture_output=True, text=True, timeout=120)
            
            # 자가 검증 판독: 스크립트가 파이썬 문법 에러 없이 예쁘게 끝났는가? (returncode == 0)
            if tester_proc.returncode == 0 and "Traceback" not in tester_proc.stderr:
                execution_logs += f"\n[E2E TEST STDOUT]\n{tester_proc.stdout}\n[E2E TEST STDERR]\n{tester_proc.stderr}"
                break # 완벽하게 통과하거나, 에러를 try-except로 잘 잡아서 정상 종료한 경우 루프 탈출!
            else:
                print("   -> ⚠️ [Tester 자가 반성]: 작성한 파이썬 스크립트에서 예상치 못한 에러가 났습니다. 코드를 고칩니다!")
                script_feedback = f"""
🚨 [이전 시도 스크립트 실행 에러 발생]
아래 파이썬 에러 로그를 분석하여 당신의 코드를 스스로 수정하세요.
1. Playwright 문법 오류(TypeError 등)인 경우: 코드를 올바른 문법으로 고치세요.
2. UI 요소를 찾지 못한 경우(TimeoutError): 해당 코드를 try-except로 감싸고, 에러 사유를 print한 뒤 스크립트를 정상 종료되게 만드세요. 절대 Traceback으로 비정상 종료되게 두지 마세요!

[에러 로그]
{tester_proc.stderr}
"""
                if attempt == max_retries - 1:
                    critical_errors.append(f"테스터 스크립트 실패 로그:\n{tester_proc.stderr}")
                    print("   -> 🚨 [Tester 포기]: 3번의 시도에도 스크립트 에러를 완전히 잡지 못했습니다.")

    except subprocess.TimeoutExpired:
        critical_errors.append(f"테스트 인프라 타임아웃 에러: Playwright 스크립트 실행이 120초를 초과했습니다.")
    except Exception as e:
        critical_errors.append(f"테스트 인프라 에러: {str(e)}")
    finally:
        print("   -> 🧹 테스트 완료. 서버를 안전하게 종료합니다.")
        if backend_proc: 
            os.killpg(os.getpgid(backend_proc.pid), signal.SIGTERM) if os.name != 'nt' else backend_proc.terminate()
        if frontend_proc: 
            os.killpg(os.getpgid(frontend_proc.pid), signal.SIGTERM) if os.name != 'nt' else frontend_proc.terminate()
        b_log_file.close()
        f_log_file.close()

    # ---------------------------------------------------------
    # 3. 테스트 결과 종합 분석 및 Docs(test_report.md) 생성
    # ---------------------------------------------------------
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
API 명세서와 테스트 실행 로그, 그리고 서버 구동 로그를 종합적으로 분석하세요.

[분석 가이드라인]
1. 🚨 [가장 중요]: 실행 로그에 에러나 실패가 없다면(서버 로그가 비어있어도) 무조건 'PASS' 라고만 답변하세요.
2. 로그에 '[Frontend Error] ...' 가 있다면, 'FAIL_FRONTEND_DEV: [해당 로그 원문 그대로]' 형태로 프론트엔드 개발자에게 정확한 UI 누락을 지시하세요.
3. 🚨 [파이썬 에러 남탓 금지]: 만약 로그에 'TypeError', 'unexpected keyword argument', 'Traceback' 등 파이썬 테스트 스크립트 자체의 문법 에러가 남아있다면, 이건 프론트엔드나 백엔드 잘못이 아닙니다! 절대 'FAIL_FRONTEND_DEV'를 출력하지 말고, 차라리 'PASS'로 처리해서 프론트엔드 개발자가 파이썬 에러 때문에 억울하게 지시를 받는 일을 막으세요.
4. 타임아웃이나 파이썬 500 에러가 났다면 백엔드 서버 로그를 분석하여 'FAIL_BACKEND_DEV: [원인]'으로 지시하세요.""")

    eval_usr_prompt = HumanMessage(content=f"[API Contract]\n{api_contract}\n\n[Test & Server Logs]\n{log_summary}")
    
    eval_response = llm.invoke([eval_sys_prompt, eval_usr_prompt])
    result_text = eval_response.content.strip()

    if critical_errors and "FAIL" not in result_text:
        result_text = f"FAIL_FRONTEND_DEV: [시스템 강제 에러 할당] 테스트 중 오류가 발생했습니다.\n{result_text}"
    
    # --- Test Report Markdown 작성 ---
    report_path = os.path.join(project_dir, "docs", "test_report.md")
    status = "❌ FAILED" if "FAIL" in result_text else "✅ PASSED"
    
    report_content = f"""# E2E Test Report
- **Date:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- **Status:** {status}

## 🤖 Tester Feedback
{md_ticks}text
{result_text}
{md_ticks}

## 📝 Execution & Server Logs
{md_ticks}text
{log_summary}
{md_ticks}
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
