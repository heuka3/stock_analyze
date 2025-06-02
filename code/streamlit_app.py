"""
Streamlit web application for Stock Analysis Dialogue Player
"""
import streamlit as st
import os
import glob
from pathlib import Path
import json
from generate_dialogue import DIALOGUE_FLOW
import base64
import subprocess
import threading
import time
import queue
import re
from datetime import datetime

# Configuration
BASE_DIR = Path(__file__).parent
SPEAKING_DIR = BASE_DIR.parent / "speaking"
STOCK_DATA_DIR = BASE_DIR.parent / "stock_data" / "refined"
CONTROL_FLOW_SCRIPT = BASE_DIR / "control_flow.py"
UI_MAPPINGS_FILE = BASE_DIR.parent / "resources" / "ui_mappings.json"

# Session state keys
SESSION_KEYS = {
    'processing_status': 'processing_status',
    'processing_logs': 'processing_logs',
    'current_ticker': 'current_ticker',
    'process_thread': 'process_thread',
    'log_queue': 'log_queue',
    'last_file_check': 'last_file_check'
}

def load_ui_mappings():
    """UI 매핑 정보를 로드"""
    try:
        with open(UI_MAPPINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"UI 매핑 파일을 로드할 수 없습니다: {e}")
        return {"company_mappings": {}, "file_title_mappings": {}}

def run_control_flow_process(query, log_queue):
    """Control flow를 별도 스레드에서 실행"""
    try:
        log_queue.put(f"🚀 프로세스 시작: {query}")
        
        # Control flow 스크립트 실행
        cmd = ['python', str(CONTROL_FLOW_SCRIPT), query]
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # 실시간 로그 수집
        for line in iter(process.stdout.readline, ''):
            if line.strip():
                log_queue.put(line.strip())
        
        process.wait()
        
        if process.returncode == 0:
            log_queue.put("✅ 프로세스가 성공적으로 완료되었습니다!")
        else:
            log_queue.put(f"❌ 프로세스가 실패했습니다. (종료 코드: {process.returncode})")
            
    except Exception as e:
        log_queue.put(f"❌ 프로세스 실행 중 오류: {str(e)}")

def get_company_display_name(ticker, mappings):
    """티커 심볼을 회사명으로 변환"""
    return mappings.get("company_mappings", {}).get(ticker, ticker)

def get_file_display_name(filename, mappings):
    """파일명을 한글 제목으로 변환"""
    return mappings.get("file_title_mappings", {}).get(filename, filename)

def get_processing_status(ticker):
    """특정 티커의 처리 상태를 확인"""
    if not ticker:
        return "idle"
    
    ticker_dir = SPEAKING_DIR / ticker.lower()
    refined_dir = STOCK_DATA_DIR / ticker.lower()
    
    # 완료된 경우
    if ticker_dir.exists() and refined_dir.exists():
        mp3_files = list(ticker_dir.glob("*.mp3"))
        md_files = list(refined_dir.glob("*.md"))
        
        if mp3_files and md_files:
            return "completed"
    
    # 처리 중인 경우 (일부 파일이 있는 경우)
    if ticker_dir.exists() or refined_dir.exists():
        return "processing"
    
    return "idle"

def count_completed_files(ticker):
    """완료된 파일 수를 계산"""
    if not ticker:
        return 0, 0, 0, 0
    
    ticker_dir = SPEAKING_DIR / ticker.lower()
    refined_dir = STOCK_DATA_DIR / ticker.lower()
    
    mp3_count = len(list(ticker_dir.glob("*.mp3"))) if ticker_dir.exists() else 0
    md_count = len(list(refined_dir.glob("*.md"))) if refined_dir.exists() else 0
    
    # DIALOGUE_FLOW 기반 예상 파일 수 계산
    expected_mp3 = sum(len(segment['flow']) for segment in DIALOGUE_FLOW) + 1  # +1 for intro
    expected_md = len(set(file for segment in DIALOGUE_FLOW for file in segment['markdown_files']))
    
    return mp3_count, expected_mp3, md_count, expected_md

def get_available_tickers():
    """Get list of available ticker symbols with MP3 files"""
    tickers = []
    if SPEAKING_DIR.exists():
        for ticker_dir in SPEAKING_DIR.iterdir():
            if ticker_dir.is_dir() and not ticker_dir.name.startswith('.'):
                # Check if there are any MP3 files
                mp3_files = list(ticker_dir.glob("*.mp3"))
                if mp3_files:
                    tickers.append(ticker_dir.name.upper())
    return sorted(tickers)

