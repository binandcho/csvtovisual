import pandas as pd
import os
from graphviz import Digraph
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime
import matplotlib.colors as mcolors
import random

# Graphviz 실행 파일 경로 설정
os.environ["PATH"] += os.pathsep + "/opt/homebrew/bin"  # 실제 `dot` 경로로 변경

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
            from_tag = row["From_PrivateTag"]
            to_tag = row["To_PrivateTag"]
            quantity = float(row["Quantity"].replace(",", ""))
            transaction_date = row["Date"]

            from_label = f"{from_address[:6]}...{from_address[-4:]}\n({from_tag})"
            to_label = f"{to_address[:6]}...{to_address[-4:]}\n({to_tag})"
            edge_label = f"Qty: {quantity:.2f}\nDate: {transaction_date}"
            edge_color = color_map[transaction_date]

            # 엣지의 화살표 방향을 한 방향으로 설정
            dot.edge(from_label, to_label, label=edge_label, color=edge_color, dir='forward')

        # PDF 파일 저장
        dot.render(output_file, format="pdf", cleanup=True)
        messagebox.showinfo("완료", f"마인드맵이 {output_file}.pdf로 저장되었습니다.")
    
    except Exception as e:
        messagebox.showerror("오류", f"파일 처리 중 오류가 발생했습니다: {e}")


def upload_file():
    file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
    if file_path:
        uploaded_file_label.config(text=f"업로드된 파일: {os.path.basename(file_path)}")
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
            f"{row['Date']} (Total Qty: {row['TotalQuantity']:.2f})"
            for _, row in app_data["available_dates"].iterrows()
        ]


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
            initialfile=f"csvconvert_{current_date}", filetypes=[("PDF files", "*.pdf")]
        )
        if output_file_path:
            if not output_file_path.endswith(".pdf"):
                output_file_path += ".pdf"
            create_mindmap(app_data["file_path"], output_file_path, app_data["excluded_dates"])
    else:
        messagebox.showwarning("파일 없음", "먼저 CSV 파일을 업로드해 주세요.")


# 앱 데이터 초기화
app_data = {
    "file_path": None,
    "excluded_dates": [],
    "available_dates": None
}

# GUI 설정
root = tk.Tk()
root.title("마인드맵 생성기")
root.geometry("450x450")

uploaded_file_label = tk.Label(root, text="업로드된 파일: 없음", width=40, height=2)
uploaded_file_label.pack(pady=10)

upload_button = tk.Button(root, text="CSV 파일 업로드", command=upload_file, width=20, height=2)
upload_button.pack(pady=10)

date_dropdown = ttk.Combobox(root, state="readonly", width=40)
date_dropdown.pack(pady=5)

add_date_button = tk.Button(root, text="날짜 추가", command=add_date, width=15)
add_date_button.pack(pady=5)

excluded_dates_list = tk.Listbox(root, width=40, height=5)
excluded_dates_list.pack(pady=10)

remove_date_button = tk.Button(root, text="선택 날짜 제거", command=remove_date, width=15)
remove_date_button.pack(pady=5)

save_button = tk.Button(root, text="변환하기", command=save_file, width=20, height=2)
save_button.pack(pady=10)

root.mainloop()
