# filepath: /Users/heuka/Desktop/coding/KAIROS/정기세션/Multi_Modal/code/generate_dialogue.py
import os
import sys
import json
from dotenv import load_dotenv
from openai import OpenAI

# --- Configuration ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESOURCES_DIR = os.path.join(BASE_DIR, "..", "resources")
GROUNDS_DIR = os.path.join(BASE_DIR, "..", "grounds")
STOCK_DATA_DIR = os.path.join(BASE_DIR, "..", "stock_data")
DOTENV_PATH = os.path.join(RESOURCES_DIR, ".env")
load_dotenv(DOTENV_PATH)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

DIALOGUE_FLOW = [
    {
        "segment": "1. Fundamentals — Profitability",
        "topic": "총·영업·순이익률, ROE·ROA·ROIC 등 수익성 지표 트렌드 및 수익 구조의 지속 가능성",
        "field": "재무-수익성",
        "markdown_files": [
            "income_statement_yearly.md",
            "income_statement_quarter.md",
            "all_financial_data_annual.md",
            "all_financial_data_quarterly.md",
            "financial_data.md",
            "key_stats.md"
        ],
        "json_theme": ["Fundamentals > Profitability"],
        "flow": [
            {"speaker": "optimistic",   "type": "development"},
            {"speaker": "pessimistic",  "type": "response"},
            {"speaker": "pessimistic",  "type": "development"},
            {"speaker": "optimistic",   "type": "response"},
            {"speaker": "moderator",    "type": "summary"}
        ]
    },
    {
        "segment": "2. Fundamentals — Financial Health & Cash-Flow",
        "topic": "유동비율·퀵비율·부채비율, 순현금/순부채, 이자보상배율, FCF·OCF·CAPEX 추세 및 배당 정책",
        "field": "재무건전성 & 현금흐름",
        "markdown_files": [
            "balance_sheet_yearly.md",
            "balance_sheet_quarter.md",
            "cash_flow_yearly.md",
            "cash_flow_quarter.md",
            "all_financial_data_annual.md",
            "all_financial_data_quarterly.md",
            "key_stats.md"
        ],
        "json_theme": [
            "Fundamentals > Financial Health",
            "Fundamentals > Cash & Dividend"
        ],
        "flow": [
            {"speaker": "pessimistic",  "type": "development"},
            {"speaker": "optimistic",   "type": "response"},
            {"speaker": "optimistic",   "type": "development"},
            {"speaker": "pessimistic",  "type": "response"},
            {"speaker": "moderator",    "type": "summary"}
        ]
    },
    {
        "segment": "3. Growth Drivers (Products & Markets)",
        "topic": "매출 성장률 y/y, 세그먼트별 성장 동력 (주요 제품·서비스), TAM·SAM·시장 점유율 분석",
        "field": "성장 전략 & 사업 포트폴리오",
        "markdown_files": [
            "product_portfolio.md",
            "segment_revenue_trends.md",
            "market_summary.md",
            "corporate_events.md",
            "sec_filings.md",
            "summary_detail.md"
        ],
        "json_theme": ["Fundamentals > Growth"],
        "flow": [
            {"speaker": "optimistic",   "type": "development"},
            {"speaker": "pessimistic",  "type": "response"},
            {"speaker": "pessimistic",  "type": "development"},
            {"speaker": "optimistic",   "type": "response"},
            {"speaker": "moderator",    "type": "summary"}
        ]
    },
    {
        "segment": "4. Valuation & Market Sentiment",
        "topic": "PER·PSR·EV/EBITDA 등 멀티플, DCF 민감도 분석, 애널리스트 목표가·리코멘데이션 트렌드, 단기 가격 모멘텀",
        "field": "밸류에이션 & 시장심리",
        "markdown_files": [
            "valuation_measures.md",
            "key_stats.md",
            "price_history.md",
            "recommendation_trend.md",
            "grading_history.md"
        ],
        "json_theme": [
            "Valuation > Multiples",
            "Valuation > Targets",
            "Market & Flow > Sentiment & Recommendations"
        ],
        "flow": [
            {"speaker": "pessimistic",  "type": "development"},
            {"speaker": "optimistic",   "type": "response"},
            {"speaker": "optimistic",   "type": "development"},
            {"speaker": "pessimistic",  "type": "response"},
            {"speaker": "moderator",    "type": "summary"}
        ]
    },
    {
        "segment": "5. Risk & Technical Momentum",
        "topic": "주요 주주·기관·내부자 거래 및 공매도 동향, 공급망·규제·거시 리스크, 이동평균·변동성 지표",
        "field": "리스크 요인 & 기술적 모멘텀",
        "markdown_files": [
            "major_holders.md",
            "institution_ownership.md",
            "insider_transactions.md",
            "esg_scores.md",
            "technical_insights.md",
            "price_history.md",
            "volatility_metrics.md"
        ],
        "json_theme": [
            "Market & Flow > Ownership & Insider",
            "Technical Momentum > Moving Averages vs Price"
        ],
        "flow": [
            {"speaker": "optimistic",   "type": "development"},
            {"speaker": "pessimistic",  "type": "response"},
            {"speaker": "pessimistic",  "type": "development"},
            {"speaker": "optimistic",   "type": "response"},
            {"speaker": "moderator",    "type": "summary"}
        ]
    }
]


