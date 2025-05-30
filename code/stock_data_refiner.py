#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import time

# OpenAI API 관련 임포트
from openai import OpenAI
from openai import APIError, RateLimitError
from dotenv import load_dotenv

# 현재 파일의 디렉토리를 기준으로 경로 설정
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
STOCK_DATA_DIR = PROJECT_ROOT / "stock_data"
RAW_DATA_DIR = STOCK_DATA_DIR / "raw"
REFINED_DATA_DIR = STOCK_DATA_DIR / "refined"
ENV_FILE = PROJECT_ROOT / "resources" / ".env"

# 환경 변수 로드
load_dotenv(ENV_FILE)

# OpenAI 클라이언트 초기화
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("경고: OPENAI_API_KEY가 설정되지 않았습니다. .env 파일을 확인해주세요.")
    sys.exit(1)

client = OpenAI(api_key=OPENAI_API_KEY)

# 시계열 분석이 필요하지 않은 파일들 (정적 정보)
NON_TIMESERIES_FILES = {
    "asset_profile", #
    "esg_scores", #
    "financial_data",#
    "insider_holders",
    "institution_ownership",
    "key_stats",#
    "major_holders",
    "market_summary",
    "option_chain",
    "price",#
    "quotes",
    "summary_detail",#
    "technical_insights"
}

# 시계열 분석이 필요한 파일들 (시간적 변화 분석 필요)
TIMESERIES_FILES = {
    "history_long_term",
    "history_middle_term", 
    "history_short_term",
    "income_statement_quarter",
    "income_statement_yearly",
    "balance_sheet_quarter",
    "balance_sheet_yearly",
    "cash_flow_quarter",
    "cash_flow_yearly",
    "all_financial_data_quarterly",
    "all_financial_data_annual",
    "recommendation_trend",
    "earnings_trend",
    "earning_history",
    "grading_history",
    "valuation_measures",
    "insider_transactions",
    "corporate_events",
    "sec_filings"
}


