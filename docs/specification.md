# 🏭 AI Software Factory - 기술 명세서 (PRD)

## 1. 프로젝트 개요
**AI Software Factory**는 LangGraph 기반의 다중 에이전트 시스템(Multi-Agent System)으로, 사용자의 자연어 요구사항을 바탕으로 즉시 실행 가능한 Python 3.13 기반의 소프트웨어를 자동으로 설계, 개발, 검증, 문서화하는 자율형 개발 프레임워크입니다.

## 2. 핵심 아키텍처 (Core Architecture)
본 시스템은 단순한 선형 구조가 아닌, 애자일(Agile) 방법론과 에러 복구 기능을 포함한 복합 상태 머신(State Machine)으로 동작합니다.

* **상태 주입 (Context Hydration):** 중단된 프로젝트 재시작 시, 디스크의 기존 산출물(`specification.md`, `architecture.md`)을 읽어와 에이전트의 메모리(State)에 복원합니다.
* **이중 루프 시스템 (Dual-Loop Debugging):**
    * `Micro Loop`: 단순 버그 발생 시 Dev ↔ QA 간의 빠른 코드 수정 루프.
    * `Macro Loop`: 구조적 결함 발생 시 Architect부터 시작하는 전면 재설계 루프.
* **지능형 에스컬레이션 (Supervisor Triage):** 해결되지 않는 데드락(3회 이상 에러 반복) 발생 시, Supervisor 에이전트가 개입하여 에이전트의 권한(RBAC)을 바탕으로 작업 방향을 재설정합니다.

## 3. 에이전트 권한 및 역할 명세 (Capability Matrix)

| 에이전트 | 역할 (Role) | 주요 권한 및 한계 |
| :--- | :--- | :--- |
| **PM Agent** | 프로덕트 매니저 | 사용자 요구사항 분석 및 증분형(Incremental) 기술 명세서 작성. (코드 작성 불가) |
| **Architect Agent** | 수석 아키텍트 | 시스템 디렉토리, DB 스키마, API 스펙 설계. (기존 아키텍처 파괴 금지) |
| **Developer Agent** | 수석 개발자 | 설계도를 바탕으로 실제 Python 코드(`.py`) 및 의존성 작성. 환경 요인 에러 시 코드 레벨 우회(Bypass) 수행. (터미널 명령어 실행 불가) |
| **QA/Security Agent** | 보안 감사자 | 격리된 Venv(샌드박스) 환경에서 의존성 설치 및 동적/정적 코드 테스트 수행. 에러 로그 수집 및 판별. (코드 직접 수정 불가) |
| **Supervisor Agent** | 문제 해결사 | 3회 연속 에러 발생 시 개입. 원인 분석 후 타겟 에이전트(Dev/Arch) 지정 및 구체적 해결 행동 지침(Directive) 하달. |
| **Tech Writer Agent** | 테크니컬 라이터 | 최종 통과된 코드를 바탕으로 사용자 메뉴얼(`README.md`) 및 상세 스펙 문서 작성. |

## 4. 주요 지원 기능
* **스마트 프로젝트 로딩:** 기존 프로젝트 스캔 및 로딩, 현재 구현 기능 즉석 요약.
* **AI 넥스트 스텝 제안:** LLM이 현재 스펙을 분석하여 사용자에게 다음 스프린트에 필요한 핵심 기능 3가지 선제적 추천.
* **대화형 휴먼 루프 (Human-in-the-loop):** 배포 직전 인간의 승인을 받거나, 자연어로 새로운 요구사항을 입력받아 즉시 다음 버전을 개발하는 연속 스프린트 지원.
