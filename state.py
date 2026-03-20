# state.py 전체 교체
import operator
from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    # --- [1] 공통 컨텍스트 ---
    messages: Annotated[Sequence[BaseMessage], operator.add]
    project_name: str
    requirements: str

    # --- [2] API 명세 (새로 추가됨) ---
    api_contract: str  # PM이 작성한 프론트/백엔드 통신 규약 및 데이터 구조

    # --- [3] 백엔드 상태 (기존 architecture/code_files를 세분화) ---
    backend_architecture: str
    backend_code_files: dict

    # --- [4] 프론트엔드 상태 (새로 추가됨) ---
    frontend_architecture: str
    frontend_code_files: dict

    # --- [5] QA 및 제어 상태 (기존 코드 완벽 유지!) ---
    test_results: str
    qa_attempts: int
    supervisor_decision: str  # 예: backend_developer, frontend_architect, human 등
    supervisor_directive: str
    human_decision: str       # 사람의 개입 결과 (continue, revise 등)

