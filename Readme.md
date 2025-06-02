# Stock Analysis Dialogue Player

낙관적 분석가와 비관적 분석가 간의 구조화된 투자 토론을 생성하는 포괄적인 멀티모달 주식 분석 시스템입니다. AI가 생성한 대화와 text-to-speech 오디오 출력을 완벽하게 제공합니다.

## 🏗️ 프로젝트 구조

```
Multi_Modal/
├── README.md                    # 이 문서 파일
├── TODO.md                     # 프로젝트 로드맵과 작업 목록
├── code/                       # 핵심 애플리케이션 스크립트
│   ├── control_flow.py         # 메인 오케스트레이션 파이프라인
│   ├── streamlit_app.py        # 웹 UI 애플리케이션
│   ├── stock_data_extractor.py # Yahoo Finance 데이터 수집
│   ├── stock_data_refiner.py   # 원시 데이터를 markdown으로 변환
│   ├── fill_template.py        # 데이터로 템플릿 채우기
│   ├── fill_commentary.py     # AI 해설 생성
│   ├── generate_dialogue.py    # 대화 스크립트 생성
│   └── tts.py                  # Text-to-speech 변환
├── resources/                  # 설정 및 매핑 파일
│   ├── .env                    # API 키와 환경 변수
│   └── ui_mappings.json        # UI 표시명 매핑
├── stock_data/                 # 금융 데이터 저장소
│   ├── raw/                    # Yahoo Finance 원시 JSON 데이터
│   └── refined/                # 처리된 markdown 문서
├── grounds/                    # 템플릿과 해설 파일
├── dialogue/                   # 생성된 대화 스크립트
├── speaking/                   # 생성된 오디오 파일
└── podcast/                    # Virtual environment (선택사항)
```

## 🔄 Control Flow 프로세스 파이프라인

시스템은 `control_flow.py`에 의해 오케스트레이션되는 정교한 다단계 파이프라인을 따릅니다:

### 1단계: 정보 추출
**입력:** 사용자 질의 (예: "애플 주식에 대해 말해줘")
**처리 과정:** 
- `extract_company_info()`가 OpenAI GPT-4를 사용하여 자연어 질의를 파싱
- 표준화된 회사명과 ticker symbol 추출
- UI 표시를 위해 `ui_mappings.json` 업데이트

**출력:** 회사명 (예: "Apple Inc.")과 ticker symbol (예: "AAPL")

### 2단계: 병렬 처리 워크플로우

#### Main Flow
1. **데이터 추출** → `stock_data_extractor.py`
   - **입력:** Ticker symbol
   - **처리 과정:** Yahoo Finance API에서 포괄적인 금융 데이터 가져오기
   - **출력:** `stock_data/raw/{ticker}/`에 26개 이상의 JSON 파일

2. **데이터 정제 & 템플릿 채우기** (병렬)
   - **데이터 정제** → `stock_data_refiner.py`
     - **입력:** 원시 JSON 파일
     - **처리 과정:** JSON 데이터를 AI 분석과 함께 구조화된 markdown으로 변환
     - **출력:** `stock_data/refined/{ticker}/`에 정제된 markdown 파일
   
   - **템플릿 채우기** → `fill_template.py`
     - **입력:** 원시 JSON 파일
     - **처리 과정:** 주요 지표로 미리 정의된 템플릿 채우기
     - **출력:** `grounds/{ticker}/`에 템플릿 파일

3. **해설 생성** → `fill_commentary.py`
   - **입력:** 정제된 markdown 파일과 템플릿
   - **처리 과정:** AI 기반 투자 해설 생성
   - **출력:** 해설이 포함된 향상된 템플릿 파일

4. **대화 & 오디오 생성**
   - **입력:** 해설, 템플릿, 정제된 데이터
   - **처리 과정:** 구조화된 DIALOGUE_FLOW를 따라 스크립트와 오디오 생성
   - **출력:** `dialogue/{ticker}/`에 스크립트 파일, `speaking/{ticker}/`에 MP3 파일

#### Moderator Flow (병렬)
- **입력:** 회사 정보
- **처리 과정:** 사회자용 소개 스크립트와 오디오 생성
- **출력:** `intro.txt`와 `intro.mp3` 파일