def create_non_timeseries_prompt(file_name: str, data: Any) -> str:
    """시계열이 아닌 정적 데이터에 대한 프롬프트 생성"""
    
    prompts = {
        "asset_profile": """
다음은 기업의 자산 프로필(JSON 형식) 데이터입니다. 이 데이터를 기반으로 **투자자를 위한 고품질 마크다운 분석 리포트**를 작성해주세요.

## 작성 형식 및 요구사항:

1. **문체**: "~임", "~함" 형태의 간결하고 단정적인 서술체로 작성. 군더더기 없이 정보를 요약 정리할 것.
2. **형식**: 마크다운(Markdown) 형식으로 정리. 보기 쉽게 제목, 소제목, 표 등을 활용해 구조화할 것.
3. **내용 구성**: 아래 항목을 반드시 포함하고, 필요시 세부 항목을 추가하여 분석을 심화할 것.

---

### 1. 회사 개요
- 회사명, 본사 위치, 설립 연도, 총 직원 수
- 산업군(Sector), 산업 세부 분류(Industry)

### 2. 사업 영역
- 제품/서비스 라인업 구체적으로 설명
- 수익 구조, 유통 경로, 고객군 등을 포함
- 플랫폼 및 구독 서비스 구성도 상세히 기술

### 3. 경영진
- CEO 및 핵심 임원진 리스트 표로 정리 (이름, 직책, 나이, 총보수 등)
- 리더십 팀의 경력 또는 전략적 기여가 드러나도록 요약

### 4. 연락처 정보
- 공식 웹사이트, 투자자 관계 사이트(IR), 전화번호, 본사 주소

### 5. 기업 지배구조 및 리스크
- 리스크 지표 (감사, 이사회, 보상, 주주 권리 등)를 표 또는 리스트로 정리
- 각 리스크 항목에 대해 간단한 해석과 투자자 관점의 시사점 추가

### 6. 투자 포인트
- 수익성, 성장성, 시장지위, 브랜드 가치, 서비스 다각화 등 투자자에게 중요한 요소 중심으로 통찰 제공
- 장단기 투자자 모두가 참고할 수 있는 인사이트 중심 서술

### 7. 결론
- 전반적인 투자 매력도 요약
- 핵심 요인(강점/우려점 포함)을 정리하고, 주기적인 모니터링 포인트 제시

---

> 마크다운 문서는 **전문 투자 리서치 문서 수준**의 완성도를 갖추도록 구성해주세요. 설명은 간결하되 깊이 있는 분석이 반영되어야 하며, 단순 나열이 아닌 통합적 이해를 돕는 방식으로 서술할 것.

""",
        
        "esg_scores": """
다음은 특정 기업의 ESG(환경, 사회, 지배구조) 점수 데이터(JSON 형식)입니다. 이 데이터를 기반으로 투자자에게 유용한 **전문적인 ESG 분석 리포트**를 마크다운 형식으로 작성해주세요.

## 작성 규칙 및 스타일

- **문체**: "~임", "~함" 형태의 단문 서술체로 작성
- **형식**: Markdown 형식으로 작성하고, 각 항목을 제목 및 표 형식으로 구조화
- **초점**: 각 지표별로 빠짐없이 구체적인 분석을 수행할 것

---

## 리포트에 반드시 포함할 분석 항목

### 1. ESG 전체 개요
- `totalEsg`: ESG 총점 
- `esgPerformance`: 등급 (예: AVG_PERF) 해석
- `ratingYear`, `ratingMonth`: 평가 기준 시점 명시
- `highestControversy`: 최고 논란 수치와 그 의미
- `relatedControversy`: 논란의 성격 설명 (예: Customer Incidents)

### 2. 환경(Environmental)
- `environmentScore`: 환경 점수 상세 분석
- `peerEnvironmentPerformance` 내의 `min`, `avg`, `max`와 비교
- `environmentPercentile`: 백분위 수치가 있는 경우 해석
- 친환경 활동 부족 여부 및 환경 리스크 해석

### 3. 사회(Social)
- `socialScore`: 사회적 책임 점수 분석
- `peerSocialPerformance` 내 `min`, `avg`, `max`와 비교
- `socialPercentile`: 값이 존재할 경우 백분위 해석
- 다양성, 인권, 노동환경, 고객 안전 측면 해석

### 4. 지배구조(Governance)
- `governanceScore`: 지배구조 점수 분석
- `peerGovernancePerformance` 내 `min`, `avg`, `max`와 비교
- `governancePercentile`: 존재 시 해석
- 이사회 구성, 투명성, 윤리경영 관점 해석

### 5. 동종업계 비교
- `peerGroup`: 동종업계 명칭 명시
- 총점 및 각 항목별 점수를 업계 평균 대비 표로 요약
- `peerCount`: 비교 대상 기업 수를 포함

### 6. 논란 및 민감 산업 여부
- `highestControversy`, `relatedControversy`: 구체적으로 분석
- 아래의 업종 민감도 플래그(`true` 또는 `false`)를 기반으로 해석 포함:
  - `adult`, `alcoholic`, `animalTesting`, `controversialWeapons`, `smallArms`, `furLeather`, `gambling`, `gmo`, `militaryContract`, `nuclear`, `pesticides`, `palmOil`, `coal`, `tobacco`

### 7. 투자 관점에서의 해석
- ESG 각 항목이 투자 리스크 또는 기회로 작용할 수 있는 근거 설명
- 해당 점수 수준이 ESG 투자 기준에 부합하는지 여부 평가
- 장기적 관점에서의 지속가능성, 평판 리스크 가능성 포함

---

> 분석은 단순 수치 나열이 아닌, 각 지표가 기업의 지속 가능성과 투자 판단에 미치는 영향을 중심으로 통찰력 있게 작성할 것.

""",
        
        "financial_data": """
다음은 특정 기업의 주요 재무 데이터(JSON 형식)입니다. 이 데이터를 기반으로 투자자에게 유용한 **정량적 재무 분석 마크다운 리포트**를 작성해주세요.

## 작성 규칙 및 스타일

- **문체**: "~임", "~함" 형태의 간결한 단문 중심 서술체
- **형식**: Markdown으로 작성, 제목/소제목 및 표/리스트 등을 적절히 활용해 시각적으로 명확하게 구성
- **초점**: 각 지표별로 빠짐없이 분석하고, 투자자 관점에서 해석할 것

---

## 반드시 포함해야 할 분석 항목

### 1. 수익성 지표
- `totalRevenue`: 총 매출
- `grossProfits`: 매출총이익
- `operatingCashflow`: 영업활동현금흐름
- `ebitda`: EBITDA
- `profitMargins`: 순이익률
- `operatingMargins`: 영업이익률
- `grossMargins`: 매출총이익률
- `ebitdaMargins`: EBITDA 마진

→ 각 항목이 기업의 수익 창출력, 비용 구조, 효율성 측면에서 어떤 의미를 가지는지 해석할 것.

---

### 2. 재무 건전성
- `totalCash`: 총 현금
- `totalDebt`: 총 부채
- `debtToEquity`: 부채비율
- `quickRatio`: 당좌비율
- `currentRatio`: 유동비율

→ 유동성, 단기 및 장기 채무 상환능력, 재무 안정성 측면에서 평가할 것.

---

### 3. 성장성 지표
- `revenueGrowth`: 매출 성장률
- `earningsGrowth`: 순이익 성장률

→ 최근 실적 기반의 성장 추세 분석 및 향후 확장 가능성에 대한 판단 포함.

---

### 4. 효율성 지표
- `returnOnAssets (ROA)`: 자산 수익률
- `returnOnEquity (ROE)`: 자기자본 수익률

→ 자본 효율성 및 기업 운영의 생산성 측면에서 분석할 것.

---

### 5. 배당 정보
- 배당 관련 항목이 제공되지 않은 경우, `"배당 미지급 기업임"` 등 명확히 기재
- 배당률(`dividendYield` 등)이 있다면, 과거 배당 정책이나 지속 가능성도 함께 해석

---

### 6. 시장 기대치 및 투자 의견
- `currentPrice`: 현재 주가
- `targetHighPrice`, `targetLowPrice`, `targetMeanPrice`, `targetMedianPrice`: 목표 주가 범위
- `recommendationKey`: 애널리스트 투자 의견 (예: Buy, Hold 등)
- `numberOfAnalystOpinions`: 애널리스트 수
- `recommendationMean`: 점수 기반 투자 의견 평균

→ 시장이 해당 종목을 어떻게 평가하는지, 현재 주가와 목표 주가 간 괴리를 통해 향후 상승 여력 판단

---

### 7. 재무 종합 평가
- 위 지표들을 종합하여 기업의 전반적인 재무 건전성, 수익성, 성장성, 효율성, 시장 신뢰도를 종합적으로 평가할 것
- 투자자 관점에서 이 기업이 재무적으로 매력적인지, 리스크는 무엇인지 정리

---

> 지표 간 비교, 수치 해석, 재무 상태에 대한 전략적 통찰을 포함한 리포트를 생성해주세요. 단순 나열이 아닌, 통합적 시각에서 투자자의 판단을 도울 수 있도록 분석할 것.

""",
        
        "key_stats": """
다음은 특정 기업의 핵심 통계 데이터(JSON 형식)입니다. 이 데이터를 기반으로 투자자 관점에서 유용한 **마크다운 형식의 분석 리포트**를 작성해주세요.

## 작성 규칙 및 스타일

- **문체**: "~임", "~함" 형태의 간결한 단문 중심 서술체
- **형식**: Markdown으로 구성하고, 각 항목을 제목/소제목으로 명확하게 구분
- **분석 수준**: 각 지표별로 구체적 수치를 해석하고, 투자자 입장에서 그 의미와 시사점을 명확히 설명할 것

---

## 반드시 포함해야 할 분석 항목

### 1. 밸류에이션 지표
- `forwardPE`: 예상 PER (주가수익비율)
- `priceToBook`: PBR (주가순자산비율)
- `enterpriseToRevenue`: EV/매출
- `enterpriseToEbitda`: EV/EBITDA

→ 각 지표의 절대적 수준뿐 아니라 일반적인 적정 범위 및 업계 평균과 비교하여 고평가/저평가 여부 해석

---

### 2. 시장 지표
- `enterpriseValue`: 기업가치 (EV)
- `beta`: 주가 변동성 (시장 민감도)
- `52WeekChange`: 52주 주가 변화율
- `SandP52WeekChange`: 동기간 S&P500 수익률과 비교
- `lastSplitFactor`, `lastSplitDate`: 주식 분할 이력 포함

→ 시장에서의 포지셔닝, 변동성 리스크, 분할 전후 효과 등 분석

---

### 3. 주식 관련 정보
- `sharesOutstanding`: 총 발행주식수
- `floatShares`: 유통주식수
- `impliedSharesOutstanding`: 암묵적 총 발행주식수
- `heldPercentInsiders`, `heldPercentInstitutions`: 내부자 및 기관 보유율
- `sharesShort`, `shortRatio`, `shortPercentOfFloat`: 공매도 관련 지표
- `sharesPercentSharesOut`: 공매도 비율

→ 유통 구조의 안정성, 내부자 매도 리스크, 공매도 추이 등을 평가

---

### 4. 수익성 및 배당 지표
- `trailingEps`, `forwardEps`: 과거 및 예상 주당순이익 (EPS)
- `earningsQuarterlyGrowth`: 분기당 순이익 성장률
- `netIncomeToCommon`: 순이익
- `lastDividendValue`, `lastDividendDate`: 최근 배당액 및 지급일
- 배당 관련 지표가 부족할 경우 "배당 비중 낮음" 또는 "무배당주로 분류"라고 명확히 기술

---

### 5. 업계 비교 및 평가
- 밸류에이션, 수익성, 변동성 등을 업계 평균과 비교
- 특히 `forwardPE`, `EV/EBITDA`, `beta` 지표를 중심으로 경쟁사 대비 상대적 위치 분석

---

### 6. 투자 매력도 종합 평가
- 현재 주가가 고평가/저평가/적정가로 판단되는 근거 설명
- 실적 성장성, 밸류에이션, 변동성, 공매도 정보 등을 종합적으로 고려
- 투자자에게 제공할 수 있는 인사이트 및 주의사항 정리

---

> 분석은 단순 수치 나열이 아닌, 각 지표가 기업의 투자 매력도와 시장 평가에 어떤 영향을 주는지를 중심으로 통찰력 있게 작성해주세요.

""",
        
        "price": """
다음은 특정 기업의 현재 주가 및 거래 정보에 대한 JSON 데이터입니다. 이 데이터를 기반으로 **정량적이고 분석적인 마크다운 주가 리포트**를 작성해주세요.

## 작성 규칙 및 스타일

- **문체**: "~임", "~함" 형태의 간결한 단문 서술체
- **형식**: Markdown으로 작성하고, 각 항목을 제목/소제목으로 구조화
- **분석 방향**: 단기 및 장기 투자자 모두를 위한 인사이트를 제공하고, 지표의 의미와 함의를 해석할 것

---

## 필수 분석 항목

### 1. 현재 주가 및 변동률
- `regularMarketPrice`: 정규장 마감 주가
- `regularMarketChange`: 전일 대비 절대 변화량
- `regularMarketChangePercent`: 전일 대비 변동률
- `preMarketPrice`, `preMarketChange`, `preMarketChangePercent`: 프리마켓 정보
- `postMarketPrice`, `postMarketChange`, `postMarketChangePercent`: 애프터마켓 정보

→ 전일 대비 주가 흐름을 분석하고, 프리/애프터 마켓에서의 흐름도 포함하여 시장의 단기 반응 해석

---

### 2. 거래 정보
- `regularMarketVolume`: 당일 거래량
- 참고로 평균 거래량은 제공되지 않았으므로 “비교 기준 없음” 명시
- 거래량이 주가 움직임과 어떻게 연관되는지 설명

---

### 3. 주가 범위
- `regularMarketDayHigh`, `regularMarketDayLow`: 당일 고가/저가
- `regularMarketOpen`: 당일 시가
- `regularMarketPreviousClose`: 전일 종가

→ 일중 변동성 분석, 시가 대비 등락폭, 종가 대비 흐름의 의미 해석

---

### 4. 시장 데이터
- `marketCap`: 시가총액
- `exchangeName`, `symbol`, `currency`: 거래소, 종목코드, 통화
- 종목의 규모 및 글로벌 대형주로서의 위상 설명

---

### 5. 모멘텀 분석
- 당일 주가 흐름과 전후장(pre/post) 데이터의 흐름을 종합적으로 해석
- 최근 주가 변화의 방향성과 특징(상승세, 조정, 횡보 등)을 간단히 기술

---

### 6. 기술적 시그널
- 현재 주가(`regularMarketPrice`)가 당일 고가/저가/시가 대비 어느 수준에 위치하는지 설명
- 기술적 관점에서 지지선/저항선 또는 심리적 가격대 분석 시도
- 시장 참여자들의 심리 해석

---

### 7. 투자자 관점 평가
- **단기 투자자**: 일중 변동성, 프리/애프터마켓 변동, 거래량을 기반으로 단기 트레이딩 관점에서 평가
- **장기 투자자**: 시가총액, 전반적 주가 추세, 기업 펀더멘털(타 파일 활용 가능 시)과 연계해 장기 보유 적합성 평가

---

> 결과물은 단순 수치 나열이 아닌, 해당 지표들이 시장 참여자 및 투자자에게 시사하는 바를 해석 중심으로 전달해야 함.

""",
        
        "summary_detail": """
다음은 특정 기업의 요약 주식 정보에 대한 JSON 데이터입니다. 이 데이터를 바탕으로 **투자자에게 유용한 마크다운 분석 리포트**를 작성해주세요.

## 작성 규칙 및 스타일

- **문체**: "~임", "~함" 형태의 간결한 단문 서술체
- **형식**: Markdown 문서 형식으로 작성하고, 각 항목을 소제목으로 명확히 분리
- **분석 수준**: 단순 수치 나열이 아닌, 투자자 관점에서 지표의 의미와 해석을 포함할 것

---

## 반드시 포함해야 할 분석 항목

### 1. 기본 정보
- **종목명**: 
- **티커**: 
- **통화**: `currency` 항목 (예: USD)
- **거래소 정보**가 없을 경우 명시 생략

---

### 2. 주가 정보
- `regularMarketOpen`: 시가
- `regularMarketDayHigh`: 고가
- `regularMarketDayLow`: 저가
- `previousClose` 또는 `regularMarketPreviousClose`: 전일 종가
- `volume`, `regularMarketVolume`: 당일 거래량
- `averageVolume`, `averageVolume10days`: 평균 거래량

→ 주가 흐름과 거래량 패턴 분석 포함

---

### 3. 시장 데이터
- `marketCap`: 시가총액
- `priceToSalesTrailing12Months`: PSR (주가매출비율)
- `currency`: 통화 단위
- `tradeable`: 거래 가능 여부 표시 (`true`/`false` 명시)

---

### 4. 주요 지표
- `trailingPE`: 현재 PER
- `forwardPE`: 예상 PER
- `beta`: 주가 민감도 (시장 변동성)
- `dividendRate`: 연간 배당액
- `dividendYield`: 현재 배당 수익률
- `exDividendDate`: 배당락일
- `payoutRatio`: 배당성향

→ 수익성, 안정성, 배당 매력도 등 다각적으로 평가

---

### 5. 52주 성과
- `fiftyTwoWeekHigh`: 52주 최고가
- `fiftyTwoWeekLow`: 52주 최저가
- `fiftyDayAverage`, `twoHundredDayAverage`: 이동 평균
- `trailingAnnualDividendYield`: 최근 1년 배당수익률
- `trailingAnnualDividendRate`: 최근 1년 배당액

→ 주가의 상대적 위치, 변동성 및 배당 안정성 판단

---

### 6. 종합 평가
- 위 모든 수치를 바탕으로 이 종목이 현재 시점에서 저평가/적정가/고평가 상태인지 종합 분석
- PER, 배당수익률, 시가총액, 거래량 패턴 등을 통합적으로 해석
- 단기 및 장기 투자자에게 각각 어떤 의미가 있는지 정리

---

> 모든 수치는 그 자체로 나열하지 말고, 의미와 맥락을 함께 설명하고 투자 판단에 참고될 수 있도록 통찰력 있게 서술할 것.

""",
        
        "inside_holders": """
        다음은 특정 기업의 내부자 보유 및 거래 활동에 관한 JSON 데이터입니다. 이 데이터를 기반으로 투자자에게 유용한 **마크다운 분석 리포트**를 작성해주세요.

## 작성 규칙 및 스타일

- **문체**: "~임", "~함" 형태의 간결한 단문 중심 서술체
- **형식**: Markdown 문서 형식으로 작성하고, 각 항목을 제목 및 표 형식으로 구조화
- **분석 수준**: 단순 보유 내역 나열이 아닌, 내부자 거래 활동의 투자 의미를 중심으로 해석할 것

---

## 반드시 포함해야 할 분석 항목

### 1. 내부자 개요
- 각 내부자의 `name`, `relation`(예: CEO, Director 등)을 리스트 형태로 요약
- 회사의 의사결정에 영향을 미치는 고위 임원 중심으로 해석

---

### 2. 최신 거래 내역
- `latestTransDate`: 최근 거래일
- `transactionDescription`: 매매 구분 (Sale, Purchase 등)
- 해당 거래가 주가에 미치는 심리적 영향 또는 신호 효과 분석
- 예: "지속적인 매도는 경영진의 주가 고점 판단 가능성을 시사함"

---

### 3. 보유 지분 현황
- `positionSummary`: 직접 보유 주식 수 (있을 경우)
- `positionIndirect`: 간접 보유 주식 수 (신탁, 가족 등 경로)
- `positionSummaryDate`, `positionIndirectDate`: 기준일 포함

→ 표로 정리하여 각 인물의 보유 비중과 형태를 비교, 간접보유가 높은 경우 이해충돌 가능성 등 평가

---

### 4. 이상 거래 패턴 여부
- 거래일 및 거래 성격을 기준으로 이상 거래 패턴이 의심되는 경우 간단히 지적
- 예: "단기간 내 연속 매도", "주가 급등 직후 대량 매도" 등

---

### 5. 투자자 관점 해석
- 내부자 매매 활동이 시장 심리에 미치는 영향 해석
- 매도 비중이 높을 경우 경계 신호로, 매수 비중이 높을 경우 신뢰 신호로 평가
- 장기적 보유 유지 여부에 따라 경영진의 주가 자신감 해석 가능

---

> 모든 수치는 그 자체로 나열하지 말고, 각 거래나 보유 정보가 시장에 어떤 신호를 줄 수 있는지를 중심으로 투자자 관점에서 해석할 것.

        """,
        
        "major_holders": """
        다음은 기업의 주요 지분 보유자(내부자 및 기관 투자자)에 대한 JSON 형식 데이터입니다. 이 데이터를 기반으로 **정리된 마크다운 분석 리포트**를 작성해주세요.

## 작성 규칙 및 스타일

- **문체**: "~임", "~함" 형태의 간결한 단문 중심 서술체
- **형식**: Markdown 문서 형식으로 작성하고, 각 항목을 제목/소제목으로 구조화

## 분석 수준

- 단순 수치 나열이 아닌, 내부자 및 기관 보유 비율이 시사하는 **경영 책임성, 시장 신뢰도, 유통 안정성** 등 투자 관련 의미를 해석적으로 서술할 것
- 내부자와 기관 보유 비중의 **상대적 구조** 및 기업 소유 지형의 **분산도/집중도**에 대한 해석 포함
- **투자자 관점**에서 이 지분 구조가 **장기 안정성, 단기 리스크, 주가 민감도** 등에 미치는 영향을 분석할 것

---

## 포함해야 할 분석 항목

### 1. 기업 식별
- 해당 JSON 데이터에서 기업 식별자(symbol 또는 name)를 활용하여 분석 대상 표시
- Markdown 문서 상단 또는 소제목으로 구분

---

### 2. 내부자 보유 지분
- `insidersPercentHeld`: 내부자 보유 비율
- 보유율이 높은 경우: 경영진의 장기적 이해관계 및 책임 경영 신호로 해석
- 보유율이 낮은 경우: 경영진의 주가 연동 동기 약화 가능성 또는 유통성 확보 목적 가능성 제시

---

### 3. 기관 보유 지분
- `institutionsPercentHeld`: 전체 주식 대비 기관 보유 비율
- `institutionsFloatPercentHeld`: 유통 주식 대비 기관 보유 비율
- `institutionsCount`: 참여 기관 수

→ 기관 참여 수준이 높은 경우, 해당 종목의 시장 신뢰도와 정보 투명성 수준이 높다고 판단 가능

---

### 4. 구조 비교 및 해석
- 내부자 vs 기관의 보유 비중을 비교하여 소유 집중도 해석
- 기관 수가 많고 분산되어 있는 경우: 안정적 유통 기반
- 한쪽 비중이 지나치게 낮거나 높은 경우 발생할 수 있는 투자 리스크 설명

---

### 5. 투자자 관점 평가
- 현재 보유 구조가 투자자에게 주는 시사점 요약
- 예: "기관의 대규모 참여는 장기 투자자 유입 가능성을 높이며, 단기적 주가 변동성은 낮을 수 있음"
- 반면, 내부자 보유 비율이 지나치게 낮을 경우, 주가 하락 시 리더십 책임 회피 우려 발생 가능

---

> 각 수치는 반드시 투자자 관점의 해석과 함께 설명할 것. 단순 숫자 나열이 아닌, 보유 구조가 기업 가치, 신뢰도, 안정성에 어떤 영향을 미치는지를 통찰력 있게 기술해야 함.

        """,
        
        "market_summary": """
        다음은 다양한 시장 자산(지수, 선물, 원자재, 암호화폐, 통화 등)의 요약 데이터를 담은 JSON 형식입니다. 이 데이터를 기반으로 투자자에게 유용한 **마크다운 분석 리포트**를 작성해주세요.

## 작성 규칙 및 스타일

- **문체**: "~임", "~함" 형태의 간결한 단문 서술체
- **형식**: Markdown 문서 형식. 각 자산 유형을 구분하여 정리하고, 표 또는 리스트 형태로 시각적으로 구조화할 것

## 분석 수준

- 단순 수치 나열이 아닌, 자산별 **가격 흐름, 변동성, 시장 심리, 기술적 시사점** 등을 함께 해석할 것
- 특히 상승/하락률이 두드러진 항목은 강조하여 투자자 주의 또는 기회를 제시할 것
- 각 자산군(예: 지수 vs 원자재 vs 통화 vs 암호화폐 등)별로 **시장 환경에 따른 반응 차이**를 요약할 것
- 전체적으로 **시장 모멘텀과 리스크 온/오프 분위기**도 해석할 것

---

## 포함해야 할 분석 항목

### 1. 지수 및 선물 (quoteType = "INDEX" 또는 "FUTURE")
- `shortName`, `symbol`, `regularMarketPrice.fmt`: 현재 가격
- `regularMarketChange.fmt`, `regularMarketChangePercent.fmt`: 절대/상대 등락폭
- `regularMarketPreviousClose.fmt`: 전일 종가
- `exchange`, `region`, `exchangeTimezoneShortName` 등 시간대 참고

→ 시장 흐름의 주요 방향성을 파악하고, 상승 또는 하락이 글로벌 경제 심리에 미치는 영향을 요약할 것

---

### 2. 원자재 (예: Crude Oil, Gold, Silver 등)
- `shortName`, `regularMarketPrice`, `regularMarketChangePercent`
- 가격 등락과 함께, 해당 자산이 **인플레이션, 경기 전망, 지정학적 리스크**에 어떻게 반응하는지 해석할 것

---

### 3. 통화쌍 (quoteType = "CURRENCY")
- 예: EUR/USD, GBP/USD, USD/JPY 등
- `regularMarketPrice`, `regularMarketChangePercent`, `currency`
- 강세/약세 분석과 더불어 달러 인덱스 변동과의 연관성 해석
- 시장 위험 선호도와 외환 움직임 간 상관관계 설명 가능

---

### 4. 암호화폐 (quoteType = "CRYPTOCURRENCY")
- `shortName`, `regularMarketPrice`, `regularMarketChangePercent`
- 주요 암호자산(BTC, ETH, XRP 등)의 변동성 설명
- 전통시장과 디커플링 여부 또는 기술주와의 상관 해석 포함 가능

---

### 5. 금리 및 공포지수 (예: ^TNX, ^VIX)
- `shortName`, `regularMarketPrice`, `regularMarketChangePercent`
- 10년물 금리 변화는 인플레이션 및 연준 기대 반영
- VIX 변동은 시장 리스크 심리 반영 → 상승 시 리스크 회피 선호

---

### 6. 종합 시황 정리
- 자산별 흐름을 통합하여 시장의 전반적 온도(리스크온/오프)를 판단
- 예: 주가지수 상승 + 원자재 하락 + 달러 강세 = 안정적 경기 낙관
- 반대로 VIX 상승 + 금 상승 + 나스닥 약세 = 변동성 확대 및 리스크 회피 심리 반영

---

> 모든 수치는 반드시 해석과 함께 제공하며, 자산간 상호작용 및 매크로 흐름을 중심으로 투자자가 이해할 수 있도록 작성할 것.

        """,
        
        #option chain은 아무것도 출력 안 되는 중, 그냥 빈칸으로 넘기자.
        
        "quotes": """
        다음은 개별 종목의 종합 시세 데이터(JSON 형식)입니다. 이 데이터를 바탕으로 투자자에게 유용한 **마크다운 형식의 분석 리포트**를 작성해주세요.

## 작성 규칙 및 스타일

- **문체**: "~임", "~함" 형태의 간결한 단문 서술체
- **형식**: Markdown 문서로 작성하고, 각 항목을 소제목으로 구분할 것

## 분석 수준

- 단순한 숫자 나열이 아닌, **각 수치가 시사하는 의미**를 투자자 관점에서 해석할 것
- 밸류에이션, 배당, 변동성, 거래량 등 지표들이 **기업의 시장 평가와 투자 매력도에 어떤 영향을 주는지** 분석할 것
- **단기 기술적 흐름**과 **장기 펀더멘털 관점**을 함께 반영한 균형 잡힌 분석 구성

---

## 포함해야 할 분석 항목

### 1. 기본 정보
- `quoteType`, `typeDisp`: 자산 종류 확인
- `exchange`, `fullExchangeName`: 거래소 정보
- `currency`: 통화 단위
- `region`, `marketState`, `tradeable`, `cryptoTradeable`: 거래 환경 요약

---

### 2. 시세 및 거래 정보
- `regularMarketPrice`, `regularMarketChange`, `regularMarketChangePercent`: 현재가 및 변동폭
- `regularMarketOpen`, `regularMarketDayHigh`, `regularMarketDayLow`, `regularMarketPreviousClose`: 일중 주가 범위
- `regularMarketVolume`, `averageDailyVolume3Month`, `averageDailyVolume10Day`: 거래량과 평균 거래량 비교

→ 거래량 대비 등락폭을 해석하여 단기 수급 흐름 분석

---

### 3. 밸류에이션 지표
- `trailingPE`, `forwardPE`, `priceEpsCurrentYear`: PER 분석
- `priceToBook`, `bookValue`: PBR 및 장부가 대비 분석
- `marketCap`: 시가총액

→ 해당 종목이 성장주, 가치주, 대형주 중 어디에 속하는지 평가

---

### 4. 배당 및 수익성
- `dividendRate`, `dividendYield`, `trailingAnnualDividendRate`, `trailingAnnualDividendYield`
- `payoutRatio` (있을 경우)
- `corporateActions` 내 배당 공지사항 내용 포함

→ 배당 정책의 변화, 수익 환원 성향, 안정성 평가

---

### 5. 실적 및 EPS 정보
- `epsTrailingTwelveMonths`, `epsForward`, `epsCurrentYear`: EPS 추이
- `earningsTimestamp`, `earningsCallTimestampStart`: 실적 발표일 정보
- `isEarningsDateEstimate`: 예측 여부 명시

→ 실적 시즌 전후 전략적 대응 시사점 제공

---

### 6. 기술적 위치
- `fiftyTwoWeekRange`, `fiftyTwoWeekHigh`, `fiftyTwoWeekLow`
- `fiftyTwoWeekChangePercent`, `fiftyDayAverage`, `twoHundredDayAverage`: 현재 주가의 상대적 위치 분석
- `fiftyDayAverageChangePercent`, `twoHundredDayAverageChangePercent`: 기술적 트렌드 방향 해석

---

### 7. 종합 평가
- 밸류에이션, 거래 흐름, 배당, 기술적 위치, 실적 등을 통합하여 투자 매력도 평가
- 예: "주가는 52주 고점 대비 18% 낮으며, 거래량은 평균보다 감소세를 보임. 이는 실적 발표를 앞둔 관망 심리를 시사함"
- 단기 및 장기 투자자 모두에게 유의미한 시사점 제공

---

> 각 수치는 반드시 해석을 동반할 것. 기업명은 언급하지 않되, 해당 데이터가 의미하는 바를 투자자 관점에서 전략적으로 설명할 것.

        """,
        
        "technical_insights": """
        다음은 특정 종목의 기술적 분석, 섹터 비교, 밸류에이션, 추천 의견 등 종합 분석 데이터를 포함한 JSON입니다. 이 데이터를 바탕으로 투자자에게 유용한 **마크다운 분석 리포트**를 작성해주세요.

## 작성 규칙 및 스타일

- **문체**: "~임", "~함" 형태의 간결한 단문 서술체
- **형식**: Markdown 형식으로 작성하고, 각 항목을 소제목으로 명확히 구분

## 분석 수준

- 각 수치나 방향성을 단순 나열하지 말고, **기술적 흐름, 섹터 대비 경쟁력, 투자 매력도** 등 투자자 관점에서 통찰력 있게 해석할 것
- **단기, 중기, 장기 시계열별로 기술적 방향성과 근거를 구분하여** 평가할 것
- 뉴스, 타겟 프라이스, 섹터 평균 대비 비교 요소를 활용해 **심층적 투자 판단 재료 제공**

---

## 포함해야 할 분석 항목

### 1. 기술적 분석 요약
- `technicalEvents` 내 각 기간별 기술적 방향성과 근거 분석:
  - `shortTermOutlook`, `intermediateTermOutlook`, `longTermOutlook`
  - 각각의 `direction`, `scoreDescription`, `stateDescription`
  - 섹터 및 지수와의 방향성/스코어 비교 (`sectorDirection`, `sectorScoreDescription`, `indexDirection`, `indexScoreDescription`)

→ 단기/중기/장기별 흐름 요약과 그 의미 해석. 기술적 관점에서의 진입/관망/이탈 시점 시사

---

### 2. 주요 기술 지표
- `support`, `resistance`, `stopLoss`: 기술적 지지/저항/손절선
→ 현재 주가가 어느 구간에 위치하는지 설명하고, 트레이딩 관점에서 대응 전략 제안 가능

---

### 3. 밸류에이션 분석
- `valuation.description`, `valuation.discount`: 현재 가치 대비 평가
→ "Fair Value", "Undervalued" 등 해석 중심 + 몇 % 할인 상태인지 명시

---

### 4. 종합 평가 점수 비교
- `companySnapshot.company` vs `companySnapshot.sector`: 아래 항목들의 수치 비교
  - `innovativeness`: 혁신성
  - `hiring`: 고용지표
  - `sustainability`: 지속가능성
  - `insiderSentiments`: 내부자 심리
  - `earningsReports`: 실적 일관성
  - `dividends`: 배당 성향

→ 섹터 평균 대비 경쟁력 요약. 해당 종목이 속한 산업 내 상대적 위치 분석

---

### 5. 애널리스트 추천 및 목표가
- `recommendation.rating`, `recommendation.targetPrice`, `recommendation.provider`
→ "BUY", "HOLD" 등의 의견과 목표주가 제시 해석. 현재 주가 대비 괴리율 설명 가능

---

### 6. 주요 뉴스 이벤트
- `sigDevs` 리스트
→ 최신 이슈 또는 발표 내용 간단 요약. 기술적 해석과 연결되면 강조할 것

---

### 7. 종합 투자 판단
- 기술적 흐름, 펀더멘털 지표, 경쟁력 비교, 외부 이벤트 등을 종합하여 단기 및 중기 투자자에게 의미 있는 시사점 도출
- 예: "단기 강세 추세이며, 기술적으로는 지지선 위에서 유지 중. 밸류에이션은 적정 수준이나 장기 추세는 약세. 기술적 반등 구간이나 실적 개선 필요."

---

> 수치는 반드시 해석을 동반하여 제공하고, 각 분석이 **투자 판단에 어떤 시사점을 주는지**를 중심으로 작성할 것.

        """
    }
    
    default_prompt = f"""
다음은 {file_name} 관련 주식 데이터입니다. 이 데이터를 분석하여 마크다운 형식으로 투자자에게 유용한 형태로 요약해주세요.

## 요구사항:
1. 데이터의 주요 특징과 핵심 지표들을 정리
2. 투자 관점에서의 의미와 해석 제공
3. 주목할 만한 포인트나 위험 요소 언급
4. 마크다운 형식으로 구조화하여 가독성 확보

투자 의사결정에 도움이 되는 인사이트를 제공해주세요.
"""
    
    base_prompt = prompts.get(file_name, default_prompt)
    
    return f"""{base_prompt}

## 데이터:
```json
{json.dumps(data, ensure_ascii=False, indent=2)}
```

위 데이터를 분석하여 마크다운 형식으로 작성해주세요. 제목은 "# {file_name.upper()} 분석 리포트"로 시작하고, 각 섹션을 명확히 구분해주세요."""