# --- Helper Functions ---
def load_json_data(file_path):
    """JSON 파일 로드"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"파일을 찾을 수 없습니다: {file_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"JSON 파일 디코딩 오류: {file_path}, 상세: {e}")
        return None
    except Exception as e:
        print(f"파일 로드 중 오류: {file_path}, 상세: {e}")
        return None

def ensure_dir(directory):
    """디렉토리 생성"""
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"디렉토리를 생성했습니다: {directory}")

def generate_script_with_openai(prompt_text, stock_name, instruction, model="gpt-4o"):
    """OpenAI API를 사용한 스크립트 생성"""
    try:
        if not OPENAI_API_KEY:
            print("오류: OPENAI_API_KEY가 설정되지 않았습니다.")
            return f"오류: {stock_name}에 대한 스크립트 생성 실패 - API 키가 없습니다"
            
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        try:
            response = client.responses.create(
                model=model,
                instructions=instruction,
                input=prompt_text,
                temperature=0.7,
                max_output_tokens=10000
            )
            if not response or not hasattr(response, 'output_text'):
                print(f"OpenAI API 응답 오류: {response}")
                return f"오류: {stock_name}에 대한 스크립트 생성 실패 - 잘못된 API 응답"
                
            return response.output_text.strip()
        except Exception as e:
            print(f"OpenAI API 오류: {e}")
            return f"오류: {stock_name}에 대한 스크립트 생성 실패 - API 오류: {e}"
    except Exception as e:
        print(f"OpenAI API 호출 중 예외 발생: {e}")
        return f"오류: {stock_name}에 대한 스크립트 생성 실패 - {e}"

def generate_intro_script(ticker_symbol: str, company_name: str) -> str:
    """투자 분석 토의회 진행자 인트로 대본 생성"""
    
    template_data = {
            "meta": {
                "ticker": ticker_symbol.upper(),
                "company_name": company_name
            }
        }
    
    # 사회자 인트로 프롬프트 생성
    prompt = f"""
당신은 주식 투자 분석 토의회의 전문 진행자입니다. '{company_name}' (티커: {ticker_symbol}) 주식에 대한 심층 분석 토의회를 시작하는 인트로 대본을 작성해주세요.

## 토의회 구성:
- **진행자**: 객관적이고 균형잡힌 토의 진행
- **낙관적 관점 분석가**: {company_name}의 투자 매력과 긍정적 요소에 주목
- **신중한 관점 분석가**: 리스크와 주의사항, 개선이 필요한 부분에 집중

## 대본 구성:
1. **인사 및 토의회 소개** (1분)
   - 청중들에게 따뜻한 인사
   - 오늘의 토의 주제: {company_name} 투자 가치 심층 분석
   - 서로 다른 관점을 통해 균형잡힌 투자 판단을 돕는 토의의 목적
   - 두 분석가가 서로의 의견을 경청하고 배우는 협력적 대화 형식 소개

