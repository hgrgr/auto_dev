# state.py
import operator
from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    project_name: str
    requirements: str
    #architecture: str
    code_files: dict
    test_results: str
    needs_human_approval: bool
    qa_attempts: int
    human_decision: str
