
import os
import sys
import json
import re
from pathlib import Path
from openai import OpenAI
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

# 출력 버퍼링 비활성화
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# 기본 설정
MODEL = "gpt-4o"
MAX_TOKENS = 2000
MAX_WORKERS = 10  # 병렬 처리 워커 수
MAX_RETRIES = 3  # API 호출 재시도 횟수
RETRY_DELAY = 2  # 재시도 간 지연 시간 (초)

# 디렉토리 경로 설정
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
GROUNDS_DIR = PROJECT_ROOT / "grounds"
REFINED_DATA_DIR = PROJECT_ROOT / "stock_data" / "refined"

# OpenAI API 키 가져오기
DOTENV_PATH = PROJECT_ROOT / "resources" / ".env"
load_dotenv(DOTENV_PATH)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    print("오류: OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.", flush=True)
    sys.exit(1)

# 로딩된 마크다운 파일 캐시 (메모리 최적화)
markdown_cache = {}

def load_json(file_path):
    """JSON 파일을 로드합니다."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(data, file_path):
    """JSON 데이터를 파일에 저장합니다."""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"파일이 저장되었습니다: {file_path}", flush=True)

def load_markdown(file_path):
    """마크다운 파일을 로드하고 캐시합니다."""
    if file_path in markdown_cache:
        return markdown_cache[file_path]
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            markdown_cache[file_path] = content
            return content
    except FileNotFoundError:
        print(f"경고: 파일을 찾을 수 없습니다: {file_path}")
        return ""

def find_relevant_markdown_files(ticker_symbol, metric_name, metric_sources):
    """지표와 관련된 마크다운 파일들을 찾습니다."""
    ticker_symbol = ticker_symbol.lower()
    refined_dir = REFINED_DATA_DIR / ticker_symbol
    
    relevant_files = []
    
    # 소스에서 직접 관련 파일 찾기
    for source in metric_sources:
        source_path = refined_dir / f"{source}.md"
        if source_path.exists():
            relevant_files.append(source_path)
    
    # 지표 이름 키워드를 이용하여 관련 파일 찾기
    keywords = re.split(r'[ \(\)/]', metric_name.lower())
    keywords = [k for k in keywords if len(k) > 2]  # 짧은 단어 필터링
    
    for file_path in refined_dir.glob("*.md"):
        file_name = file_path.stem.lower()
        
        # 이미 추가된 파일은 건너뛰기
        if file_path in relevant_files:
            continue
        
        # 키워드 기반 관련성 확인
        for keyword in keywords:
            if keyword in file_name:
                relevant_files.append(file_path)
                break
    
    return relevant_files

def get_metric_context(ticker_symbol, metric_name, metric_sources, metric_value=None, metric_unit=None):
    """특정 지표에 관한 컨텍스트 정보를 마크다운 파일에서 추출합니다."""
    relevant_files = find_relevant_markdown_files(ticker_symbol, metric_name, metric_sources)
    
    if not relevant_files:
        return f"관련 데이터를 찾을 수 없습니다: {metric_name}."
    
    context = f"지표명: {metric_name}\n"
    
    if metric_value is not None:
        if isinstance(metric_value, (int, float)):
            # 백분율 처리
            if metric_unit == '%' and abs(metric_value) < 1:
                formatted_value = f"{metric_value * 100:.2f}%"
            else:
                formatted_value = f"{metric_value:.2f}{metric_unit}" if metric_unit else f"{metric_value:.2f}"
        else:
            formatted_value = f"{metric_value}{metric_unit}" if metric_unit else f"{metric_value}"
        
        context += f"현재 값: {formatted_value}\n\n"
    
    # 관련 마크다운 파일에서 컨텍스트 추출
    context += "관련 정보:\n"
    for file_path in relevant_files:
        content = load_markdown(file_path)
        if content:
            context += f"\n--- {file_path.name} ---\n{content}\n"
    
    return context

def create_agent_prompt(ticker_symbol, metric_name, context, prompt_type="commentary", perspective="positive"):
    """에이전트 프롬프트를 생성합니다."""
    ticker_upper = ticker_symbol.upper()

    # 공통 프롬프트 베이스 생성
    if perspective == "positive":
        base_perspective = f"{ticker_upper}의 재무 상태와 성장 가능성"
        base_approach = "낙관적 시각을 바탕으로 해석하되, 데이터가 시사하는 반대 의견이 있을 경우 이를 **공정하게 인정**하고, 어떻게 해소할 수 있는지 제안하세요."
        strength_point = "**강점 해설**: 지표가 긍정적으로 보일 수 있는 이유를 구체적 근거와 함께 설명합니다."
        concern_point = "**우려 요소 인정**: 동일 지표가 지적할 수 있는 잠재적 리스크를 간략히 언급하고, 이를 완화하거나 이해하는 방안을 제시합니다."
        future_point = "**미래 전망**: 단기·중장기 관점에서 지표가 시사하는 바를 논의합니다."
    else:  # perspective == "negative"
        base_perspective = f"{ticker_upper}의 재무 위험과 잠재적 약점"
        base_approach = "비판적 시각을 바탕으로 해석하되, 데이터가 제시하는 긍정 신호가 있을 경우 이를 **공정하게 인정**하고, 어떻게 볼 수 있는지 설명하세요."
        strength_point = "**긍정 신호 인정**: 동일 지표가 제공할 수 있는 긍정적 해석을 간략히 언급하고, 이를 활용하는 방안을 제안합니다."
        concern_point = "**리스크 해설**: 지표가 부정적으로 보일 수 있는 이유를 구체적 근거와 함께 설명합니다."
        future_point = "**미래 리스크 시나리오**: 잠재적 위험이 어떻게 전개될 수 있는지 논의합니다."

    # 지표 설명(commentary)과 추세 설명(trendDescription) 구분
    if prompt_type == "commentary":
        system_prompt = f"""
