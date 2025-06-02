#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenAI TTS를 사용한 음성 생성 모듈

파일명 패턴을 분석하여 화자와 발화 유형에 따라 
다른 음성과 톤을 적용하는 TTS 시스템
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Tuple, Dict, Any

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

# 화자별 음성 설정
VOICE_MAPPING = {
    "moderator": "nova",      # 사회자: 중성적이고 안정적인 목소리
    "optimistic": "alloy",    # 낙관론자: 밝고 에너지 넘치는 목소리  
    "pessimistic": "onyx",    # 신중론자: 깊고 신중한 목소리
    "default": "shimmer"      # 기본값
}

# 발화 유형별 톤 조정을 위한 텍스트 전처리
TONE_ADJUSTMENTS = {
    "development": {
        "prefix": "",
        "speaking_rate": "normal",
        "emphasis": "analytical"
    },
    "response": {
        "prefix": "",
        "speaking_rate": "slightly_slower", 
        "emphasis": "conversational"
    },
    "summary": {
        "prefix": "",
        "speaking_rate": "normal",
        "emphasis": "conclusive"
    },
    "intro": {
        "prefix": "",
        "speaking_rate": "normal", 
        "emphasis": "welcoming"
    }
}


def parse_filename(file_path: str) -> Tuple[str, str]:
    """
    파일명에서 화자와 발화 유형을 추출
    
    Args:
        file_path: 입력 파일 경로
        
    Returns:
        Tuple[speaker, speech_type]: 화자와 발화 유형
    """
    filename = Path(file_path).stem
    
    print(f"🔍 파일명 분석: {filename}")
    
    # 인트로 파일 패턴: intro.txt, intro_1.txt
    if filename.startswith("intro"):
        return "moderator", "intro"
    
    # 세그먼트 파일 패턴: seg{num}_{speaker_code}_{type_code}_{flow}
    if filename.startswith("seg"):
        parts = filename.split("_")
        if len(parts) >= 4:
            speaker_code = parts[1]
            type_code = parts[2]
            
            # 화자 코드 변환
            speaker_mapping = {
                "opt": "optimistic",
                "pes": "pessimistic", 
                "mod": "moderator"
            }
            
            # 타입 코드 변환
            type_mapping = {
                "dev": "development",
                "res": "response",
                "sum": "summary"
            }
            
            speaker = speaker_mapping.get(speaker_code, "default")
            speech_type = type_mapping.get(type_code, "development")
            
            print(f"  📝 세그먼트 파일 - 화자: {speaker}, 타입: {speech_type}")
            return speaker, speech_type
    
    # 패턴을 인식할 수 없는 경우 기본값
    print(f"  ⚠️ 알 수 없는 파일명 패턴, 기본값 사용")
    return "default", "development"


def get_tts_instruction(speech_type: str, speaker: str) -> str:
    """
    화자와 발화 유형에 따른 TTS instruction 생성
    
    Args:
        speech_type: 발화 유형 (development, response, summary, intro)
        speaker: 화자 (moderator, optimistic, pessimistic)
        
    Returns:
        str: TTS API에 전달할 instruction
    """
    instructions = {
        "moderator": {
            "intro": "음성을 친근하고 전문적인 톤으로 읽어주세요. 청취자를 환영하는 따뜻한 느낌으로 말하되, 신뢰할 수 있는 진행자의 목소리로 안정감 있게 발음해주세요.",
            "summary": "중립적이고 정리하는 톤으로 읽어주세요. 앞선 논의를 종합하여 마무리하는 느낌으로, 차분하고 명확하게 발음해주세요."
        },
        "optimistic": {
            "development": "확신에 찬 톤으로 읽어주세요. 긍정적인 분석을 제시하는 느낌으로 활기차고 설득력 있게 발음해주세요.",
            "response": "활기찬 톤으로 읽어주세요. 반박하거나 대응하는 느낌으로 에너지 넘치고 자신감 있게 발음해주세요.",
            "summary": "희망적인 톤으로 읽어주세요. 긍정적인 전망을 제시하는 느낌으로 밝고 격려하는 듯이 발음해주세요."
        },
        "pessimistic": {
            "development": "신중한 톤으로 읽어주세요. 면밀한 분석을 제시하는 느낌으로 차분하고 깊이 있게 발음해주세요.",
            "response": "논리적인 톤으로 읽어주세요. 반박하거나 우려사항을 제기하는 느낌으로 신중하고 설득력 있게 발음해주세요.",
            "summary": "신중한 톤으로 읽어주세요. 리스크나 주의사항을 강조하는 느낌으로 차분하고 진중하게 발음해주세요."
        }
    }
    
    # instruction 조회 및 기본값 처리
    speaker_instructions = instructions.get(speaker, instructions["moderator"])
    instruction = speaker_instructions.get(speech_type, "자연스럽고 명확한 톤으로 읽어주세요.")
    
    return instruction


