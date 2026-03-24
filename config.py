import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# --- LLM 및 모델 설정 ---
DEFAULT_MODEL = "gpt-4o"
TEMPERATURE = 0

# --- 에이전트 및 시스템 규칙 ---
MAX_QA_ATTEMPTS = 3       # QA 에이전트 최대 재시도 횟수
RECURSION_LIMIT = 100     # LangGraph 전체 루프(보폭) 최대 제한

# --- 디렉토리 경로 설정 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_DIR = os.path.join(BASE_DIR, "workspace")

# config.py 하단에 추가

BACKEND_PORT = 8000
FRONTEND_PORT = 5173

# --- 에이전트 권한 및 능력 명세서 (Capability Matrix) ---
AGENT_CAPABILITIES = """
[에이전트 권한 및 한계 명세서]
1. PM (Product Manager):
   - 권한: 사용자의 요구사항을 분석하여 기획서(PRD)와 프론트/백엔드 간의 'API 명세서(Contract)'를 작성합니다.
   - 한계: 코드를 작성하거나 아키텍처를 직접 설계할 수 없습니다.

2. Backend Architect (백엔드 수석 아키텍트):
   - 권한: API 명세서를 바탕으로 백엔드(Python) 디렉토리 구조, DB 스키마, 함수/클래스 스펙을 설계합니다.
   - 한계: 실제 코드를 작성할 수 없으며, 프론트엔드 영역(React 등)은 절대 관여할 수 없습니다.

3. Backend Developer (백엔드 파이썬 개발자):
   - 권한: 백엔드 API 코드(.py)와 requirements.txt를 작성하고 수정할 수 있습니다 (backend/ 디렉토리 전담).
   - 한계: 프론트엔드 코드를 수정할 수 없습니다. 터미널 명령어를 실행할 수 없습니다 (openssl, OS 패키지 등). 시스템 외부 요인 에러 시 파이썬 코드를 수정하여 우회(Bypass)하거나 Mocking해야 합니다.

4. Frontend Architect (프론트엔드 수석 아키텍트):
   - 권한: 기획서와 API 명세서를 바탕으로 React UI 컴포넌트 구조, 라우팅, 상태 관리 구조를 설계합니다.
   - 한계: 실제 코드를 작성할 수 없으며, 백엔드 파이썬 영역은 절대 관여할 수 없습니다.

5. Frontend Developer (프론트엔드 React 개발자):
   - 권한: 프론트엔드 UI 코드(.js, .jsx, .html, .css)와 package.json을 작성하고 수정할 수 있습니다 (frontend/ 디렉토리 전담). 백엔드 API를 호출하는 로직을 구현합니다.
   - 한계: 백엔드 코드를 수정할 수 없습니다. 터미널 명령어(npm install 등)를 직접 칠 수 없으므로, 의존성 문제는 package.json을 수정하여 해결해야 합니다.

6. QA (보안 감사자) 및 Supervisor:
   - 권한: 코드를 격리 환경에서 테스트하고 에러 로그를 수집하여, 발생한 문제의 원인이 위 4개의 실무 역할 중 누구의 책임인지 판별해 정확히 타겟팅(Routing) 합니다.
   - 한계: 코드를 직접 수정할 수 없습니다.
"""
