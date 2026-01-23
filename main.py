import os
import re
import json
import threading
from pathlib import Path
import customtkinter as ctk
from tkinter import filedialog, messagebox
from ebooklib import epub

# [STEP 0] 모듈 가져오기
# 제작한 클리너(정제기)와 병합기 모듈을 불러옵니다.
from ai_cleaner import clean_text_with_ai
from cleaner import clean_structure, remove_tagged_content
from merger import merge_paragraphs

CONFIG_DIR = Path.home() / ".txt_to_epub_tool"
CONFIG_PATH = CONFIG_DIR / "config.json"


def load_saved_api_key():
    env_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if env_key:
        return env_key

    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("gemini_api_key", "").strip()
    except FileNotFoundError:
        return ""
    except Exception:
        return ""


def save_api_key(api_key):
    if not api_key:
        return

    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with CONFIG_PATH.open("w", encoding="utf-8") as f:
            json.dump({"gemini_api_key": api_key}, f)
    except Exception:
        pass

# [설정] 커스텀 Tkinter 테마 설정
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class TextToEpubApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # [STEP 1] UI 초기화
        # 윈도우 제목과 크기를 설정합니다.
        self.title("Text to EPUB Converter (Advanced)")
        self.geometry("600x750") # UI 요소가 늘어남에 따라 높이 확장

        # 그리드 레이아웃 설정 (0번 컬럼이 늘어나도록)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(7, weight=1) # 로그 창이 남는 공간 차지

        # 변수 초기화
        self.input_files = [] # 선택된 파일 경로들을 저장할 리스트

        # [UI] 1. 파일 선택 구역
        # 여러 파일을 선택하고 목록을 보여줍니다.
        self.btn_browse = ctk.CTkButton(self, text="텍스트 파일 선택 (여러 개 가능)", command=self.browse_files)
        self.btn_browse.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        
        # 선택된 파일 목록을 보여주는 읽기 전용 텍스트박스
        self.txt_file_list = ctk.CTkTextbox(self, height=80, text_color="silver")
        self.txt_file_list.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.txt_file_list.insert("0.0", "선택된 파일이 없습니다.")
        self.txt_file_list.configure(state="disabled") # 사용자 수정 방지

        # [UI] 2. 메타데이터 (책 정보) 구역
        # 일괄 변환 시에는 '파일명'을 제목으로 쓰는 것이 기본이지만, 
        # 공통 저자명을 입력받을 수 있습니다.
        self.frame_meta = ctk.CTkFrame(self)
        self.frame_meta.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        self.frame_meta.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.frame_meta, text="저자 (공통):").grid(row=0, column=0, padx=10, pady=10)
        self.entry_author = ctk.CTkEntry(self.frame_meta, placeholder_text="미상")
        self.entry_author.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        # [UI] 3. AI 설정 구역
        self.frame_ai = ctk.CTkFrame(self)
        self.frame_ai.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        self.frame_ai.grid_columnconfigure(1, weight=1)
        
        self.use_ai_var = ctk.BooleanVar(value=True) # 기본값: AI 사용
        self.chk_use_ai = ctk.CTkCheckBox(self.frame_ai, text="AI 정제 사용 (Gemini API)", variable=self.use_ai_var, command=self.toggle_ai_options)
        self.chk_use_ai.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="w")
        
        ctk.CTkLabel(self.frame_ai, text="API Key:").grid(row=1, column=0, padx=10, pady=10)
        self.entry_api_key = ctk.CTkEntry(self.frame_ai, placeholder_text="AIzaSy...", show="*")
        self.entry_api_key.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        self._saved_api_key = load_saved_api_key()
        if self._saved_api_key:
            self.entry_api_key.insert(0, self._saved_api_key)
        
        # [UI] 4. 변환 버튼
        self.btn_convert = ctk.CTkButton(self, text="EPUB변환 시작", command=self.start_conversion, fg_color="green", hover_color="darkgreen")
        self.btn_convert.grid(row=4, column=0, padx=20, pady=20, sticky="ew")

        # [UI] 5. 진행률 바
        self.progressbar = ctk.CTkProgressBar(self)
        self.progressbar.grid(row=5, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.progressbar.set(0)
        
        self.lbl_status = ctk.CTkLabel(self, text="대기 중")
        self.lbl_status.grid(row=6, column=0, padx=20, sticky="w")

        # [UI] 6. 로그 창
        self.textbox_log = ctk.CTkTextbox(self, height=150)
        self.textbox_log.grid(row=7, column=0, padx=20, pady=(0, 20), sticky="nsew")
        
        self.log("프로그램이 시작되었습니다.")
        if self._saved_api_key:
            self.log("저장된 API Key를 불러왔습니다.")

    def toggle_ai_options(self):
        """AI 체크박스 상태에 따라 API 키 입력창 활성화/비활성화"""
        state = "normal" if self.use_ai_var.get() else "disabled"
        self.entry_api_key.configure(state=state)

    def log(self, message):
        """로그 창에 메시지를 추가하고 스크롤을 맨 아래로 내립니다."""
        self.textbox_log.insert("end", message + "\n")
        self.textbox_log.see("end")

    def browse_files(self):
        """
        [STEP 1-1] 파일 선택 다이얼로그
        여러 개의 텍스트 파일을 선택할 수 있습니다.
        """
        filenames = filedialog.askopenfilenames(filetypes=[("Text Files", "*.txt")])
        if filenames:
            self.input_files = list(filenames)
            
            # 목록 표시 업데이트
            self.txt_file_list.configure(state="normal")
            self.txt_file_list.delete("0.0", "end")
            display_text = f"총 {len(self.input_files)}개 파일 선택됨:\n"
            for f in self.input_files:
                display_text += f"- {os.path.basename(f)}\n"
            self.txt_file_list.insert("0.0", display_text)
            self.txt_file_list.configure(state="disabled")
            
            self.log(f"{len(self.input_files)}개 파일이 로드되었습니다.")

    def start_conversion(self):
        """변환 시작 전 유효성 검사 및 스레드 시작"""
        if not self.input_files:
            messagebox.showerror("오류", "변환할 파일을 먼저 선택해주세요.")
            return
        
        api_key = self.entry_api_key.get().strip()
        use_ai = self.use_ai_var.get()

        if use_ai and not api_key:
            api_key = load_saved_api_key()
            if api_key:
                self.entry_api_key.delete(0, "end")
                self.entry_api_key.insert(0, api_key)
                self.log("저장된 API Key를 불러왔습니다.")

        if use_ai and not api_key:
            messagebox.showerror("오류", "AI 기능을 사용하려면 API Key가 필요합니다.")
            return
        elif use_ai:
            save_api_key(api_key)

        author = self.entry_author.get()
        if not author:
            author = "Unknown"

        self.btn_convert.configure(state="disabled")
        self.btn_browse.configure(state="disabled")
        self.progressbar.set(0)
        self.change_status("변환 준비 중...")
        
        # [STEP 2] 별도 스레드에서 작업 시작 (UI 멈춤 방지)
        threading.Thread(target=self.run_batch_conversion, args=(self.input_files, author, use_ai, api_key)).start()

    def change_status(self, text):
        self.lbl_status.configure(text=text)

    def run_batch_conversion(self, files, author, use_ai, api_key):
        """
        [STEP 3] 일괄 변환 로직 - 반복문
        선택된 모든 파일을 순회하며 변환합니다.
        """
        total_files = len(files)
        success_count = 0
        
        for idx, input_path in enumerate(files):
            basename = os.path.basename(input_path)
            title = os.path.splitext(basename)[0] # 파일명을 책 제목으로 사용
            
            self.log(f"========== [{idx+1}/{total_files}] '{title}' 처리 시작 ==========")
            self.change_status(f"처리 중 ({idx+1}/{total_files}): {title}")
            
            try:
                # 단일 파일 변환 수행
                self.process_single_file(input_path, title, author, use_ai, api_key, idx, total_files)
                success_count += 1
                self.log(f"'{title}' 변환 완료.")
                
            except Exception as e:
                self.log(f"[ERROR] '{title}' 변환 실패: {str(e)}")
        
        # [STEP 6] 완료 처리
        self.progressbar.set(1.0)
        self.change_status("모든 작업 완료")
        self.btn_convert.configure(state="normal")
        self.btn_browse.configure(state="normal")
        
        messagebox.showinfo("완료", f"총 {total_files}개 중 {success_count}개 파일 변환 성공!")

    def process_single_file(self, input_path, title, author, use_ai, api_key, file_idx, total_files):
        """
        [STEP 4] 단일 파일 변환 파이프라인
        1. 읽기 -> 2. AI 정제/구조 정제 -> 3. 병합 -> 4. EPUB 생성
        """
        
        # 내부 진행률 계산용 함수
        def update_sub_progress(val):
            # 전체 진행률 = (현재파일인덱스 + 현재파일내부진행률) / 전체파일수
            global_progress = (file_idx + val) / total_files
            self.progressbar.set(global_progress)

        update_sub_progress(0.0)
        
        # [4-1] 파일 읽기
        with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
            raw_text = f.read()

        final_text = ""

        if use_ai:
            self.log(" > AI 엔진 가동 중... (시간이 걸릴 수 있습니다)")
            try:
                # [4-2] AI 정제 (청크 분할 + 태그 처리)
                # progress_callback을 통해 내부 진행률(0.1 ~ 0.8)을 받아옴
                ai_cleaned = clean_text_with_ai(raw_text, api_key, progress_callback=update_sub_progress)
                
                self.log(" > AI 분석 완료. 태그된 노이즈 제거 중...")
                
                # [4-3] 태그된 노이즈 삭제 (<<<DELETE: ... >>>)
                cleaned_text = remove_tagged_content(ai_cleaned)
                
                # 병합은 AI가 이미 줄바꿈을 정리했으므로 불필요할 수 있으나,
                # 안전을 위해 빈 줄 정리 정도는 할 수 있음. 여기선 바로 사용.
                final_text = cleaned_text
                
            except Exception as e:
                self.log(f" > AI 처리 실패 (API 오류 등): {e}")
                self.log(" > 일반 모드로 전환하여 계속 진행합니다.")
                cleaned_text = clean_structure(raw_text)
                final_text = merge_paragraphs(cleaned_text)
        else:
            # AI 미사용 시: 기존 알고리즘 사용
            self.log(" > 구조적 정제(헤더 제거) 수행 중...")
            cleaned_text = clean_structure(raw_text)
            self.log(" > 문단 병합 중...")
            final_text = merge_paragraphs(cleaned_text)

        update_sub_progress(0.9)
        self.log(" > EPUB 파일 생성 중...")
        
        # [4-4] EPUB 생성
        output_path = os.path.splitext(input_path)[0] + ".epub"
        self.create_epub(final_text, output_path, title, author)
        
        self.log(f" > 저장됨: {output_path}")

    def create_epub(self, text, output_path, title, author):
        """
        [STEP 5] EPUB 구조 생성 및 저장
        """
        book = epub.EpubBook()

        # 메타데이터 설정
        book.set_identifier('id_generated_by_ai_tool') 
        book.set_title(title)
        book.set_language('ko') # 한국어 기본 설정
        book.add_author(author)

        # 텍스트를 HTML로 변환
        # 문단은 빈 줄(\n\n)로 구분되어 있다고 가정
        paragraphs = text.split('\n\n')
        html_content = f"<h1>{title}</h1>"
        
        # 헤더 감지 패턴 (예: 제1장, Chapter 1, 1. 등)
        header_pattern = re.compile(r'^(Chapter\s+\d+|^\d+\.\s+|제\s*\d+\s*장|^\d+$)', re.IGNORECASE)

        for p in paragraphs:
            clean_p = p.strip()
            if not clean_p:
                continue
                
            # 헤더 감지 로직
            if len(clean_p) < 100 and header_pattern.match(clean_p):
                # 챕터 제목으로 간주 (<h3> 태그 사용)
                # id를 주어 TOC 연결 가능하게 함
                safe_id = clean_p[:10].replace(' ', '_')
                html_content += f"<h2 id='{safe_id}'>{clean_p}</h2>"
            else:
                # 일반 문단
                html_content += f"<p>{clean_p}</p>"

        # 챕터 생성
        c1 = epub.EpubHtml(title='본문', file_name='content.xhtml', lang='ko')
        c1.content = html_content
        book.add_item(c1)

        # 필수 파일 추가
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        # 스파인(순서) 설정
        book.spine = ['nav', c1]

        # 파일 쓰기
        epub.write_epub(output_path, book)

if __name__ == "__main__":
    app = TextToEpubApp()
    app.mainloop()

