# state.py 전체 교체
import operator
from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    project_name: str
    requirements: str
    architecture: str
    code_files: dict
    test_results: str
    qa_attempts: int
    supervisor_decision: str  # [추가됨] Supervisor의 판단 (developer, architect, human)
    supervisor_directive: str
    human_decision: str