당신은 {base_perspective}을 **성실하고 깊이 있게** 분석하는 재무 전문가입니다. {base_approach}

분석 시 다음 요소를 반영하세요:
1. {strength_point}
2. {concern_point}
3. **맥락 연계**: 업계 트렌드, 경쟁사 비교, 거시경제 지표 등과 연관 지어 해석합니다.
4. **역사적 비교**: 과거 추세 및 산업 평균과 비교하며 의미를 부여합니다.
5. {future_point}
6. **전문적 어조**: 신뢰감을 주는 어조로, 분석 보고서 수준의 논리성과 일관성을 유지하세요.

분석 대상 지표: "{metric_name}"
"""
        user_prompt = f"""
다음은 {ticker_upper}의 '{metric_name}' 지표에 관한 상세 정보입니다:

{context}

위 데이터를 바탕으로, {ticker_upper}의 '{metric_name}' 지표에 대한 심층 재무 분석 해설을 작성하세요. 
분석은 **2-3개 이상의** 문단으로 구성하고, 각 문단은 충분한 근거와 통찰로 뒷받침되어야 하며, 전문 기관 보고서 수준의 깊이를 목표로 합니다.
이 지표가 회사의 재무 건전성, 운영 효율성, 또는 성장 전망을 어떻게 반영하는지 구체적으로 설명해주세요.
"""
    else:  # prompt_type == "trendDescription"
        system_prompt = f"""
당신은 {ticker_upper}의 '{metric_name}' 지표 추세를 분석하는 재무 전문가입니다. {base_approach}

추세 분석 시 다음 요소를 반영하세요:
1. **시계열 패턴**: 이 지표의 시간에 따른 변화와 주요 전환점을 식별합니다.
2. **계절성 및 주기성**: 반복되는 패턴이나 계절적 요인이 있는지 분석합니다.
3. **비교 분석**: 업계 평균, 경쟁사, 과거 자체 성과 대비 현재 추세를 평가합니다.
4. **변동성**: 지표의 안정성 또는 변동성을 검토하고 그 의미를 해석합니다.
5. **미래 예측**: 현재 추세를 바탕으로 향후 방향성을 예측합니다.

분석은 간결하면서도 통찰력 있게 작성하세요.
"""
        user_prompt = f"""
다음은 {ticker_upper}의 '{metric_name}' 지표에 관한 상세 정보입니다:

{context}