### 3단계: 오디오 컴파일
- **입력:** 모든 개별 MP3 파일
- **처리 과정:** FFmpeg를 사용하여 DIALOGUE_FLOW 순서로 파일 병합
- **출력:** `combined.mp3` - 완전한 토론 오디오

## 📊 DIALOGUE_FLOW 구조

시스템은 5개 세그먼트 형식을 따르는 구조화된 토론을 생성합니다:

### 세그먼트 Flow 패턴
각 세그먼트는 일관된 발화자 패턴을 따릅니다:
1. **Development** - 지정된 관점의 초기 분석
2. **Response** - 반대 관점의 응답
3. **Development** - 반대 관점의 확장 분석  
4. **Response** - 원래 관점의 재반박
5. **Summary** - 사회자의 종합

### 세그먼트 개요

| 세그먼트 | 주제 | 주요 초점 | 핵심 파일 |
|---------|-------|---------------|-----------|
| **1. Fundamentals — Profitability** | ROE, ROA, 이익률, 매출 성장 | 재무 성과 지표 | `income_statement_*.md`, `financial_data.md` |
| **2. Financial Health & Cash-Flow** | 부채비율, 유동성, 현금흐름 추세 | 대차대조표 건전성 | `balance_sheet_*.md`, `cash_flow_*.md` |
| **3. Growth Drivers** | 시장 확장, 제품 포트폴리오, TAM 분석 | 사업 성장 잠재력 | `market_summary.md`, `corporate_events.md` |
| **4. Valuation & Market Sentiment** | P/E 비율, 애널리스트 목표가, 가격 모멘텀 | 시장 가격책정과 심리 | `valuation_measures.md`, `recommendation_trend.md` |
| **5. Risk & Technical Momentum** | 내부자 거래, ESG 요인, 기술적 지표 | 리스크 평가와 추세 | `major_holders.md`, `technical_insights.md` |

### 발화자 특성
- **낙관적 분석가:** 성장 기회, 긍정적 촉매제, 경쟁 우위에 집중
- **비관적 분석가:** 리스크, 도전과제, 밸류에이션 우려, 경쟁 위협 강조
- **사회자:** 균형 잡힌 종합, 주제 간 전환, 명확한 질문 제기

## 🎮 입출력 매핑

### 핵심 스크립트 입출력 참조

#### `control_flow.py`
- **입력:** 사용자 자연어 질의
- **출력:** 완전한 분석 패키지 (데이터, 스크립트, 오디오)
- **종속성:** 모든 다른 스크립트
- **기능:** 오케스트레이션, 병렬 처리, 오류 처리

#### `stock_data_extractor.py`
- **입력:** Ticker symbol (문자열)
- **출력:** 금융 데이터가 포함된 26개 이상의 JSON 파일
- **생성되는 주요 파일:**
  - `asset_profile.json` - 회사 개요 및 사업 설명
  - `financial_data.json` - 주요 재무 지표와 비율
  - `income_statement_yearly.json` - 연간 손익계산서
  - `balance_sheet_yearly.json` - 연간 대차대조표
  - `cash_flow_yearly.json` - 연간 현금흐름표
  - `price.json` - 현재 가격과 시장 데이터
  - `recommendation_trend.json` - 애널리스트 추천
  - `valuation_measures.json` - 밸류에이션 배수

#### `stock_data_refiner.py`
- **입력:** 개별 JSON 파일 + ticker symbol
- **출력:** AI 분석이 포함된 해당 markdown 파일
- **처리 과정:** 원시 금융 데이터를 사람이 읽기 쉬운 분석으로 변환
- **파일 매핑:** `{filename}.json` → `{filename}.md`

#### `fill_template.py`
- **입력:** Ticker symbol, 모든 원시 JSON 파일
- **출력:** `grounds/{ticker}/`에 채워진 템플릿 파일
- **생성되는 템플릿:**
  - 긍정적 투자 논리
  - 부정적 투자 논리
  - 중립적 요약 템플릿

#### `fill_commentary.py`
- **입력:** 템플릿 + 정제된 markdown 파일
- **출력:** AI 생성 해설이 포함된 향상된 템플릿
- **처리 과정:** 기본 템플릿에 맥락적 투자 인사이트 추가

#### `generate_dialogue.py`
- **입력:** Ticker, 회사명, segment/flow 매개변수
- **출력:** 개별 대화 스크립트
- **모드:**
  - `--type intro` - 사회자 소개
  - `--type single --segment X --flow Y` - 개별 대화 조각
