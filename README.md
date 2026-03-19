# 🏭 AI Software Factory v2.0

> **LLM 기반의 완전 자율형 애자일(Agile) 소프트웨어 개발 팩토리** <br>
> 자연어로 아이디어를 입력하면 설계, 코딩, QA, 문서화까지 다중 에이전트가 알아서 처리합니다.

![Python](https://img.shields.io/badge/Python-3.13-blue.svg)
![LangGraph](https://img.shields.io/badge/LangGraph-Multi_Agent-orange.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## ✨ 핵심 기능 (Key Features)

- 🤖 **다중 에이전트 협업:** PM, Architect, Developer, QA가 각자의 역할과 권한에 맞춰 코드를 생산합니다.
- ♻️ **자기 주도적 디버깅:** 에러 발생 시 QA와 Dev가 자체적으로 루프를 돌며 버그를 수정합니다.
- 🧐 **Supervisor 데드락 해결:** 3회 이상 에러가 반복되면 Supervisor가 등판하여 아키텍처 재설계나 코드 우회 지시를 내립니다.
- 🔄 **연속 스프린트 (Hydration):** 기존 프로젝트 폴더를 읽어와 컨텍스트를 복원하고, 기존 코드를 파괴하지 않으며 안전하게 새 기능을 덧붙입니다.
- 💡 **AI 기능 추천:** 개발 완료 후, 현재 시스템 상태를 분석하여 다음에 추가하면 좋을 기능을 AI가 먼저 제안합니다.

## 🏗️ 시스템 아키텍처 (Agent Workflow Diagram)

아래는 LangGraph를 통해 구현된 팩토리의 실제 동작 흐름도입니다.

```mermaid
graph TD
    %% 노드 정의
    Start([🚀 사용자 요구사항 입력])
    PM[📝 PM Agent\n명세서 작성/업데이트]
    Arch[📐 Architect Agent\n설계도 작성/업데이트]
    Dev[💻 Developer Agent\n코드 및 패키지 작성]
    QA{🛡️ QA/Security Agent\n샌드박스 동적 테스트}
    Super{🧐 Supervisor Agent\n데드락 분석 및 판단}
    Docs[📚 Tech Writer Agent\n공식 문서 작성]
    Human{👤 Human-in-the-Loop\n배포 승인 / 기능 추가}
    Deploy([🎉 프로덕션 배포])

    %% 흐름 연결
    Start --> PM
    PM --> Arch
    Arch --> Dev
    Dev --> QA

    %% QA 분기
    QA -- "PASS" --> Docs
    QA -- "FAIL (1~2회)\n단순 버그" --> Dev
    QA -- "FAIL (1~2회)\n구조 결함" --> Arch
    QA -- "FAIL (3회 이상)\n루프 감지" --> Super

    %% Supervisor 분기
    Super -- "지시: 아키텍처 재설계" --> Arch
    Super -- "지시: 코드 우회/수정" --> Dev
    Super -- "지시: 인간 개입 요청" --> Human

    %% 최종 승인 분기
    Docs --> Human
    Human -- "y (배포 승인)" --> Deploy
    Human -- "r (강제 재수정)" --> Dev
    Human -- "기타 텍스트\n(새 기능 요청)" --> PM

    %% 스타일링
    classDef agent fill:#f9f0ff,stroke:#b19cd9,stroke-width:2px,color:#000;
    classDef decision fill:#fff3cd,stroke:#ffeeba,stroke-width:2px,color:#000;
    classDef endnode fill:#d4edda,stroke:#c3e6cb,stroke-width:2px,color:#000;

    class PM,Arch,Dev,Docs agent;
    class QA,Super,Human decision;
    class Start,Deploy endnode;

## 🚀 시작하기 (Getting Started)

이 프로젝트를 로컬 환경에 구축하고 실행하는 방법입니다.

### 📋 사전 준비 (Prerequisites)
본 팩토리는 에이전트들의 엄격한 품질 관리를 위해 **Python 3.13** 환경을 권장합니다.
- Python 3.13 이상
- OpenAI API Key (GPT-4o 등 최신 모델 사용 권장)

### 🛠️ 설치 및 세팅 (Installation)

1. **저장소 클론 (Clone the repository)**
```bash
git clone [https://github.com/your-username/auto-software-factory.git](https://github.com/your-username/auto-software-factory.git)
cd auto-software-factory

2. **가상 환경 생성 및 활성화 (Virtual Environment)
```bash
python3 -m venv venv
# Linux/macOS
source venv/bin/activate  
# Windows
venv\Scripts\activate

3. **필수 패키지 설치(Install Dependecies)
```bash
pip install -r requirements.txt

4. **환경 변수 설정(Configuration)
```bash
# .env 파일 생성
echo "OPENAI_API_KEY=sk-your-api-key-here" > .env

5. **실행 방법(Usage)
```bash
python3 main.py