위 데이터를 바탕으로, {ticker_upper}의 '{metric_name}' 지표의 추세에 대한 **간결하고 통찰력 있는 분석**을 작성하세요. 
약 1-2문단 정도로 지표의 추세와 방향성, 그리고 투자 의사결정에 어떤 의미를 갖는지를 명확하게 설명해주세요.
"""

    return {
        "system_prompt": system_prompt,
        "user_prompt": user_prompt
    }
    
def call_openai_api(system_prompt, user_prompt, retries=MAX_RETRIES):
    """OpenAI API를 호출하여 응답을 얻습니다."""
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=MAX_TOKENS,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"API 호출 오류 (시도 {attempt+1}/{retries}): {e}", flush=True)
            if attempt < retries - 1:
                time.sleep(RETRY_DELAY * (2 ** attempt))  # 지수 백오프
            else:
                return "API 호출 실패로 인해 분석을 제공할 수 없습니다."

def process_metric(ticker_symbol, metric, perspective):
    """개별 지표에 대한 해설을 생성합니다."""
    metric_name = metric.get('metric', '')
    metric_sources = metric.get('source', [])
    metric_value = metric.get('value')
    metric_unit = metric.get('unit', '')
    has_trend = 'trendDescription' in metric  # 트렌드 설명 필드가 있는지 확인
    
    print(f"[{perspective.upper()}] '{metric_name}' 처리 중...", flush=True)
    
    # 지표 관련 컨텍스트 가져오기
    context = get_metric_context(
        ticker_symbol, metric_name, metric_sources, metric_value, metric_unit
    )
    
    # 1. commentary 프롬프트 생성 및 API 호출
    commentary_prompts = create_agent_prompt(
        ticker_symbol, metric_name, context, "commentary", perspective
    )
    commentary = call_openai_api(
        commentary_prompts["system_prompt"], 
        commentary_prompts["user_prompt"]
    )
    
    # 2. trendDescription 생성 (있는 경우에만)
    trend_description = None
    if has_trend:
        print(f"[{perspective.upper()}] '{metric_name}'의 트렌드 설명 생성 중...", flush=True)
        trend_prompts = create_agent_prompt(
            ticker_symbol, metric_name, context, "trendDescription", perspective
        )
        trend_description = call_openai_api(
            trend_prompts["system_prompt"], 
            trend_prompts["user_prompt"]
        )
    
    # 결과 반환
    result = {
        "commentary": commentary,
        "metric": metric_name
    }
    
    if has_trend:
        result["trendDescription"] = trend_description
        
    return result

def create_perspective_template(ticker_symbol, perspective, max_workers=MAX_WORKERS):
    """특정 관점(긍정/부정)의 템플릿을 생성합니다."""
    ticker_symbol = ticker_symbol.lower()
    template_path = GROUNDS_DIR / ticker_symbol / f"{ticker_symbol}_template.json"
    
    if not template_path.exists():
        print(f"오류: 템플릿 파일을 찾을 수 없습니다: {template_path}", flush=True)
        return None
    
    # 원본 템플릿 로드
    template = load_json(template_path)
    
    # 처리할 모든 지표 수집
    all_metrics = []
    for theme in template.get('themes', []):
        for subtheme in theme.get('subthemes', []):
            for metric in subtheme.get('metrics', []):
                all_metrics.append((theme, subtheme, metric))
    
    total_metrics = len(all_metrics)
    print(f"\n=== {ticker_symbol.upper()} {perspective.upper()} 분석 시작 ({total_metrics}개 지표) ===\n", flush=True)
    
    # 병렬 처리를 위한 작업 준비
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_metric = {}
        
        for theme, subtheme, metric in all_metrics:
            future = executor.submit(
                process_metric, ticker_symbol, metric, perspective
            )
            future_to_metric[future] = (theme, subtheme, metric)
        
        # 결과 수집 및 템플릿 업데이트
        completed = 0
        for future in as_completed(future_to_metric):
            theme, subtheme, metric = future_to_metric[future]
            
            try:
                result = future.result()
                metric_name = result["metric"]
                
                # 원본 템플릿에서 해당 지표 찾아 업데이트
                for t in template.get('themes', []):
                    if t == theme:
                        for st in t.get('subthemes', []):
                            if st == subtheme:
                                for m in st.get('metrics', []):
                                    if m.get('metric') == metric_name:
                                        # commentary 항상 업데이트
                                        m['commentary'] = result["commentary"]
                                        
                                        # trendDescription이 있고 생성했다면 업데이트
                                        if 'trendDescription' in m and 'trendDescription' in result:
                                            m['trendDescription'] = result["trendDescription"]
                
                completed += 1
                print(f"진행: {completed}/{total_metrics} 완료 ({metric_name})", flush=True)
                
            except Exception as e:
                print(f"오류: {metric_name} 처리 중 실패: {e}", flush=True)
    
    # 결과 저장
    output_path = GROUNDS_DIR / ticker_symbol / f"{ticker_symbol}_{perspective}_template.json"
    save_json(template, output_path)
    
    print(f"\n=== {ticker_symbol.upper()} {perspective.upper()} 분석 완료 ===", flush=True)
    return output_path

def main():
    """메인 함수"""
    if len(sys.argv) < 2:
        print("사용법: python fill_commentary.py [티커심볼]")
        sys.exit(1)
    
    ticker_symbol = sys.argv[1]
    
    print(f"'{ticker_symbol}' 주식에 대한 Pro/Con 해설 생성 시작", flush=True)
    
    # 긍정적 관점 템플릿 생성
    pros_path = create_perspective_template(ticker_symbol, "positive")
    
    # 부정적 관점 템플릿 생성
    cons_path = create_perspective_template(ticker_symbol, "negative")
    
    if pros_path and cons_path:
        print(f"\n처리 완료!", flush=True)
        print(f"긍정적 분석: {pros_path}", flush=True)
        print(f"부정적 분석: {cons_path}", flush=True)

if __name__ == "__main__":
    main()