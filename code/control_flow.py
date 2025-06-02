#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import subprocess
import concurrent.futures
from pathlib import Path
from typing import Dict, Tuple, Optional
import time
import threading
import queue
import glob

# OpenAI API 관련 임포트
from openai import OpenAI
from dotenv import load_dotenv

# 현재 파일의 디렉토리를 기준으로 경로 설정
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
ENV_FILE = PROJECT_ROOT / "resources" / ".env"

# 환경 변수 로드
load_dotenv(ENV_FILE)

# OpenAI 클라이언트 초기화
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("❌ OPENAI_API_KEY가 설정되지 않았습니다. .env 파일을 확인해주세요.")
    sys.exit(1)

client = OpenAI(api_key=OPENAI_API_KEY)

# 디렉토리 경로 설정
DIALOGUE_DIR = PROJECT_ROOT / "dialogue"
SPEAKING_DIR = PROJECT_ROOT / "speaking"
STOCK_DATA_RAW_DIR = PROJECT_ROOT / "stock_data" / "raw"
STOCK_DATA_REFINED_DIR = PROJECT_ROOT / "stock_data" / "refined"

# 정제해야 할 파일 목록 (stock_data_refiner.py의 설정과 동일)
NON_TIMESERIES_FILES = {
    "asset_profile", "esg_scores", "financial_data", "insider_holders",
    "institution_ownership", "key_stats", "major_holders", "market_summary",
    "option_chain", "price", "quotes", "summary_detail", "technical_insights"
}

TIMESERIES_FILES = {
    "history_long_term", "history_middle_term", "history_short_term",
    "income_statement_quarter", "income_statement_yearly", "balance_sheet_quarter",
    "balance_sheet_yearly", "cash_flow_quarter", "cash_flow_yearly",
    "all_financial_data_quarterly", "all_financial_data_annual", "recommendation_trend",
    "earnings_trend", "earning_history", "grading_history", "valuation_measures",
    "insider_transactions", "corporate_events", "sec_filings"
}

ALL_REFINE_FILES = NON_TIMESERIES_FILES | TIMESERIES_FILES

# generate_dialogue.py에서 DIALOGUE_FLOW 가져오기
from generate_dialogue import DIALOGUE_FLOW


def run_subprocess_with_output(cmd: list, cwd: Path, prefix: str = "") -> subprocess.CompletedProcess:
    """실시간 출력을 보여주는 subprocess 실행 (개선된 버퍼링 처리)"""
    
    def read_output(pipe, prefix, output_queue):
        """출력을 읽어서 큐에 넣는 함수 (실시간 처리)"""
        try:
            for line in iter(pipe.readline, ''):
                if line.strip():
                    output_queue.put(f"{prefix}{line.rstrip()}")
                # 빈 줄도 처리하여 버퍼 플러시 효과
                elif line == '\n':
                    output_queue.put(f"{prefix}.")  # 진행 표시
            pipe.close()
        except Exception as e:
            output_queue.put(f"{prefix}[ERROR] {e}")
    
    # 환경 변수 설정으로 Python 출력 버퍼링 비활성화
    env = os.environ.copy()
    env['PYTHONUNBUFFERED'] = '1'
    env['PYTHONIOENCODING'] = 'utf-8'
    
    # 프로세스 시작 (버퍼링 없음)
    process = subprocess.Popen(
        cmd, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE, 
        text=True, 
        cwd=cwd,
        bufsize=0,  # 버퍼링 완전 비활성화
        universal_newlines=True,
        env=env  # 환경 변수 적용
    )
    
    # 출력 큐 생성
    output_queue = queue.Queue()
    
    # stdout과 stderr를 읽는 스레드 시작
    stdout_thread = threading.Thread(
        target=read_output, 
        args=(process.stdout, prefix, output_queue)
    )
    stderr_thread = threading.Thread(
        target=read_output, 
        args=(process.stderr, f"{prefix}[ERR] ", output_queue)
    )
    
    stdout_thread.daemon = True
    stderr_thread.daemon = True
    stdout_thread.start()
    stderr_thread.start()
    
    # 실시간 출력 표시 (더 짧은 타임아웃)
    last_output_time = time.time()
    while process.poll() is None or not output_queue.empty():
        try:
            line = output_queue.get(timeout=0.05)  # 더 짧은 타임아웃
            print(line, flush=True)
            last_output_time = time.time()
        except queue.Empty:
            # 5초 이상 출력이 없으면 진행 상황 표시
            current_time = time.time()
            if current_time - last_output_time > 5.0:
                print(f"{prefix}⏳ 처리 중... (응답 대기)", flush=True)
                last_output_time = current_time
            continue
    
    # 스레드가 완료될 때까지 대기
    stdout_thread.join(timeout=2.0)
    stderr_thread.join(timeout=2.0)
    
    # 남은 출력 처리
    while not output_queue.empty():
        try:
            line = output_queue.get_nowait()
            print(line, flush=True)
        except queue.Empty:
            break
    
    returncode = process.wait()
    
    # CompletedProcess와 유사한 객체 반환
    class ProcessResult:
        def __init__(self, returncode):
            self.returncode = returncode
            self.stdout = ""
            self.stderr = ""
    
    return ProcessResult(returncode)


