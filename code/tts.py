import os
import sys
import json
import traceback
from pathlib import Path
from openai import OpenAI
from openai import APIError, BadRequestError, RateLimitError
from dotenv import load_dotenv

# --- Configuration ---
BASE_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = BASE_DIR.parent / "scripts"  # Changed from "script" to "scripts" for consistency
AUDIO_DIR = BASE_DIR.parent / "audio"
DOTENV_PATH = BASE_DIR.parent / "resources" / ".env"

# Load environment variables (for OPENAI_API_KEY)
try:
    # Check if .env file exists
    if not Path(DOTENV_PATH).exists():
        print(f"[디버깅] 경고: .env 파일을 찾을 수 없습니다: {DOTENV_PATH}")
        
    load_dotenv(DOTENV_PATH)
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    if not OPENAI_API_KEY:
        print("[디버깅] 경고: OPENAI_API_KEY가 설정되지 않았습니다. API 호출이 실패할 수 있습니다.")
except Exception as e:
    print(f"[디버깅] 오류: 환경 변수 로드 중 오류 발생: {e}")
    OPENAI_API_KEY = None

# Initialize OpenAI client
try:
    client = OpenAI(api_key=OPENAI_API_KEY)
    if OPENAI_API_KEY:
        print("[디버깅] OpenAI 클라이언트 초기화 성공")
    else:
        print("[디버깅] 경고: OpenAI 클라이언트가 API 키 없이 초기화되었습니다. API 호출이 실패할 수 있습니다.")
except Exception as e:
    print(f"[디버깅] 오류: OpenAI 클라이언트 초기화 실패: {e}")
    client = None

def ensure_dir(directory_path: Path):
    """
    Ensure the directory exists, create if it doesn't.
    
    Args:
        directory_path: Path object pointing to the directory to ensure exists
        
    Returns:
        A string message describing the result of the operation.
    """
    try:
        if not isinstance(directory_path, Path):
            error_msg = f"[디버깅] 오류: 유효하지 않은 directory_path 유형: {type(directory_path)}"
            print(error_msg)
            return error_msg
            
        if not directory_path:
            error_msg = f"[디버깅] 오류: 빈 directory_path가 제공되었습니다."
            print(error_msg)
            return error_msg
            
        if not directory_path.exists():
            directory_path.mkdir(parents=True, exist_ok=True)
            success_msg = f"[디버깅] 디렉토리를 생성했습니다: {directory_path}"
            print(success_msg)
            return success_msg
        return f"디렉토리가 이미 존재합니다: {directory_path}"
    except PermissionError as pe:
        error_msg = f"[디버깅] 오류: 디렉토리 생성 권한 없음: {directory_path} - {pe}"
        print(error_msg)
        return error_msg
    except Exception as e:
        error_traceback = traceback.format_exc()
        error_msg = f"[디버깅] 오류: 디렉토리 생성 실패: {directory_path} - {e}"
        print(error_msg)
        print(f"[디버깅] 상세 오류: {error_traceback}")
        return error_msg

