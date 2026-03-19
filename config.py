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