def create_timeseries_prompt(file_name: str, data: Any) -> str:
    """시계열 데이터에 대한 프롬프트 생성"""
    
    prompts = {
        "history_long_term": """
다음은 특정 종목의 장기 주가 이력 데이터입니다. 이 데이터를 기반으로 다음 요구사항에 맞춰 **마크다운 형식의 심층 분석 보고서**를 작성해주세요.

## 작성 스타일
- **문체**: "~임", "~함" 형태의 간결한 서술체
- **형식**: Markdown 형식 사용

---

## 분석 수준

- **수치의 단순 나열이 아니라**, 시계열 흐름의 변화 해석 중심
- 저점과 고점, 거래량, 변동성 변화 등 **추세 전환의 시사점 강조**
- 투자자에게 의미 있는 **진입/관망/이탈 시점**, **리스크 요인**, **지속적 상승 혹은 반락 우려** 등 포함
- 중장기 관점의 **전략적 판단 근거**를 제공

---

## 포함해야 할 항목

### 1. 주가 추이 요약
- 시계열 데이터에서 `adjclose` 기준으로 **전반적인 추세** 분석
  - 상승기, 하락기, 박스권 구간 식별
  - 최고점/최저점 대비 변동폭
  - 주요 변곡점 및 추세 전환 시점 해석

---

### 2. 거래량 기반 수급 해석
- `volume` 수치의 증가/감소 패턴과 주가의 상관 관계
- **거래량 급증 시점**과 **가격 반전 또는 돌파 구간** 포착
- 수급 동향을 통한 매집/분산 가능성 평가

---

### 3. 변동성 및 리스크 요인
- 고점과 저점의 차이(`high`, `low`)를 기반으로 **월별 혹은 분기별 변동성** 분석
- 변동폭 확장 구간과 그 의미 해석
- 투자자 입장에서의 리스크 구간 명시

---

### 4. 배당 및 분할 이벤트
- `dividends`, `splits` 항목의 등장 시점과 주가 반응 요약
- 이벤트 발생 전후 수익률 비교 가능 시 포함
- **장기 보유자의 수익성 변화**에 대한 통찰 제공

---

### 5. 기술적 구간 해석
- `support`, `resistance` 개념을 활용한 **과거 지지/저항 범위 식별**
- 최근 주가가 역사적 레벨 대비 어느 위치에 있는지 분석
- 이를 바탕으로 **향후 상방/하방 가능성 및 전략 제안**

---

### 6. 종합 투자 시사점
- 위 분석을 기반으로 **중장기 보유 전략이 유효한지** 평가
- 추세 강화 여부, 고점 돌파 여력, 리스크 분산 전략 제안
- “최근 상승은 거래량 동반 상승으로 신뢰도 높음. 분할 매수 고려 가능” 등 구체적 투자 제안 포함

---

> 모든 수치는 반드시 **의미 해석을 동반하여** 설명하고, **전략적 시사점** 중심으로 요약할 것.

""",
        
        "history_middle_term": """
        다음은 특정 종목의 중기 주가 시계열 데이터를 담은 JSON입니다. 이 데이터를 기반으로 투자자에게 유익한 **마크다운 분석 리포트**를 작성해주세요.

## 작성 스타일
- **문체**: "~임", "~함" 형태의 간결한 서술체
- **형식**: Markdown 문서 형식

## 분석 수준

- 단순한 숫자 나열이 아니라 **기간별 흐름**, **변동성**, **추세 전환**, **거래량 연동 패턴** 등을 중심으로 해석할 것
- **최근 몇 주~수개월간의 흐름**을 중심으로 단기 대응 전략 또는 추세 지속 가능성 평가 포함
- 기술적 분석 관점에서 **박스권, 돌파, 조정, 반등 신호** 등을 찾아내어 시사점 제시

---

## 포함해야 할 분석 항목

### 1. 주가 추이 요약
- `adjclose` 기준으로 **중기 흐름 분석**
  - 저점 대비 회복율
  - 고점 대비 조정폭
  - **추세선** 또는 **변곡점** 추정 가능 시 서술
  - 전형적인 패턴(예: 깃발형, 쐐기형, 삼각 수렴 등)에 근거한 시사점

---

### 2. 거래량 동향
- `volume` 항목을 기준으로 **가격과 거래량의 상관관계 해석**
  - **상승 동반 거래량 증가**: 신뢰도 높은 추세
  - **하락 동반 거래량 증가**: 매도 압력 확산 가능성
  - **박스권 내 거래량 감소**: 방향성 탐색기

---

### 3. 변동성 및 위험 인식
- `high`, `low`, `close` 값을 바탕으로 각 기간의 **변동폭 계산**
- **변동성이 확대되는 구간과 축소되는 구간**의 시장 심리 해석
- 투자자 입장에서 **위험 회피 vs 기회 포착** 구간 구분

---

### 4. 기술적 위치 해석
- 고점과 저점 기준으로 현재 주가의 상대적 위치 분석
- `adjclose`가 역사적 평균 또는 중심가격대(이동평균선 근사)에 비해 높은지 낮은지 평가
- **지지선/저항선 인근 움직임**, **갭 발생 여부** 등 기술적 시그널 강조

---

### 5. 단기 전략 및 시사점
- 최근 흐름 기반으로 **매수/관망/이탈 전략** 제안
- **단기 상승 지속 예상 vs 과매수/반락 우려** 중 어떤 시사점이 강한지 요약
- 매수세/매도세 주도 구간 예측
- 예: “최근 2주간 저점 상승 지속. 거래량도 증가하며 추세 강화 중. 단기적 눌림목 공략 가능성 있음.”

---

> 모든 수치는 해석을 동반해 서술할 것. 시간 흐름에 따른 분석이 핵심이며, 단기 트레이딩 관점과 중기 포지셔닝 전략을 연결지어 서술할 것.

        """,
        
        "history_short_term": """
        다음은 특정 종목의 단기 주가 시계열 데이터를 담은 JSON입니다. 이 데이터를 기반으로 투자자에게 유용한 **마크다운 형식의 분석 보고서**를 작성해주세요.

## 작성 스타일
- **문체**: "~임", "~함" 형태의 간결한 서술체
- **형식**: Markdown 문서 형식
- 데이터 흐름에 대한 통찰과 전략 제안을 포함할 것

## 분석 수준

- 단순한 시세 나열이 아닌, **최근 흐름 속 추세, 변동성, 수급 강도, 반등 또는 이탈 시그널** 등 실전적인 기술적 해석 중심
- **3일~2주 이내의 가격 변동과 거래량 흐름**을 기준으로 단기 대응 전략 도출
- 변동성 확대 구간, 저점 지지/고점 저항 구간 식별

---

## 포함해야 할 분석 항목

### 1. 가격 흐름 요약
- `adjclose` 중심으로 **최근 종가 흐름을 요약**
  - 최고점, 최저점, 현재가의 상대 위치
  - 최근 상승/하락률, 연속 음봉/양봉 등 추이
  - **단기 추세선** (5~10일 기준)과의 괴리 해석

---

### 2. 거래량 분석
- `volume` 수치를 기준으로 **가격과 수급의 일치 여부** 해석
  - 상승 시 거래량 증가 여부 → 강세 신뢰도
  - 하락에도 거래량 적으면 조정 국면일 수 있음
  - 급등락일의 수급 특이성 포착

---

### 3. 일중 변동성 해석
- `high`, `low`, `close` 기준으로 일별 변동폭 계산
- **갭 발생 여부**, 일중 V자 반등, 음봉 반전 등 특징 포착
- 변동성이 **확장 중인지 축소 중인지** 기술적으로 판단

---

### 4. 기술적 위치
- `adjclose`가 단기 고점 대비 몇 % 하락/상승했는지 계산
- **지지선/저항선 구간**에 근접한 경우 이를 강조
- 단기 이동평균과의 이격도 언급 가능

---

### 5. 전략적 시사점
- 현재 흐름이 **관망, 매수 진입, 단기 차익 실현 구간** 중 어느 쪽인지 제시
- 예: "단기 저점이 높아지고 있으나 거래량 미동반. 추세 전환 가능성은 제한적임."
- 기술적 반등이 기대되는 구간이면 근거와 함께 서술

---

> 모든 수치는 반드시 해석과 함께 제공할 것. 단기 시세 흐름이 투자자에게 시사하는 리스크와 기회를 중심으로 기술적 해석을 제시할 것.

        """,
        
        "income_statement_quarter": """
다음은 기업의 분기별 손익계산서 시계열 데이터를 담은 JSON입니다. 이 데이터를 기반으로 투자자에게 유용한 **마크다운 형식의 분석 리포트**를 작성해주세요.

## 작성 스타일
- **문체**: "~임", "~함" 형태의 간결한 서술체 사용
- **형식**: 마크다운 문서 형식으로 각 항목을 소제목(`##`, `###`)으로 구분
- 수치는 반드시 **의미 해석과 함께 서술**
- 전년 동기 및 직전 분기와의 비교를 통해 **시계열 흐름 분석 중심으로 작성**

---

## 분석 수준
- 단순 요약이 아닌, **기간별 변화**, **수익성 구조 변화**, **비용 구조 해석**, **이익률 추이** 등을 종합적으로 해석할 것
- 최근 분기의 실적 변화에 대한 **전략적 시사점** 포함

---

## 포함해야 할 분석 항목

### 1. 핵심 수익성 지표 추이
- 매출: `OperatingRevenue`, `TotalRevenue`
- 영업이익: `OperatingIncome`
- 순이익: `NetIncome`, `NetIncomeCommonStockholders`
- 주당순이익: `BasicEPS`, `DilutedEPS`

→ 각 항목의 분기별 추세 및 변곡점 요약

---

### 2. 비용 및 투자 항목 분석
- 매출원가: `CostOfRevenue`
- 영업비용: `OperatingExpense`
- R&D: `ResearchAndDevelopment`
- 판관비: `SellingGeneralAndAdministration`, `MarketingExpense`

→ 고정비/변동비 구조 변화, R&D 투자 방향 등 설명

---

### 3. 이익률 및 비율 분석
- 매출총이익률 = `(TotalRevenue - CostOfRevenue) / TotalRevenue`
- 영업이익률 = `OperatingIncome / TotalRevenue`
- 순이익률 = `NetIncome / TotalRevenue`
- R&D 비중 = `ResearchAndDevelopment / TotalRevenue`

→ 수익성 개선/악화의 원인 진단

---

### 4. 일회성 및 기타 항목
- `OtherIncomeExpense`, `GainOnSale`, `UnusualItems` 등
→ 일회성 수익/비용 여부와 영향 평가

---

### 5. 시계열 성과 해석
- 전년 동기 및 직전 분기 대비 **매출, 이익, EPS 증감률**
- EPS 및 이익률 흐름 중심으로 **분기별 추세 정리**
- 고점/저점 분기 및 변곡점 강조

---

### 6. 종합 평가 및 투자 시사점
- 전반적인 수익성 흐름에 대한 요약
- 비용 통제력, 성장성, 이익의 질 측면에서의 해석
- 향후 실적 전망 및 단기 투자 판단 시사점

---

> 모든 수치는 반드시 해석과 함께 제공할 것. 투자자에게 의미 있는 흐름, 위험 요인, 개선 요인을 중심으로 작성할 것.

""",
        
        "income_statement_yearly": """
        다음은 기업의 연간 손익계산서 시계열 데이터를 담은 JSON입니다. 이 데이터를 기반으로 투자자 관점에서 의미 있는 **마크다운 형식의 재무 분석 보고서**를 작성해주세요.

## 작성 스타일
- **문체**: "~임", "~함" 형태의 간결하고 전문적인 서술체 사용
- **형식**: 마크다운 문서 형식 (제목, 소제목, 표 포함 가능)
- **해석 중심**: 수치는 반드시 해석과 함께 제공
- **흐름, 비교, 구조 분석** 중심으로 서술

---

## 요구 항목

### 1. 기본 정보
- **분석 대상 연도 범위** 명시
- **사용된 통화 단위** 표기
- 전체 기간 동안의 **재무 성과 개요**

---

### 2. 매출 및 수익성 분석
- 주요 항목:
  - `TotalRevenue`
  - `OperatingIncome`
  - `NetIncome`
  - `EBIT`
  - `EBITDA`
  - `GrossProfit`
- 연도별 수치 및 **전년 대비 증감률(%)**
- 마진 계산:
  - **영업이익률 = OperatingIncome / TotalRevenue**
  - **순이익률 = NetIncome / TotalRevenue**
  - **EBITDA 마진 = EBITDA / TotalRevenue**
- **수익성 구조의 추이와 해석** 포함

---

### 3. 비용 구조 분석
- 주요 항목:
  - `CostOfRevenue`
  - `ResearchAndDevelopment`
  - `SellingAndMarketingExpense`
  - `GeneralAndAdministrativeExpense`
- **총수익 대비 비중**, 연도별 **증감률 분석**
- **고정비/변동비 성격** 및 변화 가능성 평가
- **R&D 투자 증가 여부**와 그 의미 해석

---

### 4. EPS 및 주당 지표
- 주요 항목:
  - `BasicEPS`
  - `DilutedEPS`
  - `DilutedAverageShares`
  - `WeightedAverageSharesOutstanding`
- EPS 추이와 **순이익 흐름 간 연동성** 분석
- **발행주식 수 변화**가 미치는 영향 평가
- **주당 수익 흐름을 통한 투자 가치 평가**

---

### 5. 세전/세후 손익 및 비경상 항목
- 주요 항목:
  - `PretaxIncome`
  - `TaxProvision`
  - `IncomeTaxExpense`
  - `TotalUnusualItems`
  - `OtherIncomeExpense`
- **실질 세율 = TaxProvision / PretaxIncome** 추이 분석
- **일회성 항목과 지속 가능한 실적 분리**
- **순이익 왜곡 요인 여부 평가**

---

### 6. 시계열 흐름 요약
- 각 핵심 지표의 **연도별 변화 요약**
- **변곡점, 추세 반전, 정체 구간** 등 시계열 해석
- **정성적 분석 + 수치 요약 병행**

---

### 7. 종합 평가 및 투자 시사점
- **수익성, 효율성, 성장성, 안정성** 측면에서 종합 평가
- **이익의 질(Quality of Earnings)** 분석
- **향후 실적 전망 및 투자 전략적 시사점** 제시

---

## 분석 수준
- 단순 수치 나열이 아닌, **연도 간 흐름과 변화 중심 분석**
- 각 지표 간의 **구조적 상호작용과 인과관계 해석**
- 투자자가 이해할 수 있는 **논리적 설명과 요약** 포함

        """,
        
        "balance_sheet_quarter": """
다음은 기업의 분기별 대차대조표(balance sheet) 시계열 데이터를 담은 JSON입니다. 이 데이터를 기반으로 투자자 관점에서 의미 있는 **마크다운 형식의 분석 보고서**를 작성해주세요.

## 작성 스타일
- **문체**: "~임", "~함" 형태의 간결하고 전문적인 서술체 사용
- **형식**: 마크다운 문서 형식 (제목, 소제목, 표 포함 가능)
- **핵심 수치에는 반드시 해석**을 포함할 것
- **단순 수치 나열이 아닌 흐름과 구조 해석 중심**

---

## 요구 항목

### 1. 기본 정보
- **데이터 기준 분기 범위** 명시
- **통화 단위** 표기
- **총 자산, 총 부채, 자기자본** 등의 개괄적 흐름 요약

---

### 2. 유동성 분석
- 항목:
  - `CurrentAssets`
  - `CurrentLiabilities`
  - `WorkingCapital`
  - `CashAndCashEquivalents`
  - `AccountsReceivable`
  - `Inventory`
- **유동비율 = CurrentAssets / CurrentLiabilities**
- **당좌비율 = (CurrentAssets - Inventory) / CurrentLiabilities**
- 분기별 변화와 **단기지급능력 평가**

---

### 3. 자산 구조 분석
- 항목:
  - `CashCashEquivalentsAndShortTermInvestments`
  - `NetPPE`, `GrossPPE`
  - `ConstructionInProgress`, `LandAndImprovements`
  - `GoodwillAndOtherIntangibleAssets`
  - `AvailableForSaleSecurities`, `InvestmentinFinancialAssets`
- **유형자산 비중** 및 **무형자산의 적정성** 분석
- **투자자산 증가 흐름 및 전략적 의도 해석**

---

### 4. 부채 구조 분석
- 항목:
  - `AccountsPayable`, `Payables`
  - `CurrentDebt`, `LongTermDebt`
  - `CapitalLeaseObligations`, `OtherCurrentLiabilities`
  - `DeferredRevenue`, `DeferredLiabilities`
- **부채 만기 분포**와 **비유동/유동 비율** 비교
- **리스크 지표: 유동부채 급증 여부, 부채 의존도**

---

### 5. 자본 및 자기자본 분석
- 항목:
  - `CommonStockEquity`
  - `RetainedEarnings`
  - `TangibleBookValue`, `StockholdersEquity`
  - `OrdinarySharesNumber`, `ShareIssued`
- **이익잉여금의 누적 추이**
- **자기자본 증가율**, **주식발행량 변화**, **자본 구조 안정성 평가**

---

### 6. 시계열 흐름 요약
- **핵심 지표들의 분기별 변동 요약**
- **추세, 급등락, 계절성 등 패턴 분석**
- 숫자 해석과 함께 **정성적 요약** 제공

---

### 7. 종합 평가 및 투자 시사점
- **재무 안정성, 자산 유연성, 단기 지급능력** 관점에서 종합 평가
- 부채구조 변화가 **기업 전략이나 시장 대응**과 어떻게 연관되는지 해석
- **향후 자산/부채/자본 방향성**에 대한 투자 시사점 도출

---

## 분석 수준
- 분기 간 흐름 중심의 **시계열 분석**
- 각 항목 간의 구조적 관계에 대한 **심층 해석**
- 수치 해석과 **투자자 관점의 종합 요약** 포함

        """,
        
        "balance_sheet_yearly": """
        다음은 기업의 연간 대차대조표 시계열 데이터(JSON)입니다. 이 데이터를 분석하여 **마크다운 형식의 재무 리포트**를 작성해주세요.

## 작성 스타일
- 문체: "~임", "~함"의 **간결한 서술체** 사용
- 형식: **마크다운 문서 형식** (제목, 소제목, 표 포함 가능)
- **강조가 필요한 수치, 시사점은 마크다운 강조 문법 사용** (**굵게**)
- **수치 나열보다는 해석 중심**으로 작성
- **시계열 흐름** 및 **재무 구조 변화**에 대한 설명 필수

---

## 요구 항목

### 1. 기본 정보
- **데이터 연도 범위** 및 **통화 단위** 명시
- 총자산, 총부채, 자기자본 등 **요약 흐름 및 주요 구조 변화** 간략 설명

---

### 2. 유동성 분석
- 항목: `CurrentAssets`, `CurrentLiabilities`, `WorkingCapital`, `CashAndCashEquivalents`, `Inventory`, `AccountsReceivable`
- **유동비율 = CurrentAssets / CurrentLiabilities**
- **당좌비율 = (CurrentAssets - Inventory) / CurrentLiabilities**
- **분기 간 흐름 및 단기 지급 능력 변화** 해석

---

### 3. 자산 구조 분석
- 항목: `TotalAssets`, `CashCashEquivalentsAndShortTermInvestments`, `NetPPE`, `GrossPPE`, `GoodwillAndOtherIntangibleAssets`, `AvailableForSaleSecurities`, `OtherNonCurrentAssets`
- **유형자산 비중**, **무형자산 비율**, **투자성 자산의 증가/감소 흐름** 분석
- **총자산 대비 주요 항목의 비중 변화 해석**

---

### 4. 부채 구조 분석
- 항목: `AccountsPayable`, `LongTermDebt`, `CapitalLeaseObligations`, `CurrentDebtAndCapitalLeaseObligation`, `TotalLiabilitiesNetMinorityInterest`, `OtherCurrentLiabilities`, `DeferredRevenue`, `DeferredTaxesLiabilities`
- **유동 vs 비유동 부채 비중**
- **부채 구조 변화에 따른 리스크 변화** 평가
- **부채 상환 능력** 및 자본 대비 레버리지 분석

---

### 5. 자본 및 자기자본 분석
- 항목: `CommonStockEquity`, `RetainedEarnings`, `TangibleBookValue`, `ShareIssued`, `OtherEquityAdjustments`
- **이익잉여금 누적**, **자본금 변화**, **자기자본 증가율** 분석
- **주식 발행량의 변화**가 자본구조에 미치는 영향 평가

---

### 6. 시계열 흐름 요약
- 연도별 핵심 지표(자산, 부채, 자본, 유동성) **표나 리스트로 정리**
- **트렌드 분석**: 급증/급감, 정체기, 구조적 전환 포인트 식별
- 단순 수치 비교를 넘어선 **패턴 해석 중심 설명**

---

### 7. 종합 평가 및 투자 시사점
- 유동성, 부채 안정성, 자산 효율성, 자기자본 증가 측면에서 종합 평가
- **이 기업의 재무 구조가 장기적으로 투자에 얼마나 매력적인지 해석**
- **재무 안정성과 성장 전략 간의 관계** 분석

---

## 분석 수준
- 연도 간 흐름을 중심으로 한 **시계열 기반 구조 분석**
- 주요 항목 간 상호 관계 및 변동 요인에 대한 **정성적 해석 강조**
- **투자자 관점**에서 유의미한 정보 도출

        """,
        
        "cash_flow_quarter": """
        다음은 기업의 **분기별 현금흐름표 시계열 데이터(JSON)**입니다. 이 데이터를 분석하여 **마크다운 형식의 재무 리포트**를 작성해주세요.

## 작성 스타일
- 문체: "~임", "~함"의 **간결한 서술체** 사용
- 형식: **마크다운 문서 형식** (제목, 소제목, 표 포함 가능)
- **강조가 필요한 수치, 시사점은 마크다운 강조 문법 사용** (**굵게**)
- **수치 나열보다는 해석 중심**으로 작성
- **시계열 흐름** 및 **재무 구조 변화**에 대한 설명 필수

---

## 요구 항목

### 1. 기본 정보
- **데이터 분기 범위** 및 **통화 단위** 명시
- 주요 항목(`OperatingCashFlow`, `InvestingCashFlow`, `FinancingCashFlow`, `NetIncome`, `FreeCashFlow`) 중심으로 **전체 흐름 개괄**

---

### 2. 영업활동 현금흐름 분석
- 항목: `OperatingCashFlow`, `NetIncome`, `DepreciationAndAmortization`, `ChangeInWorkingCapital`, `StockBasedCompensation`
- **순이익과 영업활동 현금흐름의 관계** 분석
- 감가상각 등 **비현금 항목의 영향 해석**
- **운전자본 변동의 기여도** 분석

---

### 3. 투자활동 현금흐름 분석
- 항목: `InvestingCashFlow`, `CapitalExpenditure`, `PurchaseOfPPE`, `NetInvestmentPurchaseAndSale`, `PurchaseOfBusiness`
- **유형자산 투자 비중**, **사업인수/매각 활동 여부**, **투자 전략 방향성** 해석
- **잉여현금흐름(FreeCashFlow)**과의 관계 분석

---

### 4. 재무활동 현금흐름 분석
- 항목: `FinancingCashFlow`, `RepurchaseOfCapitalStock`, `CashDividendsPaid`, `IssuanceOfDebt`, `RepaymentOfDebt`
- **자본 조달 및 환원 정책(자사주, 배당 등)** 분석
- 부채 조정 내역과 **자금조달 전략 변화** 설명

---

### 5. 현금 유동성 및 순현금 변화
- 항목: `BeginningCashPosition`, `EndCashPosition`, `ChangesInCash`, `EffectOfExchangeRateChanges`
- **분기별 순현금 흐름 요약** 및 변화 요인 해석
- **외환 영향 포함 여부** 설명

---

### 6. 시계열 흐름 요약
- 각 분기별 주요 지표(영업, 투자, 재무, 순현금 흐름) 요약 표 작성
- 분기 간 비교를 통한 **추세 파악 및 이상치 탐지**
- **특이 시점 변화 요인 설명** 포함

---

### 7. 종합 평가 및 투자 시사점
- 영업활동 중심의 **현금 창출력 평가**
- **투자 및 자본 정책**의 방향성 해석
- **현금 유동성과 배당 지속 가능성**에 대한 투자자 관점의 종합 평가

---

## 분석 수준
- 분기 간 흐름을 중심으로 한 **시계열 기반 구조 분석**
- 각 항목 간 관계성과 기여도를 정성적으로 설명
- **투자자 관점**에서 유의미한 인사이트 제공

        """,
        
        "cash_flow_yearly": """
다음은 기업의 **연간 현금흐름표 시계열 데이터(JSON)**입니다. 이 데이터를 분석하여 마크다운 형식의 재무 리포트를 작성해주세요.

## 작성 스타일
- 문체: "~임", "~함"의 **간결한 서술체** 사용
- 형식: **마크다운 문서 형식** (제목, 소제목, 표 포함 가능)
- **강조가 필요한 수치, 시사점은 마크다운 강조 문법 사용** (**굵게**)
- **수치 나열보다는 해석 중심**으로 작성
- **시계열 흐름** 및 **재무 구조 변화**에 대한 설명 필수

---

## 요구 항목

### 1. 기본 정보
- **데이터 연도 범위** 및 **통화 단위** 명시
- **총 영업활동/투자활동/재무활동 현금흐름**의 시계열 추이 간략 소개

---

### 2. 영업활동 현금흐름 분석
- 항목: `OperatingCashFlow`, `NetIncome`, `DepreciationAndAmortization`, `ChangeInWorkingCapital`, `StockBasedCompensation`, `DeferredTax`, `OtherNonCashItems`
- **순이익 대비 영업현금흐름 비율** 분석
- **비현금성 조정 항목**이 영업현금에 미치는 영향 설명
- **운전자본 변동** 분석 (특히 `ChangeInWorkingCapital` 중심)

---

### 3. 투자활동 현금흐름 분석
- 항목: `CapitalExpenditure`, `PurchaseOfPPE`, `SaleOfInvestment`, `PurchaseOfInvestment`, `NetInvestmentPurchaseAndSale`, `NetBusinessPurchaseAndSale`
- **설비투자(자본적 지출)의 추세**
- **순투자 흐름**과 **사업 인수/매각**의 변화 해석
- **총 투자현금흐름**이 미래 성장과 연결되는지 평가

---

### 4. 재무활동 현금흐름 분석
- 항목: `FinancingCashFlow`, `IssuanceOfDebt`, `RepaymentOfDebt`, `CommonStockPayments`, `RepurchaseOfCapitalStock`, `CashDividendsPaid`, `ProceedsFromStockOptionExercised`
- **주주환원 정책**(배당, 자사주 매입) 분석
- **부채 발행 및 상환 전략**의 변화 추이
- **재무적 유연성 확보 여부 평가**

---

### 5. 현금 흐름 종합 및 잔액 변화
- 항목: `BeginningCashPosition`, `EndCashPosition`, `ChangesInCash`, `EffectOfExchangeRateChanges`, `FreeCashFlow`
- **총 현금 변화 요인** 및 **연간 말 현금잔액 추이** 설명
- **잉여현금흐름(FCF)**의 시계열 변화와 활용 방향 분석

---

### 6. 시계열 흐름 요약
- 연도별 핵심 항목을 **표**로 정리 (`OperatingCF`, `InvestingCF`, `FinancingCF`, `FreeCF`, `NetIncome`, `CapEx`, `EndCash`)
- **패턴 중심 분석**: 꾸준한 증가/감소, 변동성 여부, 특정 연도의 전환점 등 식별

---

### 7. 종합 평가 및 투자 시사점
- **영업 vs 투자 vs 재무 흐름 간 균형** 평가
- **현금창출력**, **설비투자 규모**, **재무전략**의 상호 관계 해석
- **장기 투자자 관점에서의 현금흐름 질 평가**

        """,
        
        "all_financial_data_quarterly": """
다음은 기업의 **분기별 시계열 종합 재무 데이터(JSON)**입니다. 이 데이터를 기반으로 **마크다운 형식의 재무 리포트**를 작성해주세요.

## 작성 스타일
- 문체: "~임", "~함"의 **간결한 서술체** 사용
- 형식: **마크다운 문서 형식** (제목, 소제목, 표 포함 가능)
- **강조가 필요한 수치, 전환점, 시사점은 마크다운 강조 문법 사용** (**굵게**)
- **시계열 흐름을 중심으로 한 해석**과 **수치 간 상관관계 설명** 포함
- 단순 수치 나열보다 **분석과 통찰 중심 작성**

---

## 요구 항목

### 1. 기본 정보
- 데이터 범위: `date` 기준 첫 분기 ~ 마지막 분기
- 통화 단위 및 보고 주기 명시 (예: USD, Quarterly)
- 분석 항목: 수익성, 유동성, 성장성, 효율성, 자산/부채 구조 등

---

### 2. 수익성 분석
- 항목: `totalRevenue`, `grossProfit`, `operatingIncome`, `netIncome`, `costOfRevenue`
- **분기별 매출/이익 흐름**, **계절성 존재 여부**, **마진율 변화** 해석
- **영업이익률 = operatingIncome / totalRevenue**
- **순이익률 = netIncome / totalRevenue** 시계열 추이 설명

---

### 3. 유동성과 지급능력
- 항목: `currentAssets`, `currentLiabilities`, `cashAndShortTermInvestments`, `inventory`, `accountsReceivable`
- **유동비율 = currentAssets / currentLiabilities**
- **당좌비율 = (currentAssets - inventory) / currentLiabilities**
- **단기 재무건전성 변화 및 현금유동성 흐름** 설명

---

### 4. 성장성 지표 분석
- 항목: `totalRevenue`, `netIncome`, `operatingIncome`의 분기별 성장률
- **QoQ(전분기 대비 성장률)**, **YoY(전년동기대비 성장률)** 모두 고려
- **성장 모멘텀 지속성 평가** 및 주요 원인 추정

---

### 5. 자본 효율성 및 수익률
- 항목: `returnOnAssets`, `returnOnEquity`, `returnOnCapitalEmployed`, `netMargin`, `assetTurnover`
- **자산 수익률(ROA)** 및 **자기자본 수익률(ROE)** 시계열 흐름 해석
- **영업 효율성 및 자산 활용도 개선 여부 판단**

---

### 6. 재무 안정성 및 부채 구조
- 항목: `totalAssets`, `totalLiabilities`, `debtToEquity`, `longTermDebt`, `shortTermDebt`, `interestCoverage`
- **부채비율**, **이자보상배율**, **총자산 대비 부채 비중 변화** 설명
- 단기 vs 장기 부채의 구도 변화 및 상환능력 해석

---

### 7. 현금흐름 분석
- 항목: `operatingCashFlow`, `investingCashFlow`, `financingCashFlow`, `freeCashFlow`
- **영업활동현금흐름의 안정성**, **자본지출 흐름**, **자체현금창출력 평가**
- **FCF = operatingCashFlow - capitalExpenditure**

---

### 8. 배당 및 주주환원
- 항목: `dividendsPaid`, `shareRepurchase`, `dividendYield`, `payoutRatio`
- **배당 정책의 일관성**, **자사주 매입 추이**, **주주가치 제고 노력 평가**

---

### 9. 시계열 요약 및 주요 포인트 정리
- **표 형식**으로 주요 항목의 분기별 변화 정리
- 급격한 변화가 있었던 분기 강조 및 원인 해석 시도
- 매출, 이익, 자산, 부채 등 핵심 지표들의 **패턴 식별 및 시사점 도출**

---

### 10. 종합 평가 및 투자 시사점
- **단기적 재무 흐름 안정성**, **성장 지속성**, **자본 효율성 측면에서의 투자 매력도 평가**
- 리스크 요인과 구조적 강점 요약
- **향후 개선 또는 악화 가능성이 있는 재무 영역 제시**

---

## 분석 수준
- 수치 해석을 넘어선 **정성적 평가 중심의 고차원 분석**
- 시계열 간 흐름/패턴 인식 능력 반영
- 투자자 입장에서 **재무 데이터를 전략적으로 이해할 수 있도록** 구성

        """,
        
        "all_financial_data_annual": """
당신은 구조화된 연간 재무 데이터(JSON)를 해석하는 데 특화된 재무 분석 전문가 AI입니다. 제공된 `all_financial_data_annual.json` 데이터를 기반으로, 시계열 흐름을 중심으로 한 재무 분석 보고서를 **마크다운 형식**으로 작성해주세요. 수치 간 비교, 트렌드, 재무 구조 변화에 초점을 맞춰 분석해야 합니다.

다음의 구성과 지침을 철저히 따라 작성하세요:

# 연간 재무 요약 리포트

## 1. 개요
- 분석 대상 기간(가장 오래된 연도부터 가장 최신 연도까지)과 사용된 통화 단위를 명시
- 해당 기간 동안 회사의 재무 상태와 성과가 **개선되었는지, 안정적인지, 악화되었는지** 간단히 요약

## 2. 손익계산서 하이라이트
다음 항목에 대해 연도별 흐름 요약:
- **총매출 (Total Revenue)**
- **매출총이익 (Gross Profit)**
- **영업이익 (Operating Income)**
- **순이익 (Net Income)**
- **주당순이익 (EPS: 기본 및 희석)**

- 주요 수치의 증가 또는 감소에 대해 비교 설명
- **이익률 추이** 및 **영업 레버리지 변화** 언급

## 3. 재무상태표 트렌드
다음 항목 중심으로 변화 요약:
- **총자산**, **총부채**, **자기자본**
- **운전자본**, **유형자산 장부가치**
- **현금 및 단기투자자산**과 **총부채** 비교

- **유동성**, **지급 능력**, **자본구조**에 대한 평가 포함

## 4. 현금흐름 분석
다음 항목에 대해 연도별 흐름 설명:
- **영업활동 현금흐름**
- **투자활동 현금흐름**
- **재무활동 현금흐름**
- **잉여현금흐름 (Free Cash Flow)**

- 현금흐름의 급격한 변화가 있었다면 원인을 추정하여 서술

## 5. 투자 및 자본 지출
다음 항목 분석:
- **자본적 지출 (Capital Expenditures)** 추이
- **연구개발비 (R&D Spending)**
- **자사주 매입** 및 **배당 지급액**

- 성장이 우선인지, 주주환원이 우선인지에 대한 전략 해석 포함

## 6. 수익성 지표 (가능 시 계산 또는 추정)
- **매출총이익률 (Gross Margin)**
- **영업이익률 (Operating Margin)**
- **순이익률 (Net Margin)**
- **총자산수익률 (ROA)**
- **자기자본수익률 (ROE)**

- 수익성의 시계열 변화를 간결히 해석

## 7. 레버리지 및 유동성 지표
사용 가능한 항목을 바탕으로:
- **부채비율 (Debt-to-Equity Ratio)**
- **이자보상배율 (Interest Coverage Ratio)** – EBIT와 이자비용이 있는 경우
- **순부채 및 현금 포지션 변화**에 대해 서술

## 8. 핵심 관찰사항 및 전략적 평가
전체 분석을 종합하여:
- **재무적 강점과 리스크 요인**
- **전략적 방향성** (예: 비용구조 개선, R&D 강화, 부채 축소 등)
- 종합적으로 기업의 재무 구조가 **건전해지고 있는지 또는 제약이 커지고 있는지** 판단

## 출력 형식 지침
- 중요한 수치와 용어는 **굵게** 표시할 것
- 연도 간 **변화 흐름과 비교**를 명확하게 기술할 것
- 표 또는 리스트를 활용하여 가독성 있게 구성할 것
- 과도한 금융 용어 사용은 지양하고, 비재무 전문가도 이해할 수 있도록 설명할 것

위의 구성과 지침을 엄격히 따르세요. JSON에 존재하는 항목만을 사용하여 분석하고, 존재하지 않는 값을 임의로 생성하지 마세요.

        """,
        
        "recommendation_trend": """
다음은 애널리스트의 **투자의견 시계열 데이터(JSON)**입니다. 이 데이터를 분석하여 마크다운 형식의 인사이트 리포트를 작성해주세요.

## 작성 스타일
- 문체: "~임", "~함"의 **간결한 서술체** 사용
- 형식: **마크다운 문서 형식** (제목, 소제목, 표 포함 가능)
- **강조가 필요한 수치, 시사점은 마크다운 강조 문법 사용** (**굵게**)
- **수치 나열보다는 해석 중심**으로 작성
- **시계열 흐름** 및 **의견 변화 추이 설명** 필수

---

## 요구 항목

### 1. 기본 정보
- **데이터 기준 시점 및 기간 범위** 명시 (`period`: "0m", "-1m", "-2m", "-3m" 등)
- 각 기간의 **투자의견 분포**(`strongBuy`, `buy`, `hold`, `sell`, `strongSell`) 표로 요약

---

### 2. 시계열 추이 분석
- 기간별로 다음 항목의 변화 추이를 설명
  - `strongBuy` 의견 수의 변화
  - `buy`와 `hold` 간 비율 변화
  - **부정적 의견(`sell`, `strongSell`)의 유무 및 안정성**

- **최근 의견이 긍정적으로 쏠리는지 여부** 평가
- 의견 수가 **정체, 상승, 하락 중 어느 경향인지** 분석

---

### 3. 총합 및 비중 분석
- 각 기간별 **전체 의견 수 대비 강력 매수 비중, 보통 매수 비중, 보유 비중** 등 백분율 계산
- **긍정적 의견(Strong Buy + Buy)** 비중이 **전체의 몇 %**인지 명시
- `hold` 이상 비중과 **부정적 의견이 거의 없는 구조**에 대한 해석 포함

---

### 4. 의견 안정성 평가
- `sell`, `strongSell` 의견이 장기간 0임을 기반으로 **시장 신뢰도 또는 투자자 확신** 해석
- 의견의 **급격한 변화 없이 유지**되고 있는지 평가

---

### 5. 종합 평가 및 투자 시사점
- **시장 전반의 애널리스트 의견에 기반한 투자 온도 평가**
- **강력한 매수 의견이 유지되고 있다면 그 의미에 대한 분석**
- 의견 수의 유지 여부가 **분석 커버리지 확대 or 축소 신호인지 여부** 해석

---

## 분석 수준
- 단순한 수치 나열이 아닌 **시계열 변화**, **비중 해석**, **투자 심리 해석** 중심
- 투자자 관점에서 **투자의견 흐름이 주는 시사점** 도출

""",
        
        "earings_trend": """
다음은 애널리스트의 **실적 추정 시계열 데이터(JSON)**입니다. 이 데이터를 분석하여 마크다운 형식의 인사이트 리포트를 작성해주세요.

## 작성 스타일
- 문체: "~임", "~함"의 **간결한 서술체** 사용
- 형식: **마크다운 문서 형식** (제목, 소제목, 표 포함 가능)
- **강조가 필요한 수치, 시사점은 마크다운 강조 문법 사용** (**굵게**)
- **수치 나열보다는 해석 중심**으로 작성
- **시계열 흐름 및 실적 변화의 맥락을 해석**할 것

---

## 요구 항목

### 1. 기본 정보
- 데이터 기준: `period`, `endDate` 항목 기반으로 **분기/연간별 예측 범위 요약**
- **통화 단위(USD)** 명시

---

### 2. 실적 추정 요약
- 항목: `earningsEstimate.avg`, `low`, `high`, `yearAgoEps`, `growth`
- 각 기간별 **EPS 예측 평균**, **전년 동기 대비 성장률**, **예측 범위의 상하단**
- **분석 커버리지 규모 (`numberOfAnalysts`)** 포함
- **예상 수익 성장률이 두 자릿수인 경우 강조**

---

### 3. 매출 추정 요약
- 항목: `revenueEstimate.avg`, `low`, `high`, `yearAgoRevenue`, `growth`
- **평균 매출 추정치**, **예상 성장률**, **상/하단 범위 해석**
- 매출 성장률이 **실적 성장률과 어떤 관계를 갖는지 평가**

---

### 4. EPS 트렌드 분석
- 항목: `epsTrend.current`, `7daysAgo`, `30daysAgo`, `60daysAgo`, `90daysAgo`
- 각 기간 EPS 예측이 **상향/하향되고 있는지 흐름 해석**
- **최근 수정치(7일/30일 기준)가 꾸준히 상향 중인지 여부** 판단

---

### 5. EPS 리비전 분석
- 항목: `epsRevisions.upLast7days`, `upLast30days`, `downLast30days`, `downLast7Days`
- **리비전 총합 대비 상향/하향 비율 해석**
- **애널리스트 의견 일치도 및 방향성(긍정/부정)** 분석

---

### 6. 시계열 흐름 요약
- 기간별 EPS 및 매출 예측의 핵심 수치 비교 표 작성
- EPS/매출 `growth` 항목을 중심으로 **추세 파악 및 전환점 설명**
- 분기 대비 연간, 혹은 다음 해(+1y)로 갈수록 **기대치가 상향/하향인지** 평가

---

### 7. 종합 평가 및 투자 시사점
- **애널리스트들의 전망이 긍정적 추세인지 여부**
- **EPS 상향/하향과 매출 성장 간의 관계** 해석
- **중장기 실적 모멘텀 및 투자자 관점에서의 기대치 반영 여부** 평가

---

## 분석 수준
- 단순 수치 요약이 아닌 **예측 흐름 해석과 추세 중심의 해석**
- EPS, 매출, 애널리스트 리비전 간의 **관계성과 방향성 분석**
- **투자자 관점에서의 실적 기대와 리스크 요인 파악** 포함

        """,
        
        "earning_history" : """
다음은 기업의 **과거 실적(Earnings History) 시계열 데이터(JSON)**입니다. 이 데이터를 분석하여 마크다운 형식의 리포트를 작성해주세요.

## 작성 스타일
- 문체: "~임", "~함"의 **간결한 서술체** 사용
- 형식: **마크다운 문서 형식** (제목, 소제목, 표 포함 가능)
- **강조가 필요한 수치, 시사점은 마크다운 강조 문법 사용** (**굵게**)
- **단순 수치 나열보다 해석 중심**으로 설명
- **시간적 흐름에 따른 변화 분석** 필수

---

## 요구 항목

### 1. 기본 정보
- 데이터는 **최근 4개 분기**의 실적을 포함함
- 통화 단위는 **USD** 기준임
- 각 분기의 `quarter`, `epsActual`, `epsEstimate`, `epsDifference`, `surprisePercent` 값을 **표 형식으로 요약**

---

### 2. EPS 정확도 및 예측 신뢰성 분석
- 분기별 **예측치(`epsEstimate`)와 실제치(`epsActual`)의 차이** 분석
- `epsDifference`와 `surprisePercent`의 크기를 비교해 **예측 정확도 개선 또는 악화 여부** 설명
- **최근 분기(`-1q`)가 가장 큰 서프라이즈**를 보인 경우, 그 의미 분석

---

### 3. 어닝 서프라이즈 패턴 분석
- **4개 분기 모두 실제 EPS가 추정치를 초과**
- `surprisePercent`가 **상승 추세인지, 변동성이 큰지** 시계열 기반으로 분석
- 가장 의미 있는 서프라이즈가 있었던 분기(`2025-03-31`)에 대한 강조적 해석

---

### 4. 시계열 흐름 요약
- 분기별 `epsActual`, `epsEstimate`, `surprisePercent`의 흐름을 간단한 표나 그래프 스타일 리스트로 요약
- **예측 정확도가 향상되고 있는지**, 혹은 **불안정한 패턴이 존재하는지** 해석

---

### 5. 종합 평가 및 시사점
- 애널리스트의 예측이 **전반적으로 신뢰할 만한지** 평가
- 어닝 서프라이즈가 **일회성인지, 구조적 실적 개선 신호인지** 분석
- **실적 안정성** 및 향후 분기 실적 기대에 대한 투자자 관점의 인사이트 도출

---

## 분석 수준
- **분기별 시계열 흐름** 중심의 EPS 정확도와 추세 분석
- 예측과 실제의 차이로부터 **기업 실적 변동성 또는 시장 대응력 해석**
- **투자자 입장에서의 실적 신뢰도 평가** 포함

        """,

        "grading_history" : """
다음은 기업에 대한 **애널리스트 등급 변경 시계열 데이터(JSON)**입니다. 이 데이터를 분석하여 마크다운 형식의 리포트를 작성해주세요.

## 작성 스타일
- 문체: "~임", "~함"의 **간결한 서술체** 사용
- 형식: **마크다운 문서 형식** (제목, 소제목, 표 포함 가능)
- **강조가 필요한 수치, 시사점은 마크다운 강조 문법 사용** (**굵게**)
- **단순 수치 나열보다 변화 흐름 및 해석 중심으로 작성**
- **기간별 등급 변화의 패턴과 투자 시사점 포함**

---

## 요구 항목

### 1. 기본 정보
- 분석 대상: `gradingHistory` 배열의 데이터
- 각 항목: `epochGradeDate`, `firm`, `toGrade`, `fromGrade`, `action`, `ratingScaleMark`, `companyName`
- **표로 최근 등급 변경 내역 요약** (날짜, 기관, 이전등급→현재등급, 액션 등)

---

### 2. 등급 변화 추이 분석
- `action` 값에 따라 **Upgrade / Downgrade / Initiated / Reiterated**를 분류
- 특정 시점(최근 6개월 등)에서 **등급 변화가 집중되었는지 여부** 확인
- `toGrade`의 평균적 수준 파악 (예: 대부분 Buy로 유지되는 경우)

---

### 3. 평가기관별 성향 분석
- `firm`을 기준으로 등급을 부여한 주체들을 집계
- 각 기관별로 **긍정적 평가(Upgrade/Bullish) 비중이 높은지**, **보수적인 기관인지** 분류
- **특정 기관이 반복적으로 의견을 갱신하는지 여부** 설명

---

### 4. 시계열 흐름 요약
- 날짜 기준으로 **등급 조정 이벤트를 시계열 순으로 정리**
- 등급 변경이 **주기적으로 발생하는지**, 혹은 **실적 발표 시즌에 몰리는지** 설명
- **최근에 등급 상향 추세가 뚜렷한지** 판단

---

### 5. 종합 평가 및 투자 시사점
- **등급 변화의 방향성(긍정 ↔ 부정)**이 기업 실적 및 외부 환경과 어떤 관계를 보이는지 해석
- **애널리스트 커버리지의 폭과 빈도**가 투자자에게 주는 신뢰성 판단
- **주가 상승 기대감, 리스크 경고 등 실제 투자 판단에 미치는 의미 요약**

---

## 분석 수준
- 단순 나열이 아닌 **시계열 기반의 등급 흐름 해석**
- 기관별 평가지표의 특성과 빈도까지 **정성적으로 분석**
- **투자자 입장에서 등급 데이터가 전달하는 시그널을 해석**할 것

        """,

        "valuation_measures" : """
다음은 기업의 **시계열 기반 밸류에이션 지표 데이터(JSON)**입니다. 이 데이터를 분석하여 마크다운 형식의 리포트를 작성해주세요.

## 작성 스타일
- 문체: "~임", "~함"의 **간결한 서술체** 사용
- 형식: **마크다운 문서 형식** (제목, 소제목, 표 포함 가능)
- **강조가 필요한 수치, 시사점은 마크다운 강조 문법 사용** (**굵게**)
- **시계열 흐름 기반의 추세 분석** 포함
- **단순 수치 나열보다 해석 중심**으로 설명

---

## 요구 항목

### 1. 기본 정보
- 데이터 구간: `asOfDate` 기준의 시계열 데이터 범위 명시
- 모든 수치는 **USD 기준**임
- 주요 분석 지표: `PeRatio`, `ForwardPeRatio`, `PbRatio`, `PsRatio`, `PegRatio`, `EnterpriseValue`, `MarketCap`

---

### 2. PER(P/E Ratio) 분석
- 항목: `PeRatio`, `ForwardPeRatio`
- 시계열 흐름에서 **PER 상승/하락 시기**와 원인 분석
- `ForwardPeRatio`와의 차이를 통해 **미래 수익 기대감** 해석
- **PER 20 이상 지속 구간**, 혹은 **급등/급락 시점 강조**

---

### 3. PBR(P/B Ratio) 및 PSR(P/S Ratio) 분석
- 항목: `PbRatio`, `PsRatio`
- **자산 대비 주가의 고평가/저평가 가능성** 평가
- `PsRatio` 상승 흐름은 **매출 기반 기업가치 상승** 시사 → 주가 기대 심리 분석

---

### 4. PEG(P/E to Growth Ratio) 분석
- 항목: `PegRatio`
- PEG가 **1.0 이하인 시점은 저평가**로 간주 → 이 시기의 투자 매력도 강조
- 최근 수치 상승 혹은 2.0 이상 유지 구간이 **성장 기대 대비 부담**으로 작용하는지 평가

---

### 5. EV/EBITDA 및 EV/Revenue 분석
- 항목: `EnterprisesValueEBITDARatio`, `EnterprisesValueRevenueRatio`
- **EV 기반 밸류에이션은 인수합병 혹은 대형주 분석에 중요** → 비정상 급등/급락 시기 주목
- EV/Revenue가 5~7 구간을 벗어날 경우 해석 필요

---

### 6. 시계열 흐름 요약
- 주요 항목별 **시계열 표 정리** (PER, PBR, PEG 등)
- **구간별 변곡점 식별** (예: 2024-06~07월 급등)
- 그래프 또는 리스트 형식으로 **밸류에이션 패턴 요약**

---

### 7. 종합 평가 및 투자 시사점
- **현재 밸류에이션이 고평가/저평가 구간에 속하는지 해석**
- 과거 대비 상승/하락 요인의 설명과 **미래 리스크 또는 기회 요인 정리**
- PER과 PEG 간의 괴리 여부, 시가총액과 EV 흐름 비교 등을 통한 **투자 전략 인사이트 제공**

---

## 분석 수준
- **시계열 흐름을 기반으로 한 정성적 밸류에이션 해석**
- 서로 다른 지표 간의 연관 관계 및 괴리 분석
- 투자자 관점에서 **적정 가치 평가** 및 **시장 기대와의 차이 해석**

        """,

        "insider_transactions" : """
다음은 기업의 **내부자 거래 시계열 데이터(JSON)**입니다. 이 데이터를 분석하여 마크다운 형식의 내부자 거래 리포트를 작성해주세요.

## 작성 스타일
- 문체: "~임", "~함"의 **간결한 서술체** 사용
- 형식: **마크다운 문서 형식** (제목, 소제목, 표 포함 가능)
- **강조가 필요한 수치, 시사점은 마크다운 강조 문법 사용** (**굵게**)
- **시계열 흐름 및 반복적 거래 패턴에 주목한 해석 중심**
- 단순 수치 나열보다는 **의미 있는 행동 해석** 강조

---

## 요구 항목

### 1. 기본 정보
- 분석 대상: `filerName`, `startDate`, `shares`, `value`, `transactionText`, `filerRelation`, `ownership`
- 기간: earliest ~ latest `startDate` 범위 명시
- 거래유형 분류: Sale, Gift, Award 등 **행위별 구분**

---

### 2. 내부자별 거래 분석
- 주요 인물: `SHRIRAM KAVITARK RAM`, `HENNESSY JOHN L` 등
- 각 인물별로 **거래 빈도, 거래 총량, 거래 유형** 분석
- **동일 인물의 반복적 매도/기부 등 거래 행위 해석**
- **지분 감소 추세 vs 보유 유지 경향 파악**

---

### 3. 거래 유형별 분석
- `transactionText` 기반으로 거래 분류:
  - **Sale**: 내부자의 현금화 의도 판단
  - **Gift**: 무상 이전, 세금 혹은 기부 목적 가능성
  - **Award/Grant**: 보상성 부여 판단
- 유형별로 **거래 규모 및 빈도 변화** 해석

---

### 4. 거래 시점 및 주가 연동
- `startDate` 기준 시계열 흐름에서 **특정 시점에 거래 집중 여부 확인**
- 고가 구간에서 매도 집중 시 **이익 실현 목적 시사**
- 주가 흐름과 내부자 거래 간 **상관성 간접 추론**

---

### 5. 시계열 흐름 요약
- 거래 시점별로 **내부자별 매도/기부/수령 활동을 리스트로 요약**
- 특정 분기 또는 연도에 **집중 거래 발생 여부 분석**
- **표 형태**로 최근 거래 내역 정리 (날짜, 이름, 유형, 수량, 금액)

---

### 6. 종합 평가 및 투자 시사점
- 내부자 거래 활동이 **긍정적/부정적 시그널인지** 종합 해석
- **반복적 매도는 주가 고점 신호 가능성**, **보유 강화는 장기 낙관의 시그널**일 수 있음
- 내부자 매도 시기와 기업 이벤트(실적발표 등) 간 연계 가능성 탐색

---

## 분석 수준
- 단순 거래 기록 나열을 넘어 **내부자 심리 해석 및 전략 판단 가능성 제시**
- 시계열을 활용한 **패턴 기반 리스크 또는 기회 도출**
- **투자자 입장에서 내부자의 거래를 어떤 시그널로 해석할지** 중점 분석

        """,

        "corporate_events" : """
다음은 기업의 **시계열 기반 기업 이벤트 데이터(JSON)**입니다. 이 데이터를 분석하여 마크다운 형식의 이벤트 리포트를 작성해주세요.

## 작성 스타일
- 문체: "~임", "~함"의 **간결한 서술체** 사용
- 형식: **마크다운 문서 형식** (제목, 소제목, 표 포함 가능)
- **강조가 필요한 시점, 이벤트 유형, 빈도는 마크다운 강조 문법 사용** (**굵게**)
- **단순 나열보다 흐름 중심 해석** 포함
- **시간 순서 및 이벤트 집중 구간에 주목할 것**

---

## 요구 항목

### 1. 기본 정보
- 이벤트 발생 범위: `startDate` 기준 시계열 기간 명시
- 주요 항목: `eventType`, `headline`, `startDate`, `relatedTickers`
- **이벤트 유형별 요약**: Dividend, Earnings, M&A, Guidance 등

---

### 2. 이벤트 유형별 분석
- `eventType` 기준으로 이벤트를 분류하고, **각 유형별 빈도 및 시점** 분석
  - **Dividend**: 배당 결정, 배당 성향 해석
  - **Earnings Call**: 실적 발표 일정의 규칙성 및 영향력
  - **M&A 관련**: 인수합병 뉴스가 주가에 미치는 파급 가능성
  - **Guidance/Forecast**: 실적 전망 조정 여부와 주기

---

### 3. 시계열 흐름 요약
- 연도/분기별 이벤트 수 집계
- 특정 시기에 이벤트 집중 여부 확인 (예: 연말, 실적 발표 전후)
- **이벤트 종류별 시기 분포 차이** 해석

---

### 4. 이벤트 영향력 추정
- `headline` 및 `eventType`를 활용해 **중요 이벤트 구분**
- 반복적으로 등장하거나 실적에 영향을 줄 수 있는 이벤트에 강조
- 과거 실적 발표 시점과 연계하여 **예측 가능성 및 전략적 판단 근거 제시**

---

### 5. 종합 평가 및 투자 시사점
- **기업의 이벤트 일정이 전략적 혹은 계절성 기반인지** 해석
- **배당 및 실적 발표 주기와 투자 판단 연계 가능성** 분석
- 향후 이벤트 일정을 통해 **단기 투자 시점 포착 가능 여부** 판단

---

## 분석 수준
- 시계열 기반 이벤트 흐름을 중심으로 분석
- **이벤트 유형 간 반복성, 전략성, 예측 가능성 해석 포함**
- **투자자 관점에서 이벤트가 미치는 영향 요약 및 행동 제안**

        """,

        "sec_filings" : """
다음은 기업의 **SEC 공시 시계열 데이터(JSON)**입니다. 이 데이터를 분석하여 마크다운 형식의 리포트를 작성해주세요.

## 작성 스타일
- 문체: "~임", "~함"의 **간결한 서술체** 사용
- 형식: **마크다운 문서 형식** (제목, 소제목, 표 포함 가능)
- **강조가 필요한 날짜, 공시유형, 반복 시점은 마크다운 강조 문법 사용** (**굵게**)
- **공시 빈도와 패턴 중심의 시계열 흐름 해석 포함**
- 단순 나열보다 **투자자 관점에서 해석 중심으로 작성**

---

## 요구 항목

### 1. 기본 정보
- 분석 대상 항목: `filingDate`, `formType`, `title`, `filedBy`, `edgarUrl`
- 시계열 기간: earliest ~ latest `filingDate` 범위 명시
- 공시 문서 유형(Form Type): 10-K, 10-Q, 8-K, S-1, DEF 14A 등

---

### 2. 공시 유형별 분석
- `formType` 기준으로 공시를 분류하고 **주요 유형별 비중과 빈도** 분석
  - **10-K / 10-Q**: 정기 재무 보고서 → 기업 실적 흐름 해석 근거
  - **8-K**: 주요 이벤트 발생 알림 → 주가 반응 가능성 높음
  - **DEF 14A / Proxy Statement**: 지배구조, 보수체계 분석 근거
  - **S-1 / F-1**: 상장, 증자 관련 공시

---

### 3. 시계열 흐름 요약
- 공시 발생 시점을 **월/분기별로 집계**
- **특정 시기 집중 공시 여부** 확인 (예: 연초, 실적 발표 시즌)
- `filedBy` 기준으로 **특정 계열사 혹은 대표 법인의 반복 공시 여부 확인**

---

### 4. 주목할 만한 공시 요약
- 제목(`title`)을 기반으로 **중요도 높은 공시 식별**
  - 실적 발표, 경영진 교체, 자사주 매입 등
- `edgarUrl` 활용하여 **투자자가 추가로 검토해야 할 주요 문서 링크 제공**
- 반복되는 핵심 문구를 기반으로 **공시 목적 및 이슈 요약**

---

### 5. 종합 평가 및 투자 시사점
- 공시 빈도 및 유형 변화가 **기업 전략 변화 또는 이슈를 반영하는지 여부 해석**
- 8-K, DEF 14A 등의 **비정기 공시가 증가하는 시점의 리스크 또는 기회 요인 평가**
- 공시가 **주가, 시장 기대치, 기관 반응과 연동될 가능성 있는 시점** 제시

---

## 분석 수준
- **단순 공시 나열이 아닌 시계열 흐름과 전략적 의도 중심 해석**
- 정기/비정기 공시의 비중 변화 및 기업 이벤트 흐름 연계
- **투자자 입장에서 어떤 공시가 중요한지 판단할 수 있도록 해석 중심 작성**

        """      
        
    
    }
    
    default_prompt = f"""
다음은 {file_name} 관련 시계열 주식 데이터입니다. 시간적 흐름에 따른 변화를 중심으로 분석해주세요.

## 요구사항:
1. **시계열 트렌드**: 각 지표의 시간에 따른 변화 패턴 분석
2. **주요 변곡점**: 트렌드가 바뀐 시점과 원인 분석
3. **계절성/주기성**: 반복되는 패턴이나 주기 식별
4. **변동성 분석**: 데이터의 안정성과 변동성 평가
5. **성장성 지표**: 성장률, 개선률 등 동적 지표 계산
6. **예측 인사이트**: 과거 패턴을 바탕으로 한 향후 전망
7. **투자 시사점**: 시계열 분석 결과의 투자 의미

시간의 흐름에 따른 변화에 집중하여 분석해주세요.
"""
    
    base_prompt = prompts.get(file_name, default_prompt)
    
    return f"""{base_prompt}

## 데이터:
```json
{json.dumps(data, ensure_ascii=False, indent=2)}
```

위 시계열 데이터를 분석하여 마크다운 형식으로 작성해주세요. 제목은 "# {file_name.upper()} 시계열 분석 리포트"로 시작하고, 시간적 변화에 중점을 두어 분석해주세요."""