def get_speaker_role_and_instructions(filename: str):
    """
    Determines the speaker's role (pros/cons/moderator) and appropriate voice/instructions based on filename.
    
    Args:
        filename: The name of the script file without path and possibly ticker prefix
        
    Returns:
        A tuple: (voice, instructions_text)
    """
    try:
        # 파라미터 유효성 검사
        if not filename or not isinstance(filename, str):
            error_msg = f"[디버깅] 오류: 유효하지 않은 filename 유형: {type(filename) if filename is not None else 'None'}"
            print(error_msg)
            return "alloy", "Speak in a clear, neutral, and professional tone."
            
        if filename.strip() == "":
            error_msg = "[디버깅] 오류: 빈 filename이 전달되었습니다."
            print(error_msg)
            return "alloy", "Speak in a clear, neutral, and professional tone."
            
        # 파일명을 소문자로 변환하여 비교
        filename_lower = filename.lower()
        
        print(f"[디버깅] 역할 결정 중: {filename}")
        
        # 사회자 (Moderator)
        if "moderator_intro" in filename_lower or "moderator_summary" in filename_lower or "perspective_summary" in filename_lower or "final_summary" in filename_lower:
            voice = "alloy"
            instructions = "Speak in a clear, neutral, and professional tone. Maintain an authoritative but balanced demeanor."
            print(f"[디버깅] 역할 결정됨: 사회자 (Moderator), 음성: {voice}")
            return voice, instructions
        
        # 찬성측 (Pros)
        elif "opening_pros" in filename_lower or "defend_p_vs_c" in filename_lower or "refute_p2c" in filename_lower:
            voice = "nova"
            instructions = "Speak in a confident, persuasive, and slightly optimistic tone. Emphasize key points clearly."
            print(f"[디버깅] 역할 결정됨: 찬성측 (Pros), 음성: {voice}")
            return voice, instructions
        
        # 반대측 (Cons)
        elif "opening_cons" in filename_lower or "defend_c_vs_p" in filename_lower or "refute_c2p" in filename_lower:
            voice = "onyx"
            instructions = "Speak in a firm, slightly skeptical, and analytical tone. Maintain a serious demeanor."
            print(f"[디버깅] 역할 결정됨: 반대측 (Cons), 음성: {voice}")
            return voice, instructions
        
        # 기본값 (어느 쪽도 아닐 경우)
        print(f"[디버깅] 역할을 결정할 수 없음, 기본값 사용: {filename}")
        return "alloy", "Speak in a neutral and clear tone."
        
    except Exception as e:
        error_traceback = traceback.format_exc()
        error_msg = f"[디버깅] 역할 및 지시사항 결정 중 오류 발생: {e}"
        print(error_msg)
        print(f"[디버깅] 상세 오류: {error_traceback}")
        print(f"[디버깅] 문제의 filename: '{filename}'")
        return "alloy", "Speak in a neutral and clear tone."

