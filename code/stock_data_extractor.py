# 필요한 라이브러리 임포트
import pandas as pd
import json
import os
import sys
import time
import matplotlib.pyplot as plt
import matplotlib as mpl
from IPython.display import display, HTML
import yahooquery as yq
from yahooquery import Ticker
from datetime import datetime, timedelta

def retry_function(func, *args, method_name="", max_attempts=3, **kwargs):
    """
    지정된 함수를 최대 시도 횟수만큼 재시도하는 함수
    
    Args:
        func: 재시도할 함수
        *args: 함수에 전달할 위치 인자
        method_name: 현재 시도하는 메서드 이름 (로깅용)
        max_attempts: 최대 시도 횟수
        **kwargs: 함수에 전달할 키워드 인자
        
    Returns:
        함수 실행 결과
        
    Raises:
        Exception: 최대 시도 횟수를 초과해도 성공하지 못한 경우
    """
    attempt = 1
    last_exception = None
    
    while attempt <= max_attempts:
        try:
            if method_name:
                print(f"{method_name} 조회 시도 중... (시도 {attempt}/{max_attempts})", flush=True)
            result = func(*args, **kwargs)
            if method_name:
                print(f"{method_name} 조회 성공!", flush=True)
            return result
        except Exception as e:
            last_exception = e
            if method_name:
                print(f"{method_name} 조회 실패 (시도 {attempt}/{max_attempts}): {e}", flush=True)
            if attempt == max_attempts:
                break
            attempt += 1
            # 재시도 전 잠시 대기
            time.sleep(2)
    
    # 최대 시도 횟수 초과
    raise last_exception

def save_to_json(data, ticker_symbol, method_name):
    """
    데이터를 JSON 형식으로 저장하고 통합 파일에도 추가하는 함수
    
    Args:
        data: 저장할 데이터
        ticker_symbol: 주식 티커 심볼
        method_name: 호출된 메서드 이름
    """
    # 폴더 경로 생성
    folder_path = f"../stock_data/raw/{ticker_symbol.lower()}"
    # 폴더가 없으면 생성
    os.makedirs(folder_path, exist_ok=True)
    
    # 개별 파일 경로 생성
    file_path = f"{folder_path}/{method_name}.json"
    
    # 통합 파일 경로 생성
    consolidated_file_path = f"{folder_path}/_consolidated.json"
    
    # DataFrame인 경우 처리
    if isinstance(data, pd.DataFrame):
        data = data.to_dict(orient='records')
    
    # 개별 JSON 파일 저장
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4, default=str)
    
    # 통합 JSON 파일 업데이트
    consolidated_data = {}
    
    # 기존 통합 파일이 있으면 읽어옴
    if os.path.exists(consolidated_file_path):
        try:
            with open(consolidated_file_path, 'r', encoding='utf-8') as f:
                consolidated_data = json.load(f)
        except json.JSONDecodeError:
            print(f"통합 파일 읽기 오류, 새로 생성합니다: {consolidated_file_path}", flush=True)
            consolidated_data = {}
    
    # 현재 데이터를 통합 파일에 추가/업데이트
    consolidated_data[method_name] = data
    
    # 통합 파일 저장
    with open(consolidated_file_path, 'w', encoding='utf-8') as f:
        json.dump(consolidated_data, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"{method_name} 데이터가 {file_path}에 저장되었습니다.", flush=True)
    print(f"통합 파일 {consolidated_file_path}가 업데이트되었습니다.", flush=True)

