## Cleared
- stock_data_extractor.py에서 각 메서드 실패한도 3회 지정, 최대 3회 반복하게끔 코드 수정 요청하기
- template.json만들기
- fill_template.py 완성
- stock_data_refiner.py완성
- fill_commentary.py 완성
- 각 관점에서 해당 파일 채워넣기
- stock_data_refiner.py 병렬화 취소 및 control_flow에서 해당 작업 병렬화, 

- 마크다운 파일 생성시 좀 더 간결하게 작성하도록 (~함 / ~임.) + ...등 이 아니라 모든 지표 언급해서 데이터 안 빠뜨리게

- stock_data_extractor.py 티커심볼 처음에 못받을 때 개선.

- 마크다운 파일 함 다시 만들어보고 이 마크다운 파일 및 template.json기반으로 어떤식으로 대화 흐름을 짤지 gpt랑 논의해보기

- controlflow.py & generate_dialogue.py 수정: 
무조건 각 세그먼트의 한 파일만 처리하게끔, 세그먼트 내에서는 대화내역 쌓아서 계속 전달하게끔(출력된 txt파일을 보도록 하게하자)
프롬프트 짤 때 파일 경로를 명확하게 명시하고(코드 내부에서) 파일 경로 강조하기
tts 부분 어떤 파일 처리중인지 그 인자 확인해서 목소리 다르게 / 목소리 선택하기
get_current_segment_history함수 코드리뷰해보기: 이전 flow를 잘 불러오는지 확인, 해당 segment의 파일만 불러오는지 확인.
- 병렬처리 개선(generate_dialogue -> tts.py)

- streamlit 구현
DIALOGUE_FLOW 순서에 맞게 mp3파일 생성되는대로 이어서 재생하기
해당 주식 관련해서 생산한 md파일 뷰어 (각 파일 이름에 올바른 한국어 번역 이름 제공)

## In Process

- 전체 대본 프롬프트 개선
'여러분은 어떻게 생각해요?'가 아니라 그 다음 발화할 사람을 고려해서 문장을 마무리하게끔.
대부분은 그냥 잘 마무리 짓게끔 하고 질문을 던지는건 다음 발화대상이 사회자가 아닐 때.
+조금 더 구조화해서 체계적으로 길게 이야기하게끔.

- UI 개선: 진행중인 부분은 사이드에 빼두고 이미 만들어진 데이터에 대한 접근 가능하도록

## To Do


## Flow

0. 사용자의 요청: 어떤어떤 주식에 대해 이야기해줘 -> 주식 이름 및 티커심볼 획득

1. 주식 이름을 받아 사회자의 대본 및 음성파일 생성(generate_dialogue / tts 에 특정 인자 넣어서 작동하면 해당 작업하도록 처리) // stock_data_extractor.py ts

2. stock_data_refiner.py (모든 json파일 동시에) // fill_template.py 

-> fill_commentary.py

3. generate_dialogue.py, tts.py DIALOGUE_FLOW 따라가면서 계속 생성.


## DIALOGUE_FLOW

0. 사회자의 인트로(대화 전개 방식 설명, 해당 주식에 대한 간단한 설명) +뒤의 대화 처리가 너무 늦어진다 싶으면 refine된 md파일 중 all_financial_data_annual.md 로 llm돌려서 소개 멘트 더 넣어보기?

1. 기업 fundamental 분석

2. 