def convert_script_to_audio(ticker_symbol, script_file_path, model="gpt-4o-mini-tts"):
    """
    Converts a script file to audio.
    
    Args:
        ticker_symbol: The ticker symbol of the stock.
        script_file_path: Full path to the script file.
        model: The TTS model to use.
    
    Returns:
        A dictionary with information about the conversion process.
    """
    try:
        # 파라미터 유효성 검사
        if not ticker_symbol or ticker_symbol.strip() == "":
            error_msg = "[디버깅] 오류: 빈 ticker_symbol이 전달되었습니다."
            print(error_msg)
            result = {"success": False, "message": error_msg}
            print(json.dumps(result))
            return result

        if not script_file_path or str(script_file_path).strip() == "":
            error_msg = "[디버깅] 오류: 빈 script_file_path가 전달되었습니다."
            print(error_msg)
            result = {"success": False, "message": error_msg}
            print(json.dumps(result))
            return result
            
        if not OPENAI_API_KEY:
            error_msg = "[디버깅] 오류: OPENAI_API_KEY가 설정되지 않았습니다."
            print(error_msg)
            result = {"success": False, "message": error_msg, "ticker_symbol": ticker_symbol}
            print(json.dumps(result))
            return result
            
        script_path = Path(script_file_path)
        
        # Ensure the script file exists
        if not script_path.exists():
            error_msg = f"[디버깅] 오류: 스크립트 파일을 찾을 수 없습니다: {script_path}"
            print(error_msg)
            result = {"success": False, "message": error_msg, "ticker_symbol": ticker_symbol}
            print(json.dumps(result))
            return result
        
        # Read script content
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                script_content = f.read()
        except FileNotFoundError:
            error_msg = f"[디버깅] 오류: 스크립트 파일을 찾을 수 없습니다: {script_path}"
            print(error_msg)
            result = {"success": False, "message": error_msg, "ticker_symbol": ticker_symbol}
            print(json.dumps(result))
            return result
        except Exception as e:
            error_msg = f"[디버깅] 오류: 스크립트 파일 읽기 실패: {script_path} - {e}"
            print(error_msg)
            result = {"success": False, "message": error_msg, "ticker_symbol": ticker_symbol}
            print(json.dumps(result))
            return result
        
        if not script_content or script_content.strip() == "":
            error_msg = f"[디버깅] 오류: 스크립트 파일이 비어 있습니다: {script_path}"
            print(error_msg)
            result = {"success": False, "message": error_msg, "ticker_symbol": ticker_symbol}
            print(json.dumps(result))
            return result
        
        # Set up audio output directory
        ticker_audio_dir = AUDIO_DIR / ticker_symbol
        dir_result = ensure_dir(ticker_audio_dir)
        if "[디버깅] 오류:" in dir_result:
            error_msg = f"[디버깅] 오류: 오디오 디렉토리 생성 실패: {ticker_audio_dir}"
            print(error_msg)
            result = {"success": False, "message": error_msg, "ticker_symbol": ticker_symbol}
            print(json.dumps(result))
            return result
        
        # Get the original filename without the ticker prefix and extension
        if script_path.stem.startswith(f"{ticker_symbol}_"):
            original_filename = script_path.stem[len(ticker_symbol)+1:]  # +1 for the underscore
        else:
            original_filename = script_path.stem
        
        # Determine voice and instructions based on the filename
        voice, instructions = get_speaker_role_and_instructions(original_filename)
        
        # Create audio filename
        audio_file_path = ticker_audio_dir / f"{original_filename}.mp3"
        
        # Generate audio
        try:
            print(f"[디버깅] TTS 변환 시작 (음성: {voice}): {original_filename}")
            response = client.audio.speech.create(
                model=model,
                voice=voice,
                input=script_content,
                instructions=instructions
            )
        except APIError as api_e:
            error_msg = f"[디버깅] OpenAI API 오류: {api_e}"
            print(error_msg)
            result = {"success": False, "message": error_msg, "ticker_symbol": ticker_symbol}
            print(json.dumps(result))
            return result
        except RateLimitError as re:
            error_msg = f"[디버깅] OpenAI API 속도 제한 오류: {re}"
            print(error_msg)
            result = {"success": False, "message": error_msg, "ticker_symbol": ticker_symbol}
            print(json.dumps(result))
            return result
        except BadRequestError as bre:
            error_msg = f"[디버깅] OpenAI 요청 형식 오류: {bre}"
            print(error_msg)
            result = {"success": False, "message": error_msg, "ticker_symbol": ticker_symbol}
            print(json.dumps(result))
            return result
        except Exception as e:
            error_msg = f"[디버깅] OpenAI API 호출 중 예외 발생: {e}"
            print(error_msg)
            result = {"success": False, "message": error_msg, "ticker_symbol": ticker_symbol}
            print(json.dumps(result))
            return result
        
        # Save audio file
        try:
            response.stream_to_file(audio_file_path)
            print(f"[디버깅] TTS 변환 완료: {audio_file_path}")
        except Exception as e:
            error_msg = f"[디버깅] 오류: 오디오 파일 저장 실패: {audio_file_path} - {e}"
            print(error_msg)
            result = {"success": False, "message": error_msg, "ticker_symbol": ticker_symbol}
            print(json.dumps(result))
            return result
        
        # 오디오 파일 존재 확인
        if not audio_file_path.exists():
            error_msg = f"[디버깅] 오류: 오디오 파일이 생성되지 않았습니다: {audio_file_path}"
            print(error_msg)
            result = {"success": False, "message": error_msg, "ticker_symbol": ticker_symbol}
            print(json.dumps(result))
            return result
            
        # 오디오 파일 크기 확인
        if audio_file_path.stat().st_size == 0:
            error_msg = f"[디버깅] 오류: 오디오 파일이 비어 있습니다: {audio_file_path}"
            print(error_msg)
            result = {"success": False, "message": error_msg, "ticker_symbol": ticker_symbol}
            print(json.dumps(result))
            return result
        
        # 결과 반환
        result = {
            "success": True,
            "message": f"음성 변환에 성공했습니다: {audio_file_path}",
            "ticker_symbol": ticker_symbol,
            "audio_file_path": str(audio_file_path),
            "script_file_path": str(script_path),
            "voice": voice
        }
        print(json.dumps(result))
        return result
        
    except Exception as e:
        error_traceback = traceback.format_exc()
        
        # 오류 발생 상황에 대한 자세한 정보 수집
        context_info = {
            "ticker_symbol": ticker_symbol if 'ticker_symbol' in locals() else "unknown",
            "script_file_path": str(script_file_path) if 'script_file_path' in locals() else "unknown",
            "api_key_set": bool(OPENAI_API_KEY),
            "model": model if 'model' in locals() else "unknown",
            "voice": voice if 'voice' in locals() else "unknown",
            "audio_dir_exists": AUDIO_DIR.exists() if 'AUDIO_DIR' in globals() else "unknown",
            "script_length": len(script_content) if 'script_content' in locals() else "unknown"
        }
        
        error_msg = f"[디버깅] 음성 변환 중 예상치 못한 오류 발생: {e}"
        print(error_msg)
        print(f"[디버깅] 상세 오류: {error_traceback}")
        print(f"[디버깅] 오류 컨텍스트: {json.dumps(context_info)}")
        
        result = {
            "success": False,
            "message": error_msg,
            "ticker_symbol": ticker_symbol if 'ticker_symbol' in locals() else "unknown",
            "script_file_path": str(script_file_path) if 'script_file_path' in locals() else "unknown",
            "error": str(e),
            "traceback": error_traceback,
            "error_context": context_info
        }
        print(json.dumps(result))
        return result