2. **회사 및 주식 소개** (3분)
   - {company_name}의 사업 영역과 핵심 가치 제안
   - 주요 제품/서비스와 시장에서의 경쟁 위치
   - 최근 주요 성과와 이슈들
   - 현재 주가 수준과 시장의 평가

3. **투자 분석 기초 지식** (4분)
   - 밸류에이션 지표들(PER, PBR, ROE 등)을 통한 기업 가치 평가법
   - 재무 건전성 분석(부채비율, 유동비율, 이자보상배수 등)
   - 성장성과 수익성 지표(매출 성장률, 영업이익률, ROIC 등)
   - ESG 요소와 지속가능경영이 기업 가치에 미치는 영향
   - 기술적 분석과 시장 심리 읽기

4. **토의 진행 방식 안내** (1분)
   - 낙관적 관점 분석가와 신중한 관점 분석가 소개
   - 서로의 분석을 경청하고 인정할 부분은 인정하는 건설적 대화 원칙
   - 각자의 관점에서 제시하는 근거와 데이터를 바탕으로 한 심층 토의
   - 시청자들이 다각도로 기업을 이해할 수 있도록 돕는 상호 보완적 분석

5. **토의 시작** (1분)
   - 먼저 낙관적 관점에서 {company_name}의 투자 매력 제시
   - 이어서 신중한 관점에서의 분석과 의견 교환
   - 균형잡힌 시각으로 투자 결정에 도움이 되는 토의 시작

## 요구사항:
- 총 10분 분량의 충실하고 깊이 있는 내용
- 전문적이면서도 이해하기 쉬운 친근한 설명
- 객관적이고 균형잡힌 어조 유지
- 투자 교육과 실질적 정보 제공에 중점
- 자연스럽고 신뢰감 있는 구어체

두 분석가가 서로의 전문성을 인정하며 건설적으로 대화할 수 있는 분위기를 조성하고, 시청자들이 다양한 관점에서 나오는 통찰을 통해 더 나은 투자 판단을 할 수 있도록 기대감을 높여주세요.
"""

    # 진행자용 instruction 작성
    moderator_instruction = """
당신은 주식 투자 분석 토의회의 전문 진행자 대본 작가입니다. 
다음 사항을 준수하여 진행자 대본을 작성해주세요:

