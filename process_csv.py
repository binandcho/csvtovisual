import pandas as pd
import os
from graphviz import Digraph
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime
import matplotlib.colors as mcolors  # type: ignore
import random

# Graphviz 실행 파일 경로 설정
os.environ["PATH"] += os.pathsep + "/opt/homebrew/bin"  # 실제 `dot` 경로로 변경

# 언어별 텍스트 준비
languages = {
    "en": {
        "upload_file": "Upload CSV File",
        "no_file": "No file uploaded",
        "add_date": "Add Date",
        "remove_date": "Remove Selected Date",
        "convert": "Convert",
        "completed": "Mindmap saved as",
        "file_error": "Error processing file",
        "file_warning": "Please upload a CSV file first",
        "date_instruction": "Select the date to exclude",
    },
    "ko": {
        "upload_file": "CSV 파일 업로드",
        "no_file": "업로드된 파일: 없음",
        "add_date": "날짜 추가",
        "remove_date": "선택 날짜 제거",
        "convert": "변환하기",
        "completed": "마인드맵이 저장되었습니다",
        "file_error": "파일 처리 중 오류가 발생했습니다",
        "file_warning": "먼저 CSV 파일을 업로드해 주세요",
        "date_instruction": "제외할 날짜를 선택하세요",
    },
    "ja": {
        "upload_file": "CSVファイルをアップロード",
        "no_file": "アップロードされたファイル: なし",
        "add_date": "日付を追加",
        "remove_date": "選択された日付を削除",
        "convert": "変換",
        "completed": "マインドマップが保存されました",
        "file_error": "ファイルの処理中にエラーが発生しました",
        "file_warning": "まずCSVファイルをアップロードしてください",
        "date_instruction": "除外する日付を選択してください",
    },
}

current_language = "en"  # 기본 언어는 영어

def filter_colors():
    """흰색 및 밝은 색상을 제외한 색상 목록 생성"""
    filtered_colors = {}
    for name, hex_color in mcolors.CSS4_COLORS.items():
        r, g, b = mcolors.to_rgb(hex_color)
        brightness = (r + g + b) / 3
        if brightness < 0.85 and name != "white":  # 밝은 색상과 흰색 제외
            filtered_colors[name] = hex_color
    return list(filtered_colors.values())

def generate_colors(dates):
    """날짜별로 고유한 색상을 생성"""
    unique_dates = sorted(dates)
    color_map = {}
    available_colors = filter_colors()
    random.shuffle(available_colors)
    
    for i, date in enumerate(unique_dates):
        color_map[date] = available_colors[i % len(available_colors)]
    return color_map

def create_mindmap(file_path, output_file, excluded_dates):
    try:
        # CSV 파일 읽기
        data = pd.read_csv(file_path)
        
        # UnixTimestamp를 Date로 변환
        data['Date'] = pd.to_datetime(data['UnixTimestamp'], unit='s').dt.date
        data = data.sort_values(by="Date", ascending=True)

        # 필터링: 제외할 날짜를 제거
        filtered_data = data[~data['Date'].isin(excluded_dates)]

        # 날짜별 색상 매핑
        color_map = generate_colors(filtered_data['Date'].unique())

        # Graphviz 그래프 생성
        dot = Digraph(comment="Wallet Interaction Mindmap", engine="dot")
        dot.graph_attr.update(
            rankdir="LR",         # 왼쪽에서 오른쪽으로 그래프 레이아웃
            splines="true",       # 직선 경로 (기본값)
            ranksep="1.5",        # 노드 간의 수직 간격
            nodesep="1",          # 노드 간의 수평 간격
        )

        # 거래 데이터를 그래프에 추가
        for _, row in filtered_data.iterrows():
            from_address = row["From"]
            to_address = row["To"]
            from_tag = row["From_PrivateTag"] if pd.notna(row["From_PrivateTag"]) else "No Tag"
            to_tag = row["To_PrivateTag"] if pd.notna(row["To_PrivateTag"]) else "No Tag"
            quantity = float(row["Quantity"].replace(",", ""))
            transaction_date = row["Date"]

            # 거래 정보 표시 형식 지정
            from_label = f"{from_address[:6]}...{from_address[-4:]}\n({from_tag})"
            to_label = f"{to_address[:6]}...{to_address[-4:]}\n({to_tag})"
            edge_label = f"Qty: {quantity:.2f}\nDate: {transaction_date}"
            edge_color = color_map[transaction_date]

            # 엣지의 화살표 방향을 한 방향으로 설정
            dot.edge(from_label, to_label, label=edge_label, color=edge_color, dir='forward')

        # PDF 파일 저장
        dot.render(output_file, format="pdf", cleanup=True)
        messagebox.showinfo(languages[current_language]["completed"], f"{output_file} {languages[current_language]['completed']}.")
    
    except Exception as e:
        messagebox.showerror(languages[current_language]["file_error"], f"{languages[current_language]['file_error']}: {e}")