def adjust_text(text: str, speech_type: str, speaker: str) -> str:
    """
    발화 유형과 화자에 따라 텍스트를 조정
    
    Args:
        text: 원본 텍스트
        speech_type: 발화 유형 (development, response, summary, intro)
        speaker: 화자 (moderator, optimistic, pessimistic)
        
    Returns:
        str: 조정된 텍스트
    """
    # 기본적으로 텍스트 정리
    adjusted_text = text.strip()
    
    # 텍스트 전처리 (필요시 추가)
    # 예: 특수 문자 처리, 발음하기 어려운 용어 교체 등
    
    return adjusted_text


def generate_speech(text: str, voice: str, output_path: str, instruction: str = "") -> bool:
    """
    OpenAI TTS API를 사용하여 음성 생성
    
    Args:
        text: 변환할 텍스트
        voice: 사용할 음성
        output_path: 출력 파일 경로
        instruction: TTS 스타일 instruction
        
    Returns:
        bool: 성공 여부
    """
    try:
        print(f"🔊 TTS 생성 시작...")
        print(f"  📝 텍스트 길이: {len(text)} 글자")
        print(f"  🎵 음성: {voice}")
        print(f"  🎭 instruction: {instruction[:50]}..." if len(instruction) > 50 else f"  🎭 instruction: {instruction}")
        print(f"  📁 출력: {output_path}")
        
        # 출력 디렉토리 생성
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # OpenAI TTS API 호출 (gpt-4o-mini-tts 모델은 instruction 파라미터 지원)
        speech_file_path = Path(output_path)
        
        # API 호출 파라미터 구성
        api_params = {
            "model": "gpt-4o-mini-tts",
            "voice": voice,
            "input": text
        }
        
        # # instruction이 있으면 파라미터에 추가.. 왜인지는 모르겠으나 instruction이 있으면 안 되는 듯...?
        # if instruction:
        #     api_params["instruction"] = instruction
        
        with client.audio.speech.with_streaming_response.create(**api_params) as response:
            response.stream_to_file(speech_file_path)
        
        print(f"✅ TTS 생성 완료: {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ TTS 생성 실패: {e}")
        return False


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="텍스트를 음성으로 변환")
    parser.add_argument("--input", required=True, help="입력 텍스트 파일 경로")
    parser.add_argument("--output", required=True, help="출력 음성 파일 경로")
    
    args = parser.parse_args()
    
    input_path = args.input
    output_path = args.output
    
    print("🎯 TTS 변환 시작")
    print(f"📄 입력 파일: {input_path}")
    print(f"🔊 출력 파일: {output_path}")
    
    # 입력 파일 존재 확인
    if not Path(input_path).exists():
        print(f"❌ 입력 파일을 찾을 수 없습니다: {input_path}")
        sys.exit(1)
    
    try:
        # 텍스트 파일 읽기
        with open(input_path, 'r', encoding='utf-8') as f:
            text = f.read().strip()
        
        if not text:
            print("❌ 입력 파일이 비어있습니다.")
            sys.exit(1)
        
        # 파일명에서 화자와 발화 유형 추출
        speaker, speech_type = parse_filename(input_path)
        
        # 화자에 따른 음성 선택
        voice = VOICE_MAPPING.get(speaker, VOICE_MAPPING["default"])
        
        # 화자와 발화 유형에 따른 instruction 생성
        instruction = get_tts_instruction(speech_type, speaker)
        
        print(f"🎭 화자: {speaker}")
        print(f"💬 발화 유형: {speech_type}")
        print(f"🎵 선택된 음성: {voice}")
        print(f"📋 instruction: {instruction[:100]}..." if len(instruction) > 100 else f"📋 instruction: {instruction}")
        
        # 텍스트 조정
        adjusted_text = adjust_text(text, speech_type, speaker)
        
        # TTS 생성 (instruction 포함)
        success = generate_speech(adjusted_text, voice, output_path, instruction)
        
        if success:
            print("🎉 TTS 변환 완료!")
            sys.exit(0)
        else:
            print("❌ TTS 변환 실패!")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ 처리 중 오류 발생: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()