1. 마크다운 코드 블록이나 추가 설명 없이 자연스러운 대본만 작성
2. 균형잡힌 중립적 어조로 작성
3. 두 분석가 간의 건설적 대화를 이끌어내는 진행 스타일
4. 투자 초보자도 이해할 수 있는 친근하고 교육적인 설명
5. 협력적 토의 분위기를 조성하는 따뜻한 구어체
"""

    # OpenAI API 호출
    script_content = generate_script_with_openai(prompt, company_name, moderator_instruction)
    
    if script_content.startswith("오류:"):
        return None
    
    # 대본 파일 저장
    dialogue_dir = os.path.join(BASE_DIR, "..", "dialogue", ticker_symbol.lower())
    ensure_dir(dialogue_dir)
    
    output_path = os.path.join(dialogue_dir, "intro.txt")
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        return output_path
    except Exception as e:
        print(f"❌ 파일 저장 실패: {e}")
        return None

def get_markdown_context(ticker_symbol: str, markdown_files: list) -> str:
    """특정 세그먼트에 필요한 마크다운 파일들을 통합하여 컨텍스트 생성"""
    ticker_dir = os.path.join(STOCK_DATA_DIR, "refined", ticker_symbol.lower())
    
    if not os.path.exists(ticker_dir):
        print(f"⚠️ 티커 디렉토리를 찾을 수 없습니다: {ticker_dir}")
        return ""
    
    context_parts = []
    
    for markdown_file in markdown_files:
        file_path = os.path.join(ticker_dir, markdown_file)
        
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        context_parts.append(f"## {markdown_file}\n{content}")
                        print(f"  📄 로드됨: {markdown_file}")
                    else:
                        print(f"  ⚠️ 빈 파일: {markdown_file}")
            except Exception as e:
                print(f"  ❌ 파일 읽기 실패 ({markdown_file}): {e}")
        else:
            print(f"  ⚠️ 파일 없음: {markdown_file}")
    
    if context_parts:
        return "\n\n".join(context_parts)
    else:
        print("  ⚠️ 로드된 마크다운 파일이 없습니다.")
        return ""


def load_json_template(ticker_symbol: str, template_type: str, themes: list) -> dict:
    """JSON 템플릿 로드 및 특정 테마 필터링"""
    template_path = os.path.join(GROUNDS_DIR, ticker_symbol, f"{ticker_symbol}_{template_type}_template.json")
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template_data = json.load(f)
        if not template_data:
            return {}
        
        # 테마별로 필터링된 데이터 추출
        filtered_data = {}
        for theme in themes:
            # 테마 경로를 따라 데이터 추출 (예: "Fundamentals > Profitability")
            current_data = template_data
            for key in theme.split(" > "):
                key = key.strip()
                if isinstance(current_data, dict) and key in current_data:
                    current_data = current_data[key]
                else:
                    current_data = None
                    break
            
            if current_data:
                filtered_data[theme] = current_data
        
        return filtered_data
        
    except Exception as e:
        print(f"⚠️ JSON 템플릿 로드 중 오류 ({template_type}): {e}")
        return {}

def get_current_segment_history(ticker_symbol: str, segment_num: int, flow_step: int) -> str:
    """현재 세그먼트에서 이전에 생성된 대본들을 읽어와서 히스토리로 반환"""
    dialogue_dir = os.path.join(BASE_DIR, "..", "dialogue", ticker_symbol.lower())
    
    if not os.path.exists(dialogue_dir):
        return ""
    
    history_parts = []
    
    # 현재 flow_step 이전의 파일들을 찾아서 읽기
    for step in range(1, flow_step):
        # 파일 패턴 찾기: seg{segment_num}_*_{step}.txt
        pattern = f"seg{segment_num}_*_{step}.txt"
        
        for filename in os.listdir(dialogue_dir):
            if filename.startswith(f"seg{segment_num}_") and filename.endswith(f"_{step}.txt"):
                file_path = os.path.join(dialogue_dir, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if content:
                            # 파일명에서 speaker와 type 추출
                            parts = filename.replace('.txt', '').split('_')
                            speaker_code = parts[1]
                            type_code = parts[2]
                            
                            speaker = "OPTIMISTIC" if speaker_code == "opt" else "PESSIMISTIC" if speaker_code == "pes" else "MODERATOR"
                            script_type = "DEVELOPMENT" if type_code == "dev" else "RESPONSE" if type_code == "res" else "SUMMARY"
                            
                            history_parts.append(f"[{speaker} - {script_type}]\n{content}")
                except Exception as e:
                    print(f"  ⚠️ 히스토리 파일 읽기 실패 ({filename}): {e}")
    
    return "\n\n".join(history_parts) if history_parts else ""

def generate_single_script(ticker_symbol: str, company_name: str, segment_num: int, flow_step: int) -> str:
    """단일 대본 생성"""
    
    # DIALOGUE_FLOW에서 해당 세그먼트 정보 가져오기
    if segment_num < 1 or segment_num > len(DIALOGUE_FLOW):
        print(f"❌ 잘못된 세그먼트 번호: {segment_num}")
        return None
    
    segment_info = DIALOGUE_FLOW[segment_num - 1]
    
    if flow_step < 1 or flow_step > len(segment_info['flow']):
        print(f"❌ 잘못된 플로우 단계: {flow_step}")
        return None
    
    flow_info = segment_info['flow'][flow_step - 1]
    speaker = flow_info['speaker']
    script_type = flow_info['type']
    
    # 파일명 생성
    speaker_code = "opt" if speaker == "optimistic" else "pes" if speaker == "pessimistic" else "mod"
    type_code = "dev" if script_type == "development" else "res" if script_type == "response" else "sum"
    script_filename = f"seg{segment_num}_{speaker_code}_{type_code}_{flow_step}"
    
    print(f"🎬 {script_filename} 대본 생성 시작...")
    
    # 마크다운 컨텍스트 준비
    markdown_context = get_markdown_context(ticker_symbol, segment_info['markdown_files'])
    
    # JSON 템플릿 로드
    positive_template = load_json_template(ticker_symbol, "positive", segment_info.get('json_theme', []))
    negative_template = load_json_template(ticker_symbol, "negative", segment_info.get('json_theme', []))
    
    # 현재 세그먼트 히스토리 가져오기
    current_segment_history = get_current_segment_history(ticker_symbol, segment_num, flow_step)
    
    # 프롬프트 생성
    prompt = create_dialogue_prompt(
        ticker_symbol=ticker_symbol,
        company_name=company_name,
        segment_info=segment_info,
        speaker=speaker,
        script_type=script_type,
        markdown_context=markdown_context,
        positive_template=positive_template,
        negative_template=negative_template,
        dialogue_history="",  # 더 이상 전체 히스토리는 사용하지 않음
        current_segment_history=current_segment_history
    )
    
    # 인스트럭션 생성
    instruction = create_speaker_instruction(speaker, script_type, segment_info)
    
    # 스크립트 생성
    script_content = generate_script_with_openai(prompt, company_name, instruction)
    
    if script_content and not script_content.startswith("오류:"):
        # 파일 저장
        dialogue_dir = os.path.join(BASE_DIR, "..", "dialogue", ticker_symbol.lower())
        ensure_dir(dialogue_dir)
        
        output_path = os.path.join(dialogue_dir, f"{script_filename}.txt")
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
            print(f"✅ {script_filename} 생성 완료: {output_path}")
            return output_path
        except Exception as e:
            print(f"❌ 파일 저장 실패: {e}")
            return None
    else:
        print(f"❌ {script_filename} 생성 실패: {script_content}")
        return None

def create_dialogue_prompt(ticker_symbol: str, company_name: str, segment_info: dict,
                         speaker: str, script_type: str, markdown_context: str,
                         positive_template: dict, negative_template: dict,
                         dialogue_history: str, current_segment_history: str) -> str:
    """컨텍스트 기반 대화 프롬프트 생성"""
    
    # 스피커별 관점 결정
    perspective = "긍정적" if speaker == "optimistic" else "신중한" if speaker == "pessimistic" else "중립적"
    template_data = positive_template if speaker == "optimistic" else negative_template
    
    # 스크립트 타입별 역할 설명
    if script_type == "development":
        role_desc = f"{perspective} 관점에서 {segment_info['topic']}에 대한 심층 분석을 발전시키는"
    elif script_type == "response":
        role_desc = f"상대방의 분석에 대해 {perspective} 관점에서 응답하고 보완하는"
    else:  # summary
        role_desc = "양쪽 분석가의 의견을 종합하고 균형잡힌 시각으로 정리하는"
    
    prompt = f"""