- **파일 명명:** `seg{segment}_{speaker}_{type}_{flow}.txt`

#### `tts.py`
- **입력:** 텍스트 파일 경로, 출력 오디오 경로
- **출력:** MP3 오디오 파일
- **처리 과정:** OpenAI TTS API를 사용하여 텍스트를 음성으로 변환
- **음성 매핑:** 각 발화자 유형별로 다른 음성

#### `streamlit_app.py`
- **입력:** 웹 인터페이스를 통한 사용자 상호작용
- **출력:** 오디오 플레이어, 문서 뷰어, 프로세스 모니터링
- **기능:**
  - 진행률 표시줄이 있는 실시간 처리 상태
  - Ticker별 상태 관리가 있는 오디오 내비게이션
  - Markdown 렌더링이 있는 문서 탐색
  - 사이드바의 처리 로그 모니터링

## 🚀 사용법

### Command Line Interface
```bash
# 완전한 분석 워크플로우 시작
python code/control_flow.py "애플 주식 분석해줘"
python code/control_flow.py "테슬라의 투자 전망에 대해 말해줘"

# 개별 스크립트 실행
python code/stock_data_extractor.py AAPL
python code/generate_dialogue.py --ticker AAPL --company "Apple Inc." --type intro
```

### 웹 인터페이스
```bash
# Streamlit 애플리케이션 실행
cd code
streamlit run streamlit_app.py
```

웹 인터페이스는 다음을 제공합니다:
- **회사 선택** - 사용 가능한 분석에서 선택
- **오디오 플레이어** - 내비게이션 컨트롤 포함
- **문서 뷰어** - 기반이 되는 금융 데이터용
- **실시간 처리** 상태와 로그
- **대화 흐름** 구조 시각화

## 🔧 설정

### 환경 변수 (`.env`)
```env
OPENAI_API_KEY=your_openai_api_key_here
```

### UI 매핑 (`ui_mappings.json`)
```json
{
    "company_mappings": {
        "AAPL": "Apple Inc.",
        "TSLA": "Tesla, Inc."
    },
    "file_title_mappings": {
        "asset_profile.md": "기업 개요",
        "financial_data.md": "주요 재무 지표",
        "income_statement_yearly.md": "연간 손익계산서"
    }
}
```

## 📈 데이터 소스

- **Yahoo Finance API:** 모든 금융 데이터의 주요 소스
- **OpenAI GPT-4:** 자연어 처리 및 분석 생성
- **OpenAI TTS:** Text-to-speech 오디오 생성

## 🎯 주요 기능

1. **멀티모달 출력:** 텍스트 스크립트 + 오디오 파일 + 웹 인터페이스
2. **구조화된 분석:** 5개 세그먼트 토론 프레임워크
3. **병렬 처리:** 동시 실행을 통한 효율적인 워크플로우
4. **실시간 모니터링:** 진행 상황 추적 및 오류 처리
5. **확장 가능한 아키텍처:** 새로운 회사와 세그먼트 추가 용이
6. **전문적인 오디오:** 발화자 구분이 있는 고품질 TTS
7. **풍부한 문서화:** 금융 데이터의 포괄적인 markdown 분석

## 🔍 프로세스 모니터링

시스템은 상세한 로깅과 진행 상황 추적을 제공합니다:

- **파일 기반 진행률:** JSON → Markdown → Script → Audio 파이프라인의 완료도 추적
- **실시간 로그:** 서브프로세스 출력이 UI에 캡처되고 표시됨
- **오류 처리:** API 실패와 누락된 데이터의 우아한 처리
- **상태 관리:** 세션 간 처리 상태의 지속적 추적

## 🎵 오디오 시스템

- **개별 파일:** 각 대화 조각이 별도의 MP3 생성
- **결합 출력:** 모든 파일이 적절한 순서로 병합됨
- **발화자 음성:** 낙관적, 비관적, 사회자 역할별 구별되는 음성
- **품질 관리:** 적절한 속도와 톤을 가진 전문적인 TTS

이 시스템은 복잡한 금융 데이터를 구조화된 분석적 토론을 통해 균형 잡힌 투자 관점을 제공하는 접근 가능하고 매력적인 오디오 콘텐츠로 변환합니다.