def get_available_companies(mappings):
    """사용 가능한 회사 목록을 회사명으로 반환"""
    tickers = get_available_tickers()
    companies = []
    for ticker in tickers:
        company_name = get_company_display_name(ticker, mappings)
        companies.append((company_name, ticker))
    return companies

def get_audio_files_for_ticker(ticker):
    """Get all MP3 files for a given ticker in DIALOGUE_FLOW order"""
    ticker_dir = SPEAKING_DIR / ticker.lower()
    if not ticker_dir.exists():
        return []
    
    # Build expected audio file names based on DIALOGUE_FLOW
    audio_files = []
    
    # Add combined file first if it exists
    combined_file = ticker_dir / "combined.mp3"
    if combined_file.exists():
        audio_files.append(combined_file)
    
    # Add intro if it exists
    intro_files = list(ticker_dir.glob("intro_*.mp3"))
    if intro_files:
        audio_files.extend(sorted(intro_files))
    
    # Add segment files in order
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
    
    return audio_files

def get_markdown_files_for_ticker(ticker):
    """Get all markdown files for a given ticker"""
    ticker_dir = STOCK_DATA_DIR / ticker.lower()
    if not ticker_dir.exists():
        return []
    
    md_files = list(ticker_dir.glob("*.md"))
    return sorted(md_files)