## 주식 투자 분석 토의회 대본 생성

### 기본 정보
- **회사**: {company_name} (티커: {ticker_symbol.upper()})
- **세그먼트**: {segment_info['segment']}
- **주제**: {segment_info['topic']}
- **분야**: {segment_info['field']}

### 현재 역할
- **스피커**: {speaker} ({perspective} 분석가)
- **스크립트 타입**: {script_type}
- **역할**: {role_desc}

### 대화 맥락
"""

    # 이전 대화 히스토리 추가
    if dialogue_history.strip():
        prompt += f"""
#### 이전 세그먼트들의 대화 요약:
{dialogue_history[:2000]}...  # 너무 길면 제한
"""

    # 현재 세그먼트 히스토리 추가
    if current_segment_history.strip():
        prompt += f"""
#### 현재 세그먼트에서의 대화 흐름:
{current_segment_history}
"""

    # 관련 데이터 컨텍스트 추가
    if markdown_context.strip():
        prompt += f"""
### 관련 재무/시장 데이터
{markdown_context[:3000]}...  # 너무 길면 제한
"""

    # JSON 템플릿 컨텍스트 추가
    if template_data:
        prompt += f"""
### {perspective} 관점 분석 가이드라인
{json.dumps(template_data, ensure_ascii=False, indent=2)}
"""

    prompt += f"""