def main():
    """
    Main function to handle command-line execution of TTS conversion.
    Performs input validation and executes the conversion process.
    """
    import argparse
    
    try:
        # 명령행 인자 파싱
        parser = argparse.ArgumentParser(description="텍스트를 음성으로 변환")
        parser.add_argument("--input", required=True, help="입력 텍스트 파일 경로")
        parser.add_argument("--output", required=True, help="출력 음성 파일 경로")
        parser.add_argument("--voice", choices=["host", "optimist", "pessimist"], 
                          default="host", help="음성 타입 (사회자, 낙관론자, 비관론자)")
        
        args = parser.parse_args()
        
        # 음성 타입에 따른 OpenAI voice 매핑
        voice_mapping = {
            "host": "alloy",      # 사회자 - 중립적
            "optimist": "nova",   # 낙관론자 - 밝음  
            "pessimist": "onyx"   # 비관론자 - 차분함
        }
        
        selected_voice = voice_mapping[args.voice]
        
        # 입력 파일 확인
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"❌ 입력 파일을 찾을 수 없습니다: {input_path}")
            sys.exit(1)
        
        # 텍스트 파일 읽기
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                text_content = f.read()
        except Exception as e:
            print(f"❌ 파일 읽기 실패: {e}")
            sys.exit(1)
        
        if not text_content.strip():
            print(f"❌ 입력 파일이 비어있습니다: {input_path}")
            sys.exit(1)
        
        # 출력 디렉토리 생성
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # OpenAI TTS API 호출
        try:
            print(f"🔊 음성 생성 중... (음성: {args.voice})")
            response = client.audio.speech.create(
                model="tts-1",
                voice=selected_voice,
                input=text_content
            )
            
            # 음성 파일 저장
            response.stream_to_file(output_path)
            print(f"✓ 음성 생성 완료: {output_path}")
            
        except Exception as e:
            print(f"❌ 음성 생성 실패: {e}")
            sys.exit(1)
            
    except SystemExit:
        raise
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        sys.exit(1)
            
        return convert_result
            
    except Exception as e:
        error_traceback = traceback.format_exc()
        error_msg = f"[디버깅] main 함수 실행 중 예상치 못한 오류 발생: {e}"
        print(error_msg)
        print(f"[디버깅] 상세 오류: {error_traceback}")
        result = {
            "success": False,
            "message": error_msg,
            "error": str(e),
            "traceback": error_traceback
        }
        print(json.dumps(result))
        sys.exit(1)

if __name__ == "__main__":
    main()