def upload_file():
    file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
    if file_path:
        uploaded_file_label.config(text=f"{languages[current_language]['upload_file']}: {os.path.basename(file_path)}")
        app_data["file_path"] = file_path

        # CSV 파일에서 날짜 및 수량 추출
        data = pd.read_csv(file_path)
        data['Date'] = pd.to_datetime(data['UnixTimestamp'], unit='s').dt.date
        app_data["available_dates"] = (
            data.groupby('Date')['Quantity']
            .apply(lambda x: sum(float(q.replace(",", "")) for q in x))
            .reset_index(name='TotalQuantity')
        )

        # 드롭다운 업데이트 (날짜와 보낸 총 수량 표시)
        date_dropdown["values"] = [
            f"{row['Date']} ({languages[current_language]['add_date']}: {row['TotalQuantity']:.2f})"
            for _, row in app_data["available_dates"].iterrows()
        ]
        update_save_button_state()


def add_date():
    """선택된 날짜를 필터링 목록에 추가"""
    selected_entry = date_dropdown.get()
    if selected_entry:
        # 선택된 항목에서 날짜 추출
        selected_date = selected_entry.split(" ")[0]
        date_obj = datetime.strptime(selected_date, "%Y-%m-%d").date()
        if date_obj not in app_data["excluded_dates"]:
            app_data["excluded_dates"].append(date_obj)
            excluded_dates_list.insert(tk.END, date_obj)


def remove_date():
    """선택된 날짜를 필터링 목록에서 제거"""
    selected_idx = excluded_dates_list.curselection()
    if selected_idx:
        selected_date = excluded_dates_list.get(selected_idx)
        excluded_dates_list.delete(selected_idx)
        app_data["excluded_dates"].remove(selected_date)


def save_file():
    if "file_path" in app_data:
        current_date = datetime.now().strftime("%Y-%m-%d")
        output_file_path = filedialog.asksaveasfilename(
            initialfile=f"csvconvert_{current_date}"
        )
        if output_file_path:
            # 사용자가 파일 이름을 지정한 그대로 저장
            create_mindmap(app_data["file_path"], output_file_path, app_data["excluded_dates"])
    else:
        messagebox.showwarning(languages[current_language]["file_warning"], languages[current_language]["file_warning"])


def update_save_button_state():
    """업로드된 파일 상태에 따라 저장 버튼 활성화/비활성화"""
    if app_data["file_path"]:
        save_button.config(state=tk.NORMAL)
    else:
        save_button.config(state=tk.DISABLED)


def change_language(event):
    """언어 변경 처리"""
    global current_language
    selected_language = language_dropdown.get()
    if selected_language == "English":
        current_language = "en"
    elif selected_language == "Korean":
        current_language = "ko"
    elif selected_language == "Japanese":
        current_language = "ja"

    # 텍스트 업데이트
    update_texts()


def update_texts():
    """UI 텍스트 업데이트"""
    uploaded_file_label.config(text=f"{languages[current_language]['no_file']}")
    upload_button.config(text=languages[current_language]["upload_file"])
    add_date_button.config(text=languages[current_language]["add_date"])
    remove_date_button.config(text=languages[current_language]["remove_date"])
    save_button.config(text=languages[current_language]["convert"])
    date_instruction_label.config(text=languages[current_language]["date_instruction"])


# 앱 데이터 초기화
app_data = {
    "file_path": None,
    "excluded_dates": [],
    "available_dates": None
}

# GUI 설정
root = tk.Tk()
root.title("Mindmap Generator")
root.geometry("500x500")
root.resizable(False, False)

# 아이콘 설정 (아이콘 파일 경로를 지정)
# root.iconbitmap("path/to/your/icon.ico")  # 아이콘 파일 경로를 여기에 넣으세요.

# 언어 변경 드롭다운 (오른쪽 상단에 배치)
language_dropdown = ttk.Combobox(root, values=["English", "Korean", "Japanese"], state="readonly", width=8)
language_dropdown.place(x=395, y=10)  # 오른쪽 상단에 배치
language_dropdown.bind("<<ComboboxSelected>>", change_language)

uploaded_file_label = tk.Label(root, text=languages[current_language]["no_file"], width=30, height=2)
uploaded_file_label.pack(pady=5)

# 업로드 버튼과 날짜 제외 버튼을 수평으로 배치
button_frame = tk.Frame(root)
button_frame.pack(pady=5)

upload_button = tk.Button(button_frame, text=languages[current_language]["upload_file"], command=upload_file, width=20, height=2)
upload_button.pack(side=tk.LEFT, padx=5)

# 날짜 제외 드롭다운 위 해설 추가
date_instruction_label = tk.Label(root, text=languages[current_language]["date_instruction"], width=40, height=2)
date_instruction_label.pack(pady=5)

# 드롭다운 메뉴 생성
date_dropdown = ttk.Combobox(root, state="readonly", width=40)
date_dropdown.pack(pady=2)

# 날짜 추가 및 제거 버튼
add_date_button = tk.Button(root, text=languages[current_language]["add_date"], command=add_date, width=15)
add_date_button.pack(pady=2)

excluded_dates_list = tk.Listbox(root, width=40, height=5)
excluded_dates_list.pack(pady=5)

remove_date_button = tk.Button(root, text=languages[current_language]["remove_date"], command=remove_date, width=15)
remove_date_button.pack(pady=5)

save_button = tk.Button(root, text=languages[current_language]["convert"], command=save_file, width=20, height=2, state=tk.DISABLED)
save_button.pack(pady=10)

update_save_button_state()  # 초기 상태 업데이트
update_texts()  # 초기 텍스트 업데이트

root.mainloop()