### 대본 작성 요구사항
1. **전문성**: 구체적인 수치와 데이터 기반의 분석
2. **자연스러움**: 실제 토의회처럼 자연스러운 대화체
3. **교육적 가치**: 투자자들이 배울 수 있는 실질적 통찰
4. **상호 존중**: 다른 관점을 인정하면서도 자신의 견해를 명확히 제시
5. **적절한 분량**: 2-3분 분량의 충실한 내용

### 분석 포인트
- {segment_info['topic']}에 집중한 심층 분석
- 제공된 데이터와 템플릿을 활용한 구체적 근거 제시
- 투자 의사결정에 도움이 되는 실용적 관점

자연스럽고 전문적인 대본을 작성해주세요.
"""

    return prompt

def create_speaker_instruction(speaker: str, script_type: str, segment_info: dict) -> str:
    """스피커별 인스트럭션 생성"""
    
    base_instruction = """
당신은 주식 투자 분석 토의회의 전문 대본 작가입니다.
다음 사항을 준수하여 대본을 작성해주세요:

1. 마크다운 코드 블록이나 추가 설명 없이 자연스러운 대본만 작성
2. 구체적인 수치와 데이터를 활용한 분석
3. 상대방을 존중하면서도 명확한 견해 표현
4. 투자 초보자도 이해할 수 있는 설명
5. 2-3분 분량의 충실한 내용
"""

    if speaker == "optimistic":
        return base_instruction + """
6. 긍정적 관점에서 투자 기회와 강점에 집중
7. 데이터의 밝은 면과 성장 가능성 강조
8. 낙관적이지만 근거 있는 분석 제시
"""
    elif speaker == "pessimistic":
        return base_instruction + """
6. 신중한 관점에서 리스크와 주의사항에 집중
7. 데이터의 우려스러운 면과 개선 필요사항 강조
8. 보수적이지만 건설적인 분석 제시
"""
    else:  # moderator
        return base_instruction + """
6. 중립적 관점에서 양쪽 의견을 균형있게 정리
7. 투자자들이 다양한 관점을 이해할 수 있도록 도움
8. 객관적이고 교육적인 요약 제시
"""

def main():
    """메인 함수 - command line 인자 처리"""
    import argparse
    
    parser = argparse.ArgumentParser(description="주식 투자 분석 토의 대본 생성 도구")
    parser.add_argument("--ticker", required=True, help="티커 심볼 (예: AAPL)")
    parser.add_argument("--company", required=True, help="회사명 (예: Apple Inc.)")
    parser.add_argument("--type", required=True, 
                       choices=["intro", "single"], 
                       help="대본 타입: intro(진행자 인트로), single(단일 대본)")
    parser.add_argument("--segment", type=int, choices=[1,2,3,4,5], 
                       help="세그먼트 번호 (--type single일 때 필수)")
    parser.add_argument("--flow", type=int, choices=[1,2,3,4,5], 
                       help="플로우 단계 (--type single일 때 필수)")
    
    args = parser.parse_args()
    
    try:
        if args.type == "intro":
            # 진행자 인트로 대본 생성
            result = generate_intro_script(args.ticker, args.company)
            if result:
                print(f"✓ 진행자 대본 생성 완료: {result}")
            else:
                print("❌ 진행자 대본 생성 실패")
                sys.exit(1)
                
        elif args.type == "single":
            # 단일 대본 생성
            if not args.segment or not args.flow:
                print("❌ 세그먼트 번호와 플로우 단계를 지정해주세요 (--segment 1-5, --flow 1-5)")
                sys.exit(1)
            
            result = generate_single_script(args.ticker, args.company, args.segment, args.flow)
            
            if result:
                print(f"✓ 단일 대본 생성 완료: {result}")
            else:
                print(f"❌ 단일 대본 생성 실패")
                sys.exit(1)
        else:
            print(f"❌ 지원하지 않는 대본 타입: {args.type}")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ 대본 생성 중 오류: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