def extract_company_info(user_request: str) -> Tuple[str, str]:
    """사용자 요청에서 회사명과 티커 심볼을 추출"""
    
    prompt = f"""
사용자가 주식에 대해 질문했습니다: "{user_request}"

이 질문에서 언급된 회사의 정보를 추출해주세요.

## 요구사항:
1. 정확한 회사 공식 명칭 (영어)
2. 정확한 티커 심볼 (대문자)

## 응답 형식:
반드시 다음 JSON 형식으로만 답변해주세요. 다른 설명은 포함하지 마세요. 
```json 
```
형식의 코드블럭을 사용하지 말고 JSON 객체만 반환하세요.

{{
    "company_name": "정확한 회사 공식 명칭",
    "ticker_symbol": "정확한 티커 심볼"
}}

예시:
- "애플에 대해 이야기해줘" → {{"company_name": "Apple Inc.", "ticker_symbol": "AAPL"}}
- "테슬라 주식 분석해줘" → {{"company_name": "Tesla, Inc.", "ticker_symbol": "TSLA"}}
- "구글에 대해 알려줘" → {{"company_name": "Alphabet Inc.", "ticker_symbol": "GOOGL"}}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "당신은 정확한 회사 정보를 제공하는 전문가입니다. 반드시 JSON 형식으로만 답변하세요."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=150,
            temperature=0.1
        )
        
        result_text = response.choices[0].message.content.strip()
        
        print(f"🔍 OpenAI 응답 확인: '{result_text}'")  # 디버깅용
        
        if not result_text:
            raise Exception("OpenAI API 응답이 비어있습니다")
        
        # JSON 파싱 시도
        try:
            result = json.loads(result_text)
        except json.JSONDecodeError as json_err:
            print(f"❌ JSON 파싱 실패: {json_err}")
            print(f"📝 원본 응답: {result_text}")
        
        # JSON 파싱 성공한 경우
        if "company_name" not in result or "ticker_symbol" not in result:
            raise Exception(f"필수 필드가 없습니다: {result}")
            
        company_name = result["company_name"]
        ticker_symbol = result["ticker_symbol"].upper()
        
        print(f"✓ 회사 정보 추출 완료:")
        print(f"  - 회사명: {company_name}")
        print(f"  - 티커: {ticker_symbol}")
        
        return company_name, ticker_symbol
        
    except Exception as e:
        print(f"❌ 회사 정보 추출 실패: {e}")
        print(f"🔧 API 키 확인: {'설정됨' if OPENAI_API_KEY else '미설정'}")
        raise



def run_data_extraction(ticker_symbol: str):
    """데이터 추출"""
    
    print("  🔍 주식 데이터 추출 중...")
    result = run_subprocess_with_output(
        ["python", str(BASE_DIR / "stock_data_extractor.py"), ticker_symbol],
        cwd=BASE_DIR,
        prefix="    [데이터추출] "
    )
    
    if result.returncode == 0:
        print("  ✓ 주식 데이터 추출 완료")
    else:
        print(f"  ❌ 주식 데이터 추출 실패 (종료코드: {result.returncode})")
        raise Exception("데이터 추출 실패")




def generate_intro_and_voice(ticker_symbol: str, company_name: str) -> bool:
    """사회자 대본 생성 + 음성 생성 (직렬)"""
    
    try:
        # 1. 사회자 대본 생성
        print("    📝 사회자 대본 생성 중...")
        dialogue_result = run_subprocess_with_output(
            ["python", str(BASE_DIR / "generate_dialogue.py"),
             "--ticker", ticker_symbol,
             "--company", company_name,
             "--type", "intro"],
            cwd=BASE_DIR,
            prefix="      [대본생성] "
        )
        
        if dialogue_result.returncode != 0:
            print(f"    ❌ 사회자 대본 생성 실패 (종료코드: {dialogue_result.returncode})")
            return False
        
        print("    ✓ 사회자 대본 생성 완료")
        
        # 2. 음성 생성
        print("    🔊 사회자 음성 생성 중...")
        # 대본 파일 경로 (generate_dialogue.py가 생성할 경로)
        script_file = DIALOGUE_DIR / ticker_symbol.lower() / "intro.txt"
        
        if not script_file.exists():
            print(f"    ❌ 대본 파일을 찾을 수 없음: {script_file}")
            return False
        
        tts_result = run_subprocess_with_output(
            ["python", str(BASE_DIR / "tts.py"),
             "--input", str(script_file),
             "--output", str(SPEAKING_DIR / ticker_symbol.lower() / "intro.mp3")],
            cwd=BASE_DIR,
            prefix="      [음성생성] "
        )
        
        if tts_result.returncode != 0:
            print(f"    ❌ 음성 생성 실패 (종료코드: {tts_result.returncode})")
            return False
        
        print("    ✓ 사회자 음성 생성 완료")
        return True
        
    except Exception as e:
        print(f"    ❌ 사회자 대본/음성 생성 중 오류: {e}")
        return False


def run_data_refinement_and_template_fill(ticker_symbol: str):
    """데이터 정제와 템플릿 채우기를 병렬로 실행"""
    
    # 원시 데이터 디렉토리 확인
    raw_data_dir = STOCK_DATA_RAW_DIR / ticker_symbol.lower()
    if not raw_data_dir.exists():
        raise Exception(f"원시 데이터 디렉토리가 존재하지 않습니다: {raw_data_dir}")
    
    # 존재하는 JSON 파일 목록 확인
    existing_files = []
    for file_name in ALL_REFINE_FILES:
        json_file = raw_data_dir / f"{file_name}.json"
        if json_file.exists():
            existing_files.append(file_name)
    
    print(f"  📁 정제할 파일 수: {len(existing_files)}개")
    
    # 출력 동기화를 위한 락
    output_lock = threading.Lock()
    
    def run_refinement_with_output(file_name):
        """개별 파일 정제 (실시간 출력 포함)"""
        try:
            result = run_subprocess_with_output(
                ["python", str(BASE_DIR / "stock_data_refiner.py"), ticker_symbol, file_name],
                cwd=BASE_DIR,
                prefix=f"    [정제-{file_name}] "
            )
            
            with output_lock:
                if result.returncode == 0:
                    print(f"    ✓ {file_name}.md 생성 완료")
                else:
                    print(f"    ❌ {file_name}.md 생성 실패 (종료코드: {result.returncode})")
            
            return file_name, result.returncode
            
        except Exception as e:
            with output_lock:
                print(f"    ❌ {file_name} 정제 중 오류: {e}")
            return file_name, -1
    
    def run_template_fill_with_output():
        """템플릿 채우기 (실시간 출력 포함)"""
        try:
            result = run_subprocess_with_output(
                ["python", str(BASE_DIR / "fill_template.py"), ticker_symbol],
                cwd=BASE_DIR,
                prefix="    [템플릿] "
            )
            
            with output_lock:
                if result.returncode == 0:
                    print("  ✓ 템플릿 생성 완료")
                else:
                    print(f"  ❌ 템플릿 생성 실패 (종료코드: {result.returncode})")
            
            return result.returncode
            
        except Exception as e:
            with output_lock:
                print(f"  ❌ 템플릿 생성 중 오류: {e}")
            return -1
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # 1. 각 JSON 파일을 마크다운으로 정제 (병렬)
        refine_futures = []
        for file_name in existing_files:
            future = executor.submit(run_refinement_with_output, file_name)
            refine_futures.append(future)
        
        # 2. 템플릿 채우기 (병렬)
        template_future = executor.submit(run_template_fill_with_output)
        
        # 데이터 정제 결과 확인
        failed_files = []
        for future in refine_futures:
            file_name, returncode = future.result()
            if returncode != 0:
                failed_files.append(file_name)
        
        # 템플릿 생성 결과 확인
        template_returncode = template_future.result()
        if template_returncode != 0:
            raise Exception("템플릿 생성 실패")
        
        if failed_files:
            print(f"  ⚠️ 실패한 파일들: {failed_files}")
        
        print("  ✓ 데이터 정제 및 템플릿 생성 완료")


def run_commentary_generation(ticker_symbol: str):
    """코멘터리 생성"""
    
    print("  💬 코멘터리 생성 중...")
    result = run_subprocess_with_output(
        ["python", str(BASE_DIR / "fill_commentary.py"), ticker_symbol],
        cwd=BASE_DIR,
        prefix="    [코멘터리] "
    )
    
    if result.returncode == 0:
        print("  ✓ 코멘터리 생성 완료")
    else:
        print(f"  ❌ 코멘터리 생성 실패 (종료코드: {result.returncode})")
        raise Exception("코멘터리 생성 실패")


def run_main_flow(ticker_symbol: str, company_name: str):
    """메인 흐름: 데이터 추출 → 데이터 정제 + 템플릿 생성 → 코멘터리 생성 → 대화 생성"""
    
    try:
        # 메인 흐름 1단계: 데이터 추출
        print("\n[메인 흐름] 📊 데이터 추출 시작...")
        run_data_extraction(ticker_symbol)
        
        # 메인 흐름 2단계: 데이터 정제 + 템플릿 생성 (병렬)
        print("\n[메인 흐름] 🔄 데이터 정제 및 템플릿 생성 시작...")
        run_data_refinement_and_template_fill(ticker_symbol)
        
        # 메인 흐름 3단계: 코멘터리 생성
        print("\n[메인 흐름] 💬 코멘터리 생성 시작...")
        run_commentary_generation(ticker_symbol)
        
        # 메인 흐름 4단계: 모든 대본 생성 + TTS
        print("\n[메인 흐름] 🎬 전체 대화 시스템 생성 시작...")
        dialogue_dir = DIALOGUE_DIR / ticker_symbol.lower()
        speaking_dir = SPEAKING_DIR / ticker_symbol.lower()
        dialogue_dir.mkdir(parents=True, exist_ok=True)
        speaking_dir.mkdir(parents=True, exist_ok=True)
        
        failed_scripts = []
        
        # 모든 세그먼트와 플로우 순차 처리
        for segment_idx, segment_info in enumerate(DIALOGUE_FLOW, 1):
            print(f"\n  📍 세그먼트 {segment_idx}: {segment_info['segment']}")
            
            for flow_idx, flow_info in enumerate(segment_info['flow'], 1):
                speaker = flow_info['speaker']
                script_type = flow_info['type']
                
                # 대본 생성
                dialogue_result = run_dialogue_generation(ticker_symbol, company_name, segment_idx, flow_idx)
                
                if dialogue_result == 0:
                    # 대본 생성 성공 시 TTS 생성
                    speaker_code = "opt" if speaker == "optimistic" else "pes" if speaker == "pessimistic" else "mod"
                    type_code = "dev" if script_type == "development" else "res" if script_type == "response" else "sum"
                    script_filename = f"seg{segment_idx}_{speaker_code}_{type_code}_{flow_idx}"
                    
                    script_file_path = str(dialogue_dir / f"{script_filename}.txt")
                    audio_file_path = str(speaking_dir / f"{script_filename}.mp3")
                    
                    tts_result = run_tts_generation(script_file_path, audio_file_path)
                    
                    if tts_result != 0:
                        print(f"    ⚠️ {script_filename} TTS 생성 실패")
                else:
                    failed_scripts.append(f"seg{segment_idx}_flow{flow_idx}")
        
        if failed_scripts:
            print(f"\n  ⚠️ 실패한 대본들: {failed_scripts}")
            print("⚠️ [메인 흐름] 일부 대본 생성에 실패했지만 작업을 계속 진행합니다.")
        else:
            print("\n  ✅ 모든 대본과 음성 파일 생성 완료!")
        
        print("✅ [메인 흐름] 완료")
        return True
        
    except Exception as e:
        print(f"❌ [메인 흐름] 실패: {e}")
        return False


def run_moderator_flow(ticker_symbol: str, company_name: str):
    """서브 흐름 1: 사회자 대본/음성 생성"""
    
    try:
        # 필요한 디렉토리 생성
        dialogue_dir = DIALOGUE_DIR / ticker_symbol.lower()
        speaking_dir = SPEAKING_DIR / ticker_symbol.lower()
        dialogue_dir.mkdir(parents=True, exist_ok=True)
        speaking_dir.mkdir(parents=True, exist_ok=True)
        
        print("\n[서브 흐름 - 사회자] 🎙️ 사회자 대본/음성 생성 시작...")
        success = generate_intro_and_voice(ticker_symbol, company_name)
        
        if success:
            print("✅ [서브 흐름 - 사회자] 완료")
        else:
            print("❌ [서브 흐름 - 사회자] 실패")
        
        return success
        
    except Exception as e:
        print(f"❌ [서브 흐름 - 사회자] 오류: {e}")
        return False


def run_dialogue_generation(ticker_symbol: str, company_name: str, segment_num: int, flow_step: int):
    """단일 대화 생성 단계"""
    
    print(f"  🎬 세그먼트 {segment_num}, 플로우 {flow_step} 대화 생성 중...")
    
    result = run_subprocess_with_output(
        ["python", str(BASE_DIR / "generate_dialogue.py"), 
         "--ticker", ticker_symbol, 
         "--company", company_name, 
         "--type", "single",
         "--segment", str(segment_num),
         "--flow", str(flow_step)],
        cwd=BASE_DIR,
        prefix="    [대화생성] "
    )
    
    if result.returncode == 0:
        print(f"  ✓ 세그먼트 {segment_num}, 플로우 {flow_step} 생성 완료")
    else:
        print(f"  ❌ 세그먼트 {segment_num}, 플로우 {flow_step} 생성 실패 (종료코드: {result.returncode})")
    
    return result.returncode

def run_tts_generation(script_file_path: str, output_audio_path: str):
    """TTS 음성 생성"""
    print(f"  🔊 음성 생성 중: {output_audio_path}")
    
    result = run_subprocess_with_output(
        ["python", str(BASE_DIR / "tts.py"),
         "--input", script_file_path,
         "--output", output_audio_path],
        cwd=BASE_DIR,
        prefix="    [TTS] "
    )
    
    if result.returncode == 0:
        print(f"  ✓ 음성 생성 완료: {output_audio_path}")
    else:
        print(f"  ❌ 음성 생성 실패 (종료코드: {result.returncode})")
    
    return result.returncode

def merge_mp3_files(ticker_symbol: str) -> bool:
    """주어진 티커의 모든 MP3 파일을 DIALOGUE_FLOW 순서로 합쳐서 combined.mp3 파일 생성"""
    try:
        ticker_dir = SPEAKING_DIR / ticker_symbol.lower()
        if not ticker_dir.exists():
            print(f"❌ 음성 파일 디렉토리가 존재하지 않습니다: {ticker_dir}")
            return False
        
        # DIALOGUE_FLOW 순서로 파일 목록 생성
        audio_files = []
        
        # intro 파일 추가
        intro_files = list(ticker_dir.glob("intro.mp3"))
        if intro_files:
            audio_files.extend(sorted(intro_files))
        
        # 세그먼트 파일들을 DIALOGUE_FLOW 순서로 추가
        for segment_idx, segment_info in enumerate(DIALOGUE_FLOW, 1):
            for flow_idx, flow_info in enumerate(segment_info['flow'], 1):
                speaker = flow_info['speaker']
                script_type = flow_info['type']
                
                speaker_code = "opt" if speaker == "optimistic" else "pes" if speaker == "pessimistic" else "mod"
                type_code = "dev" if script_type == "development" else "res" if script_type == "response" else "sum"
                
                audio_filename = f"seg{segment_idx}_{speaker_code}_{type_code}_{flow_idx}.mp3"
                audio_path = ticker_dir / audio_filename
                
                if audio_path.exists():
                    audio_files.append(audio_path)
        
        if not audio_files:
            print(f"❌ 합칠 MP3 파일이 없습니다: {ticker_symbol}")
            return False
        
        # ffmpeg를 사용하여 파일 합치기
        combined_file = ticker_dir / "combined.mp3"
        temp_list_file = ticker_dir / "file_list.txt"
        
        # 파일 목록을 텍스트 파일로 작성 (ffmpeg concat 용)
        with open(temp_list_file, 'w', encoding='utf-8') as f:
            for audio_file in audio_files:
                f.write(f"file '{audio_file.name}'\n")
        
        # ffmpeg 명령어 실행
        ffmpeg_cmd = [
            'ffmpeg', '-f', 'concat', '-safe', '0',
            '-i', str(temp_list_file),
            '-c', 'copy', str(combined_file), '-y'
        ]
        
        print(f"🎵 MP3 파일 합치기 시작: {ticker_symbol} ({len(audio_files)}개 파일)")
        result = subprocess.run(ffmpeg_cmd, cwd=ticker_dir, capture_output=True, text=True)
        
        # 임시 파일 삭제
        temp_list_file.unlink()
        
        if result.returncode == 0:
            print(f"✅ MP3 파일 합치기 완료: {combined_file}")
            return True
        else:
            print(f"❌ MP3 파일 합치기 실패: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ MP3 파일 합치기 중 오류: {e}")
        return False


def update_ui_mappings(ticker_symbol: str, company_name: str) -> bool:
    """ui_mappings.json에 새로운 회사 정보를 추가"""
    try:
        ui_mappings_file = PROJECT_ROOT / "resources" / "ui_mappings.json"
        
        # 기존 파일 읽기
        if ui_mappings_file.exists():
            with open(ui_mappings_file, 'r', encoding='utf-8') as f:
                ui_mappings = json.load(f)
        else:
            ui_mappings = {"company_mappings": {}, "file_title_mappings": {}}
        
        # company_mappings 섹션이 없으면 생성
        if "company_mappings" not in ui_mappings:
            ui_mappings["company_mappings"] = {}
        
        # 새로운 회사 정보 추가 (이미 존재하면 업데이트)
        ui_mappings["company_mappings"][ticker_symbol] = company_name
        
        # 파일에 저장
        with open(ui_mappings_file, 'w', encoding='utf-8') as f:
            json.dump(ui_mappings, f, ensure_ascii=False, indent=4)
        
        print(f"✅ UI 매핑 업데이트 완료: {ticker_symbol} -> {company_name}")
        return True
        
    except Exception as e:
        print(f"⚠️ UI 매핑 업데이트 실패: {e}")
        return False


def main():
    """메인 제어 함수"""
    
    if len(sys.argv) < 2:
        print("사용법: python control_flow.py '<주식에 대한 질문>'")
        print("예시: python control_flow.py '애플에 대해 이야기해줘'")
        sys.exit(1)
    
    user_request = sys.argv[1]
    
    print("🎯 주식 분석 워크플로우 시작")
    print(f"📝 사용자 요청: {user_request}")
    
    try:
        # 1단계: 회사 정보 추출
        print("\n=== 1단계: 회사 정보 추출 ===")
        company_name, ticker_symbol = extract_company_info(user_request)
        
        # 1.5단계: UI 매핑 업데이트
        print("\n=== 1.5단계: UI 매핑 업데이트 ===")
        update_ui_mappings(ticker_symbol, company_name)
        
        # 2단계: 메인 흐름과 서브 흐름들을 병렬로 실행
        print("\n=== 2단계: 병렬 워크플로우 실행 ===")
        print("🔄 메인 흐름과 서브 흐름들을 병렬로 시작합니다...")
        print("📺 실시간 출력을 통해 진행 상황을 확인할 수 있습니다.\n")
        
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            # 메인 흐름: 데이터 추출 → 데이터 정제 + 템플릿 생성 → 코멘터리 생성 → 대화 생성
            main_future = executor.submit(run_main_flow, ticker_symbol, company_name)
            
            # 서브 흐름 1: 사회자 대본/음성 생성
            moderator_future = executor.submit(run_moderator_flow, ticker_symbol, company_name)
            
            # 모든 흐름 완료 대기
            main_result = main_future.result()
            moderator_result = moderator_future.result()
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            # 결과 요약
            print(f"\n=== 워크플로우 실행 결과 ===")
            print(f"⏱️  총 실행 시간: {execution_time:.2f}초")
            print(f"✅ 메인 흐름: {'성공' if main_result else '실패'}")
            print(f"✅ 사회자 흐름: {'성공' if moderator_result else '실패'}")
            
            if not main_result:
                raise Exception("메인 흐름이 실패했습니다")
            
            # MP3 파일 합치기
            if main_result and moderator_result:
                print(f"\n=== MP3 파일 합치기 ===")
                merge_result = merge_mp3_files(ticker_symbol)
                if merge_result:
                    print(f"✅ 전체 대화 파일 생성 완료")
                else:
                    print(f"⚠️ MP3 파일 합치기 실패 (개별 파일은 사용 가능)")
        
        print(f"\n🎉 모든 작업이 완료되었습니다!")
        print(f"📊 결과 위치:")
        print(f"  - 정제된 데이터: {STOCK_DATA_REFINED_DIR / ticker_symbol.lower()}")
        print(f"  - 대본: {DIALOGUE_DIR / ticker_symbol.lower()}")
        print(f"  - 음성: {SPEAKING_DIR / ticker_symbol.lower()}")
        print(f"  - 템플릿: ../grounds/{ticker_symbol.lower()}")
        
    except KeyboardInterrupt:
        print("\n❌ 사용자에 의해 중단됨")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ 워크플로우 실행 중 오류 발생: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()