def load_markdown_file(file_path):
    """Load and return markdown file content"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error loading file: {str(e)}"

def main():
    st.set_page_config(
        page_title="Stock Analysis Dialogue Player",
        page_icon="📈",
        layout="wide"
    )
    
    st.title("📈 Stock Analysis Dialogue Player")
    st.markdown("Automatically play MP3 dialogue files and view stock analysis documents")
    
    # Load UI mappings
    ui_mappings = load_ui_mappings()
    
    # Initialize session state
    for key in SESSION_KEYS.values():
        if key not in st.session_state:
            if key == 'processing_logs':
                st.session_state[key] = []
            elif key == 'last_file_check':
                st.session_state[key] = 0
            else:
                st.session_state[key] = None
    
    # Sidebar for stock analysis request
    st.sidebar.header("🔍 New Stock Analysis")
    
    user_query = st.sidebar.text_input(
        "Enter your stock analysis request:",
        placeholder="e.g., Tell me about Apple stock, 애플에 대해 분석해줘",
        key="user_query"
    )
    
    if st.sidebar.button("🚀 Start Analysis", disabled=st.session_state.get(SESSION_KEYS['processing_status']) == 'processing'):
        if user_query:
            # control_flow.py가 회사명과 티커를 자동으로 추출하므로 쿼리를 그대로 전달
            st.session_state[SESSION_KEYS['processing_status']] = 'processing'
            st.session_state[SESSION_KEYS['processing_logs']] = []
            st.session_state[SESSION_KEYS['log_queue']] = queue.Queue()
            st.session_state[SESSION_KEYS['current_ticker']] = None  # Reset ticker
            st.session_state['ticker_detected_refreshed'] = False  # Reset refresh flag
            
            # Start processing in background thread
            thread = threading.Thread(
                target=run_control_flow_process,
                args=(user_query, st.session_state[SESSION_KEYS['log_queue']])
            )
            thread.daemon = True
            thread.start()
            st.session_state[SESSION_KEYS['process_thread']] = thread
            
            st.sidebar.success(f"✅ Analysis started for: {user_query}")
            # Don't call st.rerun() here to preserve sidebar interactions
        else:
            st.sidebar.error("❌ Please enter a stock analysis request")
    
    # Processing status section moved to sidebar
    processing_updated = False
    log_update_count = 0
    
    if st.session_state.get(SESSION_KEYS['processing_status']) == 'processing':
        # Update logs from queue - limit updates per cycle
        log_queue = st.session_state.get(SESSION_KEYS['log_queue'])
        if log_queue:
            try:
                # Process only a few logs at a time to avoid blocking UI
                max_logs_per_cycle = 3
                while log_update_count < max_logs_per_cycle:
                    log_entry = log_queue.get_nowait()
                    st.session_state[SESSION_KEYS['processing_logs']].append(f"[{datetime.now().strftime('%H:%M:%S')}] {log_entry}")
                    processing_updated = True
                    log_update_count += 1
                    
                    # Enhanced ticker extraction from logs
                    if not st.session_state.get(SESSION_KEYS['current_ticker']):
                        import re
                        ticker_patterns = [
                            r'Processing ticker: ([A-Z]+)',
                            r'분석 대상.*?([A-Z]{1,5})',
                            r'티커.*?([A-Z]{1,5})',
                            r'([A-Z]{1,5}).*?주식',
                            r'([A-Z]{1,5}).*?분석',
                            r'/([A-Z]+)/',
                            r'결과.*?([A-Z]{1,5})'
                        ]
                        for pattern in ticker_patterns:
                            match = re.search(pattern, log_entry)
                            if match:
                                extracted_ticker = match.group(1).upper()
                                # Validate ticker (common US stock tickers are 1-5 characters)
                                if 1 <= len(extracted_ticker) <= 5 and extracted_ticker.isalpha():
                                    st.session_state[SESSION_KEYS['current_ticker']] = extracted_ticker
                                    break
                    
                    # Extract ticker from successful completion logs
                    if "결과 위치:" in log_entry:
                        import re
                        match = re.search(r'/([^/]+)$', log_entry)
                        if match:
                            st.session_state[SESSION_KEYS['current_ticker']] = match.group(1).upper()
                    
                    # Check if processing is complete
                    if "성공적으로 완료" in log_entry or "실패했습니다" in log_entry:
                        st.session_state[SESSION_KEYS['processing_status']] = 'completed'
                        processing_updated = True
                        break
            except queue.Empty:
                pass
    
    # Stock selection section
    st.sidebar.header("📊 Available Stocks")
    available_companies = get_available_companies(ui_mappings)
    
    if available_companies:
        company_options = [company[0] for company in available_companies]
        selected_company_display = st.sidebar.selectbox(
            "Choose a company:",
            company_options,
            key="company_selection"
        )
        
        # Find the corresponding ticker
        selected_ticker = None
        for company_name, ticker in available_companies:
            if company_name == selected_company_display:
                selected_ticker = ticker
                break
    else:
        st.sidebar.info("No stocks available. Start a new analysis above.")
        selected_ticker = None
        selected_company_display = None
    
    # Processing status in sidebar (compact view) - use fragments to reduce refresh
    if st.session_state.get(SESSION_KEYS['processing_status']) == 'processing':
        st.sidebar.divider()
        st.sidebar.markdown("### 🔄 Processing Status")
        
        # Show progress - try to get ticker from query or logs
        current_ticker = st.session_state.get(SESSION_KEYS['current_ticker'])
        
        # If no current_ticker, try to extract from the most recent logs
        if not current_ticker and st.session_state[SESSION_KEYS['processing_logs']]:
            import re
            for log in reversed(st.session_state[SESSION_KEYS['processing_logs']]):
                # Look for ticker pattern in logs
                ticker_patterns = [
                    r'Processing ticker: ([A-Z]+)',
                    r'분석 대상: ([A-Z]+)',
                    r'티커: ([A-Z]+)',
                    r'([A-Z]{1,5}).*분석',
                    r'/([A-Z]+)/',
                    r'결과.*([A-Z]{1,5})'
                ]
                for pattern in ticker_patterns:
                    match = re.search(pattern, log)
                    if match:
                        current_ticker = match.group(1).upper()
                        st.session_state[SESSION_KEYS['current_ticker']] = current_ticker
                        break
                if current_ticker:
                    break
        
        # Progress display in a container to minimize impact
        progress_container = st.sidebar.container()
        with progress_container:
            if current_ticker:
                mp3_count, expected_mp3, md_count, expected_md = count_completed_files(current_ticker)
                
                # Compact progress display
                st.markdown(f"**📁 {current_ticker}**")
                
                # MP3 progress (clamp to 0-1 range)
                mp3_progress = min(1.0, mp3_count / expected_mp3) if expected_mp3 > 0 else 0
                st.progress(mp3_progress, text=f"🎵 MP3: {mp3_count}/{expected_mp3}")
                
                # Markdown progress (clamp to 0-1 range)
                md_progress = min(1.0, md_count / expected_md) if expected_md > 0 else 0
                st.progress(md_progress, text=f"📄 MD: {md_count}/{expected_md}")
            else:
                # Show general processing status without specific ticker
                st.info("🔄 Processing... Extracting ticker information...")
                st.caption("Analyzing request and generating content...")
        
        # Show recent logs (compact)
        with st.sidebar.expander("📋 Recent Logs", expanded=False):
            if st.session_state[SESSION_KEYS['processing_logs']]:
                # Show only last 5 logs in sidebar
                recent_logs = st.session_state[SESSION_KEYS['processing_logs']][-5:]
                for log in recent_logs:
                    st.caption(log)
            else:
                st.caption("Waiting for logs...")
    
    # Show completion status in sidebar
    elif st.session_state.get(SESSION_KEYS['processing_status']) == 'completed':
        st.sidebar.divider()
        st.sidebar.success("✅ Analysis completed!")
        
        # Show completed ticker if available
        completed_ticker = st.session_state.get(SESSION_KEYS['current_ticker'])
        if completed_ticker:
            mp3_count, expected_mp3, md_count, expected_md = count_completed_files(completed_ticker)
            st.sidebar.markdown(f"**📁 {completed_ticker}**")
            st.sidebar.markdown(f"🎵 Generated {mp3_count} MP3 files")
            st.sidebar.markdown(f"📄 Generated {md_count} markdown files")
            
            # Show completion status
            if mp3_count > 0 and md_count > 0:
                st.sidebar.info(f"✨ Ready to play! Select '{completed_ticker}' from the Available Stocks section below.")
        
        # Show final logs
        with st.sidebar.expander("📋 Final Logs", expanded=True):
            if st.session_state[SESSION_KEYS['processing_logs']]:
                # Show last 3 logs
                final_logs = st.session_state[SESSION_KEYS['processing_logs']][-3:]
                for log in final_logs:
                    st.caption(log)
        
        # Reset processing status after showing completion
        if st.sidebar.button("🔄 Clear Status"):
            st.session_state[SESSION_KEYS['processing_status']] = None
            st.session_state[SESSION_KEYS['processing_logs']] = []
            st.session_state[SESSION_KEYS['current_ticker']] = None
            st.session_state['ticker_detected_refreshed'] = False  # Reset refresh flag
            st.rerun()
    
    # Auto-refresh only when absolutely necessary - minimize to preserve UI interactions
    if processing_updated:
        # Only refresh in very specific cases to avoid blocking sidebar
        should_refresh = False
        
        # Only refresh when processing completes (final state change)
        if st.session_state.get(SESSION_KEYS['processing_status']) == 'completed':
            should_refresh = True
        
        # Don't refresh during processing to allow sidebar interactions
        # Progress will update naturally on the next render cycle
        
        if should_refresh:
            # Add small delay and then refresh
            import time
            time.sleep(0.3)
            st.rerun()
    
    if selected_ticker:
        # Main content area
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.header(f"🎵 Audio Player - {selected_company_display}")
            
            # Get audio files for selected ticker
            audio_files = get_audio_files_for_ticker(selected_ticker)
            
            if not audio_files:
                st.warning(f"No audio files found for {selected_company_display}")
            else:
                st.info(f"Found {len(audio_files)} audio files")
                
                # Initialize session state for current track (ticker-specific)
                track_key = f'current_track_index_{selected_ticker}'
                audio_files_key = f'audio_files_{selected_ticker}'
                
                # Initialize track index if not exists
                if track_key not in st.session_state:
                    st.session_state[track_key] = 0
                
                # Check if audio files changed and reset if needed
                current_audio_list = [f.name for f in audio_files]
                if (audio_files_key not in st.session_state or 
                    st.session_state[audio_files_key] != current_audio_list):
                    st.session_state[track_key] = 0
                    st.session_state[audio_files_key] = current_audio_list
                
                # Ensure track index is within bounds
                if st.session_state[track_key] >= len(audio_files):
                    st.session_state[track_key] = 0
                
                # Navigation buttons
                col_prev, col_next = st.columns(2)
                
                with col_prev:
                    if st.button("⏮️ Previous", disabled=st.session_state[track_key] == 0):
                        st.session_state[track_key] = max(0, st.session_state[track_key] - 1)
                        st.rerun()
                
                with col_next:
                    if st.button("⏭️ Next", disabled=st.session_state[track_key] >= len(audio_files) - 1):
                        st.session_state[track_key] = min(len(audio_files) - 1, st.session_state[track_key] + 1)
                        st.rerun()
                
                # Current track info
                current_file = audio_files[st.session_state[track_key]]
                track_name = current_file.name
                
                # Highlight combined file
                if track_name == "combined.mp3":
                    st.subheader(f"🎧 Now Playing: 🔗 전체 토론 ({track_name})")
                else:
                    st.subheader(f"🎧 Now Playing: {track_name}")
                
                st.text(f"Track {st.session_state[track_key] + 1} of {len(audio_files)}")
                
                # Audio player using Streamlit's native audio component
                try:
                    # Use a container to force widget refresh when track changes
                    audio_container = st.container()
                    with audio_container:
                        # Display audio player without key parameter
                        st.audio(str(current_file), format='audio/mp3')
                        
                        # Show file size for reference
                        file_size = current_file.stat().st_size / (1024 * 1024)  # MB
                        st.caption(f"File size: {file_size:.2f} MB")
                    
                except Exception as e:
                    st.error(f"Could not load audio file: {str(e)}")
                    st.error(f"File path: {current_file}")
                    
                    # Debug info
                    if st.checkbox("Show debug info", key=f"debug_{selected_ticker}"):
                        st.write(f"File exists: {current_file.exists()}")
                        if current_file.exists():
                            st.write(f"File size: {current_file.stat().st_size} bytes")
                        st.write(f"Current file: {current_file}")
                        st.write(f"Audio files: {[f.name for f in audio_files]}")
                        st.write(f"Track index: {st.session_state[track_key]}")
                
                # Track list
                st.subheader("📝 Track List")
                for i, audio_file in enumerate(audio_files):
                    prefix = "🔊" if i == st.session_state[track_key] else "🎵"
                    if audio_file.name == "combined.mp3":
                        prefix = "🔗" if i != st.session_state[track_key] else "🔊"
                        display_name = f"{prefix} 전체 토론 (combined.mp3)"
                    else:
                        display_name = f"{prefix} {audio_file.name}"
                    
                    if st.button(display_name, key=f"track_{selected_ticker}_{i}"):
                        st.session_state[track_key] = i
                        st.rerun()
        
        with col2:
            st.header(f"📄 Stock Analysis Documents - {selected_company_display}")
            
            # Get markdown files
            md_files = get_markdown_files_for_ticker(selected_ticker)
            
            if not md_files:
                st.warning(f"No markdown files found for {selected_company_display}")
            else:
                # File selector with Korean titles
                file_options = []
                file_mapping = {}
                
                for md_file in md_files:
                    display_name = get_file_display_name(md_file.name, ui_mappings)
                    file_options.append(display_name)
                    file_mapping[display_name] = md_file
                
                selected_file_display = st.selectbox(
                    "Choose a document:",
                    file_options,
                    key="md_file_selection"
                )
                
                selected_md_file = file_mapping.get(selected_file_display)
                
                if selected_md_file:
                    # Display file content
                    st.subheader(f"📖 {selected_file_display}")
                    
                    content = load_markdown_file(selected_md_file)
                    
                    # Show in expandable sections for better readability
                    with st.expander("📊 Document Content", expanded=True):
                        st.markdown(content)
                    
                    # Download button
                    st.download_button(
                        label="💾 Download Document",
                        data=content,
                        file_name=selected_md_file.name,
                        mime="text/markdown"
                    )
    
    # Dialogue Flow Information
    st.header("🎭 Dialogue Flow Structure")
    
    with st.expander("📋 View Dialogue Flow Details"):
        for i, segment in enumerate(DIALOGUE_FLOW, 1):
            st.subheader(f"Segment {i}: {segment['segment']}")
            st.write(f"**Topic:** {segment['topic']}")
            st.write(f"**Field:** {segment['field']}")
            
            # Show flow structure
            st.write("**Flow Structure:**")
            for j, flow in enumerate(segment['flow'], 1):
                speaker_emoji = "😊" if flow['speaker'] == "optimistic" else "😟" if flow['speaker'] == "pessimistic" else "🎤"
                st.write(f"  {j}. {speaker_emoji} {flow['speaker'].capitalize()} - {flow['type'].capitalize()}")
            
            # Show related markdown files
            st.write("**Related Documents:**")
            for md_file in segment['markdown_files']:
                display_name = get_file_display_name(md_file, ui_mappings)
                st.write(f"  • {display_name}")
            
            st.divider()

if __name__ == "__main__":
    main()
