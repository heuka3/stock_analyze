import json
import re
import os
import sys
from pathlib import Path

def load_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_nested(data, path, ticker_symbol=None):
    """Fetch nested data using dot notation and list indices."""
    # .ts.를 티커 심볼로 대체
    if ticker_symbol and '.ts.' in path:
        path = path.replace('.ts.', f'.{ticker_symbol}.')
    
    parts = re.split(r'\.(?![^\[]*\])', path)
    for part in parts:
        m = re.match(r'(.+)\[(-?\d+)\]$', part)
        if m:
            key, idx = m.group(1), int(m.group(2))
            data = data[key][idx]
        else:
            data = data[part]
    return data

def replace_ts_in_dict(data, ticker_symbol):
    """재귀적으로 딕셔너리나 리스트를 순회하면서 문자열 값에서 '.ts.'를 티커심볼로 대체"""
    if isinstance(data, dict):
        for key, value in list(data.items()):
            if isinstance(value, (dict, list)):
                replace_ts_in_dict(value, ticker_symbol)
            elif isinstance(value, str) and '.ts.' in value:
                data[key] = value.replace('.ts.', f'.{ticker_symbol}.')
    elif isinstance(data, list):
        for i, item in enumerate(data):
            if isinstance(item, (dict, list)):
                replace_ts_in_dict(item, ticker_symbol)
            elif isinstance(item, str) and '.ts.' in item:
                data[i] = item.replace('.ts.', f'.{ticker_symbol}.')
    return data

