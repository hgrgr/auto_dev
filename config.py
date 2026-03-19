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

# --- 에이전트 권한 및 능력 명세서 (Capability Matrix) ---
AGENT_CAPABILITIES = """
[에이전트 권한 및 한계 명세서]
1. PM (Product Manager):
   - 권한: 사용자의 요구사항을 분석하여 마크다운(MD) 형태의 기획서를 작성할 수 있습니다.
   - 한계: 코드를 작성하거나 아키텍처를 설계할 수 없습니다.

2. Architect (수석 아키텍트):
   - 권한: 기획서를 바탕으로 디렉토리 구조, DB 스키마, 함수 스펙을 설계합니다.
   - 한계: 실제 파이썬 코드를 작성하거나 실행할 수 없습니다.

3. Developer (개발자):
   - 권한: 파이썬 코드(.py)와 requirements.txt를 작성하고 수정할 수 있습니다.
   - 한계: 터미널 명령어를 실행할 수 없습니다. (예: openssl 인증서 생성, OS 레벨의 패키지 설치 불가). 시스템 외부 요인(인증서, DB 파일 부재 등)으로 인한 에러 발생 시, 코드를 수정하여 이를 우회(Bypass)하거나 Mocking해야 합니다.

4. QA (보안 감사자):
   - 권한: 작성된 코드를 샌드박스에서 실행하고 에러 로그를 수집합니다.
   - 한계: 코드를 직접 수정할 수 없습니다.
"""