def extract_stock_data(ticker_symbol):
    """
    주어진 티커 심볼에 대한 모든 주식 데이터를 추출하고 JSON으로 저장하는 함수
    
    Args:
        ticker_symbol: 주식 티커 심볼 (예: AAPL, MSFT)
    """
    print(f"{ticker_symbol} 데이터 추출 시작...", flush=True)
    
    # 티커 객체 생성 - 최대 3번 재시도
    max_attempts = 3
    attempt = 1
    ticker = None
    
    while attempt <= max_attempts:
        try:
            print(f"티커 객체 생성 시도 중... (시도 {attempt}/{max_attempts})", flush=True)
            ticker = Ticker(ticker_symbol.lower())
            
            # 티커가 제대로 생성되었는지 더 엄밀하게 검증
            print(f"티커 객체 생성됨, 유효성 검증 중...", flush=True)
            
            # 1. 심볼 리스트 확인
            symbols = ticker.symbols
            if not symbols or len(symbols) == 0:
                raise ValueError(f"티커 '{ticker_symbol}'에 대한 심볼을 찾을 수 없습니다.")
            
            # 2. 요청한 심볼이 실제로 포함되어 있는지 확인
            ticker_upper = ticker_symbol.upper()
            if ticker_upper not in symbols:
                raise ValueError(f"요청한 심볼 '{ticker_upper}'이 결과에 포함되지 않았습니다. 사용 가능한 심볼: {symbols}")
            
            # 3. 기본 데이터에 접근해서 실제로 데이터가 있는지 확인
            try:
                price_data = ticker.price
                if not price_data or ticker_upper not in price_data:
                    raise ValueError(f"티커 '{ticker_symbol}'의 가격 정보를 가져올 수 없습니다.")
                
                # 기본적인 가격 정보가 있는지 확인
                ticker_price_info = price_data[ticker_upper]
                if not ticker_price_info or 'regularMarketPrice' not in ticker_price_info:
                    raise ValueError(f"티커 '{ticker_symbol}'의 시장 가격 정보가 누락되었습니다.")
                
                print(f"티커 객체 검증 성공! 현재 가격: ${ticker_price_info.get('regularMarketPrice', 'N/A')}", flush=True)
                
            except Exception as validation_error:
                raise ValueError(f"티커 데이터 검증 실패: {validation_error}")
            
            print(f"티커 객체 생성 및 검증 완료!", flush=True)
            break
            
        except Exception as e:
            print(f"티커 객체 생성/검증 실패 (시도 {attempt}/{max_attempts}): {e}", flush=True)
            if attempt == max_attempts:
                print(f"최대 시도 횟수({max_attempts}회)를 초과했습니다. 프로그램을 종료합니다.", flush=True)
                sys.exit(1)
            attempt += 1
            # 재시도 전 잠시 대기 (점진적 증가)
            wait_time = 2 * attempt
            print(f"{wait_time}초 대기 후 재시도합니다...", flush=True)
            time.sleep(wait_time)
    
    # 티커 객체가 없으면 종료 (위에서 이미 처리되긴 함)
    if ticker is None:
        print("티커 객체 생성에 실패했습니다. 프로그램을 종료합니다.", flush=True)
        sys.exit(1)
    
    # 최종 검증: 데이터 추출 전 한 번 더 확인
    try:
        final_symbols = ticker.symbols
        if not final_symbols or ticker_symbol.upper() not in final_symbols:
            print(f"최종 검증 실패: 티커 '{ticker_symbol}' 심볼이 유효하지 않습니다.", flush=True)
            sys.exit(1)
        print(f"최종 검증 완료. 데이터 추출을 시작합니다...", flush=True)
    except Exception as e:
        print(f"최종 검증 중 오류 발생: {e}", flush=True)
        sys.exit(1)
    
    # 1.1 자산 프로필 (회사 정보)
    # 회사의 기본 정보, 사업 개요, 주소, 경영진, 산업 분류 등의 상세 정보를 제공
    try:
        asset_profile = retry_function(lambda: ticker.asset_profile, method_name="자산 프로필")
        save_to_json(asset_profile, ticker_symbol, "asset_profile")
    except Exception as e:
        print(f"자산 프로필 조회 최종 실패: {e}", flush=True)

    # 1.2 요약 정보
    # 주가, 시가총액, 거래량, 52주 최고/최저가 등 주식의 기본적인 시장 데이터를 제공
    try:
        summary_detail = retry_function(lambda: ticker.summary_detail, method_name="요약 정보")
        save_to_json(summary_detail, ticker_symbol, "summary_detail")
    except Exception as e:
        print(f"요약 정보 조회 최종 실패: {e}", flush=True)

    # 1.3 핵심 통계 정보
    # PER(주가수익비율), PBR(주가순자산비율), 베타, EPS 등 주요 투자 지표를 제공
    try:
        key_stats = retry_function(lambda: ticker.key_stats, method_name="핵심 통계 정보")
        save_to_json(key_stats, ticker_symbol, "key_stats")
    except Exception as e:
        print(f"핵심 통계 정보 조회 최종 실패: {e}", flush=True)

    # 1.4 가격 정보
    # 현재 주가, 장중 가격 변동, 시가/종가 정보 등 실시간에 가까운 가격 정보를 제공
    try:
        price = retry_function(lambda: ticker.price, method_name="가격 정보")
        save_to_json(price, ticker_symbol, "price")
    except Exception as e:
        print(f"가격 정보 조회 최종 실패: {e}", flush=True)
    
    # 2.1 재무 데이터
    # 주요 재무 지표, 현금 흐름, 수익, 부채 비율 등을 요약한 주요 재무 정보를 제공
    try:
        financial_data = retry_function(lambda: ticker.financial_data, method_name="재무 데이터")
        save_to_json(financial_data, ticker_symbol, "financial_data")
    except Exception as e:
        print(f"재무 데이터 조회 최종 실패: {e}")

    # 2.2 손익 계산서
    # 회사의 수익, 비용, 순이익 등 재무 성과를 나타내는 분기별/연간 손익계산서 정보를 제공
    try:
        income_statement_quarter = retry_function(
            ticker.income_statement, frequency='q', method_name="손익 계산서(분기)"
        )
        income_statement_yearly = retry_function(
            ticker.income_statement, frequency='a', method_name="손익 계산서(연간)"
        )
        print("손익 계산서 조회 성공", flush=True)
        save_to_json(income_statement_quarter, ticker_symbol, "income_statement_quarter")
        save_to_json(income_statement_yearly, ticker_symbol, "income_statement_yearly")
    except Exception as e:
        print(f"손익 계산서 조회 실패: {e}", flush=True)

    # 2.3 대차대조표
    # 자산, 부채, 자본 등 회사의 재무 상태를 나타내는 분기별/연간 대차대조표 정보를 제공
    try:
        balance_sheet_quarter = retry_function(
            ticker.balance_sheet, frequency='q', method_name="대차대조표(분기)"
        )
        balance_sheet_yearly = retry_function(
            ticker.balance_sheet, frequency='a', method_name="대차대조표(연간)"
        )
        print("대차대조표 조회 성공", flush=True)
        save_to_json(balance_sheet_quarter, ticker_symbol, "balance_sheet_quarter")
        save_to_json(balance_sheet_yearly, ticker_symbol, "balance_sheet_yearly")
    except Exception as e:
        print(f"대차대조표 조회 최종 실패: {e}")

    # 2.4 현금 흐름표
    # 영업/투자/재무 활동의 현금 흐름을 보여주는 분기별/연간 현금흐름표 정보를 제공
    try:
        cash_flow_quarter = retry_function(
            ticker.cash_flow, frequency='q', method_name="현금 흐름표(분기)"
        )
        cash_flow_yearly = retry_function(
            ticker.cash_flow, frequency='a', method_name="현금 흐름표(연간)"
        )
        print("현금 흐름표 조회 성공", flush=True)
        save_to_json(cash_flow_quarter, ticker_symbol, "cash_flow_quarter")
        save_to_json(cash_flow_yearly, ticker_symbol, "cash_flow_yearly")
    except Exception as e:
        print(f"현금 흐름표 조회 최종 실패: {e}")
    
    # 3.1 주가 히스토리 (long_term)
    try:
        history_long_term = retry_function(
            ticker.history, period="max", interval="3mo", method_name="주가 히스토리(장기)"
        ) # 최대기간, 1분기당
        print("전체 기간 분기별 주가 히스토리 조회 성공", flush=True)
        save_to_json(history_long_term, ticker_symbol, "history_long_term")
    except Exception as e:
        print(f"주가 히스토리 (long_term) 조회 최종 실패: {e}")
    
    # 3.2 주가 히스토리 (middle_term)
    try:
        history_middle_term = retry_function(
            ticker.history, period="5y", interval="1wk", method_name="주가 히스토리(중기)"
        ) # 5년, 1주당
        print("5년 주가 1주별 주가 히스토리 조회 성공", flush=True)
        save_to_json(history_middle_term, ticker_symbol, "history_middle_term")
    except Exception as e:
        print(f"주가 히스토리 (middle_term) 조회 최종 실패: {e}")
    
    # 3.3 주가 히스토리 (short_term)
    try:
        history_short_term = retry_function(
            ticker.history, period="1y", interval="1d", method_name="주가 히스토리(단기)"
        ) # 1년, 1일당
        print("1년 주가 1일별 주가 히스토리 조회 성공", flush=True)
        save_to_json(history_short_term, ticker_symbol, "history_short_term")
    except Exception as e:
        print(f"주가 히스토리 (short_term) 조회 최종 실패: {e}")
    
    # 4.1 분석가 추천 트렌드
    # 증권사 분석가들의 '매수/보유/매도' 추천 분포 및 트렌드를 보여주는 정보를 제공
    try:
        recommendation_trend = retry_function(
            lambda: ticker.recommendation_trend, method_name="분석가 추천 트렌드"
        )
        print("분석가 추천 트렌드 조회 성공", flush=True)
        save_to_json(recommendation_trend, ticker_symbol, "recommendation_trend")
    except Exception as e:
        print(f"분석가 추천 트렌드 조회 최종 실패: {e}")
    
    # 4.2 실적 트렌드
    # 분석가의 EPS(주당순이익) 예측치와 실제 발표된 실적의 트렌드를 제공
    try:
        earnings_trend = retry_function(
            lambda: ticker.earnings_trend, method_name="실적 트렌드"
        )
        print("실적 트렌드 조회 성공", flush=True)
        save_to_json(earnings_trend, ticker_symbol, "earnings_trend")
    except Exception as e:
        print(f"실적 트렌드 조회 최종 실패: {e}")
    
    # 4.3 실적 이력
    # 과거 분기별/연간 실적 발표 결과와 분석가 예상치 비교 정보를 제공
    try:
        earning_history = retry_function(
            lambda: ticker.earning_history, method_name="실적 이력"
        )
        print("실적 이력 조회 성공", flush=True)
        save_to_json(earning_history, ticker_symbol, "earning_history")
    except Exception as e:
        print(f"실적 이력 조회 최종 실패: {e}")
    
    # 5.1 주요 주주 정보
    # 기관 투자자와 일반 투자자들의 주식 보유 비율 등 주요 주주 현황 정보를 제공
    try:
        major_holders = retry_function(
            lambda: ticker.major_holders, method_name="주요 주주 정보"
        )
        print("주요 주주 정보 조회 성공", flush=True)
        save_to_json(major_holders, ticker_symbol, "major_holders")
    except Exception as e:
        print(f"주요 주주 정보 조회 최종 실패: {e}")

    # 5.2 기관 소유 현황
    # 연기금, 은행, 보험사 등 기관 투자자들의 보유 현황과 변동 내역 정보를 제공
    try:
        institution_ownership = retry_function(
            lambda: ticker.institution_ownership, method_name="기관 소유 현황"
        )
        print("기관 소유 현황 조회 성공", flush=True)
        save_to_json(institution_ownership, ticker_symbol, "institution_ownership")
    except Exception as e:
        print(f"기관 소유 현황 조회 최종 실패: {e}")
    
    # 5.3 내부자 거래
    # 임원, 이사 등 회사 내부자들의 주식 매매 내역 정보를 제공
    try:
        insider_transactions = retry_function(
            lambda: ticker.insider_transactions, method_name="내부자 거래"
        )
        print("내부자 거래 조회 성공", flush=True)
        save_to_json(insider_transactions, ticker_symbol, "insider_transactions")
    except Exception as e:
        print(f"내부자 거래 조회 최종 실패: {e}")
    
    # 5.4 내부자 보유 현황
    # 경영진, 이사 등 내부자들의 주식 보유 현황 정보를 제공
    try:
        insider_holders = retry_function(
            lambda: ticker.insider_holders, method_name="내부자 보유 현황"
        )
        print("내부자 보유 현황 조회 성공", flush=True)
        save_to_json(insider_holders, ticker_symbol, "insider_holders")
    except Exception as e:
        print(f"내부자 보유 현황 조회 최종 실패: {e}")
    
    # 6.1 ESG 점수
    # 환경(E), 사회(S), 지배구조(G) 관련 기업의 지속가능성 평가 점수 정보를 제공
    try:
        esg_scores = retry_function(
            lambda: ticker.esg_scores, method_name="ESG 점수"
        )
        print("ESG 점수 조회 성공", flush=True)
        save_to_json(esg_scores, ticker_symbol, "esg_scores")
    except Exception as e:
        print(f"ESG 점수 조회 최종 실패: {e}")
    
    # 7.1 옵션 만기일 목록
    # 주식 옵션 거래를 위한 만기일 목록과 콜/풋 옵션 정보를 제공
    try:
        option_chain = retry_function(
            lambda: ticker.option_chain, method_name="옵션 체인"
        )
        print("옵션 체인 조회 성공", flush=True)
        
        # 옵션 체인 기본 정보 저장
        option_chain_data = {"expiration_dates": option_chain.expiration_dates} if hasattr(option_chain, 'expiration_dates') else {}
        save_to_json(option_chain_data, ticker_symbol, "option_chain")
        
        # 만기일이 있으면 첫 번째 만기일에 대한 옵션 정보 저장
        if hasattr(option_chain, 'expiration_dates') and len(option_chain.expiration_dates) > 0:
            for expiry in option_chain.expiration_dates[:3]:  # 처음 3개 만기일만 저장
                try:
                    calls = retry_function(
                        option_chain.calls, expiry, method_name=f"옵션 콜({expiry})"
                    )
                    save_to_json(calls, ticker_symbol, f"option_calls_{expiry}")
                except Exception as e:
                    print(f"옵션 콜({expiry}) 조회 최종 실패: {e}")
                
                try:
                    puts = retry_function(
                        option_chain.puts, expiry, method_name=f"옵션 풋({expiry})"
                    )
                    save_to_json(puts, ticker_symbol, f"option_puts_{expiry}")
                except Exception as e:
                    print(f"옵션 풋({expiry}) 조회 최종 실패: {e}")
                
    except Exception as e:
        print(f"옵션 체인 조회 최종 실패: {e}")
    
    # 8.1 뉴스 (corporate_events)
    # 기업의 주요 이벤트(실적 발표, 배당 일정 등) 정보를 제공
    try:
        corporate_events = retry_function(
            lambda: ticker.corporate_events, method_name="기업 이벤트"
        )
        print("corporate_events 조회 성공", flush=True)
        save_to_json(corporate_events, ticker_symbol, "corporate_events")
    except Exception as e:
        print(f"corporate_events 조회 최종 실패: {e}")
    
    # 8.2 뉴스 (news) (에러로 인한 주석처리)
    # 해당 기업에 관한 최신 뉴스 기사 목록을 제공
    # try:
    #     today = datetime.now()
    #     three_months_ago = today - timedelta(days=90)
    #     start_date = three_months_ago.strftime('%Y-%m-%d')
    #     news = retry_function(
    #         ticker.news, count=10, start=start_date, method_name="뉴스"
    #     )  # 최신 뉴스 10개 조회, 1분기 전부터 시작
    #     print(f"news 조회 성공 (시작일: {start_date})")
    #     save_to_json(news, ticker_symbol, "news")
    # except Exception as e:
    #     print(f"news 조회 최종 실패: {e}")
    
    # 8.3 뉴스 (quotes)
    # 현재 주가 견적 및 관련된 시장 정보를 제공
    try:
        quotes = retry_function(
            lambda: ticker.quotes, method_name="주가 견적"
        )
        print("quotes 조회 성공", flush=True)
        save_to_json(quotes, ticker_symbol, "quotes")
    except Exception as e:
        print(f"quotes 조회 최종 실패: {e}")    
    
    # 9. SEC 파일링
    # 미국 증권거래위원회(SEC)에 제출된 공시 보고서 목록 정보를 제공
    try:
        sec_filings = retry_function(
            lambda: ticker.sec_filings, method_name="SEC 파일링"
        )
        print("SEC 파일링 조회 성공", flush=True)
        save_to_json(sec_filings, ticker_symbol, "sec_filings")
    except Exception as e:
        print(f"SEC 파일링 조회 최종 실패: {e}")
    
    # 10.1 전체 재무 데이터 조회
    # 모든 재무제표 관련 데이터를 하나의 큰 데이터프레임으로 통합하여 제공
    try:
        all_financial_data_annual = retry_function(
            ticker.all_financial_data, method_name="전체 재무 데이터(연간)"
        )
        print("전체 재무 데이터(연간) 조회 성공", flush=True)
        all_financial_data_quarterly = retry_function(
            ticker.all_financial_data, frequency='q', method_name="전체 재무 데이터(분기)"
        )
        print("전체 재무 데이터(분기) 조회 성공", flush=True)
        save_to_json(all_financial_data_annual, ticker_symbol, "all_financial_data_annual")
        save_to_json(all_financial_data_quarterly, ticker_symbol, "all_financial_data_quarterly")
    except Exception as e:
        print(f"전체 재무 데이터 조회 최종 실패: {e}")

    # 11.1 기술적 인사이트
    # 주가 차트 분석에 사용되는 기술적 지표 및 패턴 분석 정보를 제공
    try:
        technical_insights = retry_function(
            lambda: ticker.technical_insights, method_name="기술적 인사이트"
        )
        print("기술적 인사이트 조회 성공", flush=True)
        save_to_json(technical_insights, ticker_symbol, "technical_insights")
    except Exception as e:
        print(f"기술적 인사이트 조회 최종 실패: {e}")

    # 11.2 평가 지표
    # PER, EV/EBITDA 등 기업가치 평가에 사용되는 다양한 지표들의 히스토리 정보를 제공
    try:
        valuation_measures = retry_function(
            lambda: ticker.valuation_measures, method_name="평가 지표"
        )
        print("평가 지표 조회 성공", flush=True)
        save_to_json(valuation_measures, ticker_symbol, "valuation_measures")
    except Exception as e:
        print(f"평가 지표 조회 최종 실패: {e}")
    
    # 12.1 그레이딩 히스토리
    # 증권사들의 투자의견 변경 이력을 제공하여 시장 전문가들의 기업 평가 추이를 파악 가능
    try:
        grading_history = retry_function(
            lambda: ticker.grading_history, method_name="그레이딩 히스토리"
        )
        print("그레이딩 히스토리 조회 성공", flush=True)
        save_to_json(grading_history, ticker_symbol, "grading_history")
    except Exception as e:
        print(f"그레이딩 히스토리 조회 최종 실패: {e}")

    # 13.1 시장 요약
    # 주요 지수 및 시장 전체 동향에 관한 요약 정보를 제공
    try:
        market_summary = retry_function(
            yq.get_market_summary, method_name="시장 요약"
        )
        print("시장 요약 조회 성공", flush=True)
        save_to_json(market_summary, ticker_symbol, "market_summary")
    except Exception as e:
        print(f"시장 요약 조회 최종 실패: {e}")

    # 확인 메시지 출력
    consolidated_file_path = f"../stock_data/{ticker_symbol.lower()}/_consolidated.json"
    if os.path.exists(consolidated_file_path):
        file_size_mb = os.path.getsize(consolidated_file_path) / (1024 * 1024)
        print(f"\n통합 파일 생성 완료: {consolidated_file_path}", flush=True)
        print(f"통합 파일 크기: {file_size_mb:.2f} MB", flush=True)
    
    print(f"{ticker_symbol} 데이터 추출 완료!", flush=True)

if __name__ == "__main__":
    # 명령줄 인자로 티커 심볼을 받음
    if len(sys.argv) < 2:
        print("사용법: python stock_data_extractor.py [티커심볼]")
        print("예시: python stock_data_extractor.py AAPL")
        sys.exit(1)
    
    # 티커 심볼 받아오기
    ticker_symbol = sys.argv[1].upper()
    extract_stock_data(ticker_symbol)