def call_openai_api(prompt: str, max_retries: int = 3) -> str:
    """OpenAI API 호출"""
    
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system", 
                        "content": "당신은 주식 투자 전문가이자 데이터 분석가입니다. 주어진 금융 데이터를 정확하고 통찰력 있게 분석하여 투자자에게 유용한 정보를 제공해야 합니다. 마크다운 형식으로 구조화된 분석 보고서를 작성해주세요."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=4000,
                temperature=0.1
            )
            
            return response.choices[0].message.content
            
        except RateLimitError as e:
            wait_time = 2 ** attempt
            print(f"Rate limit 오류 발생. {wait_time}초 대기 후 재시도... (시도 {attempt + 1}/{max_retries})")
            time.sleep(wait_time)
            
        except APIError as e:
            print(f"API 오류 발생: {e}")
            if attempt == max_retries - 1:
                raise
            time.sleep(1)
            
        except Exception as e:
            print(f"예상치 못한 오류 발생: {e}")
            if attempt == max_retries - 1:
                raise
            time.sleep(1)
    
    raise Exception(f"OpenAI API 호출이 {max_retries}번 모두 실패했습니다.")


def process_single_file(ticker_symbol: str, file_name: str, force_overwrite: bool = False) -> Optional[str]:
    """단일 JSON 파일을 처리하여 마크다운으로 변환"""
    
    # _consolidated.json 파일은 스킵
    if file_name == "_consolidated":
        print(f"{file_name}.json 스킵 (통합 파일)")
        return None
    
    # 파일명이 정의된 파일 목록에 있는지 확인
    all_files = NON_TIMESERIES_FILES | TIMESERIES_FILES
    if file_name not in all_files:
        print(f"❌ '{file_name}'은(는) 지원되지 않는 파일명입니다.")
        print(f"지원되는 파일명: {sorted(all_files)}")
        return None
    
    # 파일 경로 설정
    input_file = RAW_DATA_DIR / ticker_symbol.lower() / f"{file_name}.json"
    output_dir = REFINED_DATA_DIR / ticker_symbol.lower()
    output_file = output_dir / f"{file_name}.md"
    
    # 입력 파일 존재 확인
    if not input_file.exists():
        print(f"❌ {file_name}.json 파일을 찾을 수 없습니다: {input_file}")
        return None
    
    # 출력 디렉토리 생성
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 이미 처리된 파일이면 스킵 (force_overwrite가 False인 경우)
    if output_file.exists() and not force_overwrite:
        print(f"{file_name}.md 이미 존재함 (스킵)")
        return str(output_file)
    
    try:
        print(f"{ticker_symbol.upper()} - {file_name}.json 처리 시작...")
        
        # JSON 파일 읽기
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 데이터가 비어있거나 None이면 스킵
        if not data:
            print(f"❌ {file_name}.json 데이터가 비어있음")
            return None
        
        # 프롬프트 생성 (시계열 여부에 따라)
        if file_name in TIMESERIES_FILES:
            prompt = create_timeseries_prompt(file_name, data)
            print(f"시계열 분석 프롬프트로 처리 중...")
        else:
            prompt = create_non_timeseries_prompt(file_name, data)
            print(f"정적 분석 프롬프트로 처리 중...")
        
        # OpenAI API 호출
        print(f"OpenAI API 호출 중...")
        markdown_content = call_openai_api(prompt)
        
        # 마크다운 파일 저장
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        print(f"✓ {file_name}.md 생성 완료: {output_file}")
        return str(output_file)
        
    except FileNotFoundError:
        print(f"❌ {file_name}.json 파일을 찾을 수 없음")
        return None
        
    except json.JSONDecodeError as e:
        print(f"❌ {file_name}.json JSON 파싱 오류: {e}")
        return None
        
    except Exception as e:
        print(f"❌ {file_name}.json 처리 중 오류: {e}")
        return None


def main():
    """메인 함수"""
    import sys
    
    if len(sys.argv) != 3:
        print("사용법: python stock_data_refiner.py <ticker_symbol> <file_name>")
        print("\n지원되는 파일명:")
        all_files = NON_TIMESERIES_FILES | TIMESERIES_FILES
        for file_name in sorted(all_files):
            file_type = "시계열" if file_name in TIMESERIES_FILES else "정적"
            print(f"  - {file_name} ({file_type})")
        sys.exit(1)
    
    ticker_symbol = sys.argv[1].upper()
    file_name = sys.argv[2]
    
    print(f"=== {ticker_symbol} - {file_name}.json 처리 시작 ===")
    
    result = process_single_file(ticker_symbol, file_name, force_overwrite=False)
    
    if result:
        print(f"\n✓ 처리 완료: {result}")
    else:
        print(f"\n❌ 처리 실패")
        sys.exit(1)


if __name__ == "__main__":
    main()