def fill_template(ticker_symbol):
    ticker_symbol = ticker_symbol.lower()
    template_path = f"../resources/template.json"
    consolidated_path = f"../stock_data/raw/{ticker_symbol}/_consolidated.json"
    output_dir = f"../grounds/{ticker_symbol}"
    output_path = f"{output_dir}/{ticker_symbol}_template.json"
    os.makedirs(output_dir, exist_ok=True)

    template = load_json(template_path)
    consolidated = load_json(consolidated_path)
    
    # 템플릿의 meta 섹션 업데이트
    template['meta']['ticker'] = ticker_symbol.upper()
    
    # 템플릿에서 모든 '.ts.' 문자열을 티커 심볼로 대체
    template = replace_ts_in_dict(template, ticker_symbol)

    # 편의용: flattened namespace
    ns = dict(consolidated)  # 원본 데이터 사본 생성

    for theme in template.get('themes', []):
        for sub in theme.get('subthemes', []):
            for metric in sub.get('metrics', []):

                # 기존 field 처리
                if 'field' in metric:
                    try:
                        value = get_nested(consolidated, metric['field'], ticker_symbol)
                    except Exception:
                        value = None
                    metric['value'] = value
                    if 'latestValue' in metric:
                        metric['latestValue'] = value

                # formula 고정 분기 처리
                elif 'formula' in metric:
                    name = metric['metric']
                    try:
                        if name == "Return on Invested Capital (ROIC)":
                            a = ns['all_financial_data_annual'][-1]  # 배열의 마지막 항목
                            if isinstance(a, dict):
                                value = a['EBIT'] * (1 - a['TaxRateForCalcs']) / a['InvestedCapital']
                            else:
                                value = None

                        elif name == "Net Debt":
                            fd = ns['financial_data'][ticker_symbol]  # 티커 심볼로 동적 접근
                            value = fd['totalDebt'] - fd['totalCash']

                        elif name == "Interest Coverage":
                            a = ns['all_financial_data_annual'][-1]
                            if isinstance(a, dict):
                                value = a['EBIT'] / a['InterestExpense']
                            else:
                                value = None

                        elif name == "Net Debt / EBITDA":
                            a = ns['all_financial_data_annual'][-1]
                            if isinstance(a, dict):
                                value = a['NetDebt'] / a['EBITDA']
                            else:
                                value = None

                        elif name == "5-Year Revenue CAGR": #현재 계산 잘 안되는 중. 중간에 데이터 비어있어서 그런 듯.
                            arr = ns['all_financial_data_annual']
                            # 데이터가 충분히 있는지 확인 (최소 5년치 데이터가 필요)
                            if len(arr) >= 5:
                                # 마지막 항목과 5년 전 항목 가져오기
                                current_data = arr[-1]
                                five_years_ago_data = arr[-5]
                                
                                # 데이터 유효성 검사 및 계산
                                if (isinstance(current_data, dict) and isinstance(five_years_ago_data, dict) and
                                    'TotalRevenue' in current_data and 'TotalRevenue' in five_years_ago_data and
                                    five_years_ago_data['TotalRevenue'] is not None and five_years_ago_data['TotalRevenue'] > 0):
                                    value = ((current_data['TotalRevenue'] / five_years_ago_data['TotalRevenue']) ** (1/4) - 1)
                                else:
                                    value = None
                            else:
                                value = None

                        elif name == "3-Year Revenue CAGR":
                            arr = ns['all_financial_data_annual']
                            if len(arr) >= 4 and isinstance(arr[-1], dict) and isinstance(arr[-4], dict):
                                value = ((arr[-1]['TotalRevenue'] / arr[-4]['TotalRevenue'])**(1/3) - 1)
                            else:
                                value = None

                        elif name == "FCF Margin":
                            fd = ns['financial_data'][ticker_symbol]
                            value = fd['freeCashflow'] / fd['operatingCashflow']

                        elif name == "FCF Conversion (FCF/NI)":
                            a = ns['all_financial_data_annual'][-1]
                            if isinstance(a, dict):
                                value = a['FreeCashFlow'] / a['NetIncome']
                            else:
                                value = None

                        elif name == "EV/FCF":
                            a = ns['all_financial_data_annual'][-1]
                            if isinstance(a, dict):
                                value = a['EnterpriseValue'] / a['FreeCashFlow']
                            else:
                                value = None

                        elif name == "Upside to Target":
                            fd = ns['financial_data'][ticker_symbol]
                            value = (fd['targetMeanPrice'] - fd['currentPrice']) / fd['currentPrice']

                        elif name == "Insider Buys":
                            cnt = 0
                            for tx in ns.get('insider_transactions', []):
                                if 'Purchase' in tx.get('transactionText', ''):
                                    cnt += 1
                            value = cnt

                        elif name == "Insider Sells":
                            cnt = 0
                            for tx in ns.get('insider_transactions', []):
                                if 'Sale' in tx.get('transactionText', ''):
                                    cnt += 1
                            value = cnt

                        elif name == "Share Buyback Change (YoY)":
                            arr = ns['all_financial_data_annual']
                            if len(arr) >= 2 and isinstance(arr[-1], dict) and isinstance(arr[-2], dict):
                                prev = arr[-2].get('RepurchaseOfCapitalStock')
                                curr = arr[-1].get('RepurchaseOfCapitalStock')
                                if prev not in (0, None) and curr is not None:
                                    value = (curr - prev) / abs(prev)
                                else:
                                    value = None
                            else:
                                value = None

                        elif name == "Analyst Buy %":
                            if 'recommendation_trend' in ns and len(ns['recommendation_trend']) > 0:
                                rt = ns['recommendation_trend'][0]
                                if isinstance(rt, dict):
                                    # 딕셔너리에서 숫자 값만 합산
                                    total = sum(v for k, v in rt.items() if isinstance(v, (int, float)))
                                    if total > 0:
                                        value = (rt.get('strongBuy', 0) + rt.get('buy', 0)) / total
                                    else:
                                        value = None
                                else:
                                    value = None
                            else:
                                value = None

                        elif name == "Price vs 50-Day MA":
                            fd = ns['financial_data'][ticker_symbol]
                            sd = ns['summary_detail'][ticker_symbol]
                            value = (fd['currentPrice'] - sd['fiftyDayAverage']) / sd['fiftyDayAverage']

                        elif name == "Price vs 200-Day MA":
                            fd = ns['financial_data'][ticker_symbol]
                            sd = ns['summary_detail'][ticker_symbol]
                            value = (fd['currentPrice'] - sd['twoHundredDayAverage']) / sd['twoHundredDayAverage']

                        elif name == "Price vs 52-Week High":
                            fd = ns['financial_data'][ticker_symbol]
                            sd = ns['summary_detail'][ticker_symbol]
                            value = (fd['currentPrice'] - sd['fiftyTwoWeekHigh']) / sd['fiftyTwoWeekHigh']

                        else:
                            value = None

                    except Exception:
                        value = None

                    metric['value'] = value
                    if 'latestValue' in metric:
                        metric['latestValue'] = value

    # 결과 저장
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(template, f, ensure_ascii=False, indent=2)

    print(f"템플릿이 {output_path}에 성공적으로 저장되었습니다.")
    return output_path

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("사용법: python fill_template.py [티커심볼]")
        sys.exit(1)
    fill_template(sys.argv[1])
