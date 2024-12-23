import pandas as pd
import os
from graphviz import Digraph
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime

# Graphviz 실행 파일 경로 설정 (이 경로는 필요에 따라 설정)
os.environ["PATH"] += os.pathsep + "/opt/homebrew/bin"  # 실제 `dot` 경로로 변경

def create_mindmap(file_path, output_file):
    try:
        # CSV 파일을 읽어오기
        data = pd.read_csv(file_path)
        
        # UnixTimestamp 기준으로 날짜로 변환하여 'Date' 컬럼 생성
        data['Date'] = pd.to_datetime(data['UnixTimestamp'], unit='s').dt.date
        
        # 거래를 날짜순으로 정렬
        data = data.sort_values(by="Date", ascending=True)

        # 거래를 시각화하기 위한 그래프 객체 생성
        dot = Digraph(comment="Wallet Interaction Mindmap", engine="dot")
        
        # 그래프 속성 설정
        dot.graph_attr.update(
            rankdir="LR",  # 방향을 왼쪽에서 오른쪽으로
            splines="polyline",  # 선을 부드럽게
            ranksep="1.5"  # 노드들 간의 간격을 더 넓히기 위해 값을 늘림
        )

        # 거래 기록을 추적하기 위한 딕셔너리
        interactions = {}

        def format_address(address, tag):
            """주소의 앞 6자리와 뒤 4자리만 표시하고, tag가 존재하면 괄호 안에 태그를 추가"""
            if tag != "-":
                return f"{address[:6]}...{address[-4:]}\n({tag})"
            return f"{address[:6]}...{address[-4:]}"
        
        # 거래 데이터를 순차적으로 처리하여 상호작용 기록을 만듦
        for _, row in data.iterrows():
            from_address = row["From"]
            to_address = row["To"]
            from_tag = row["From_PrivateTag"]
            to_tag = row["To_PrivateTag"]
            
            # 쉼표 제거 후 수량을 숫자로 변환
            quantity_str = row["Quantity"].replace(",", "")
            quantity = float(quantity_str)

            # 거래 날짜를 수집 (UnixTimestamp -> Date)
            transaction_date = row['Date']
            
            # 상호작용 기록 (날짜, 발신자, 수신자 기준으로 거래 수량 합산)
            key = (from_address, to_address, transaction_date)
            if key in interactions:
                interactions[key] += quantity
            else:
                interactions[key] = quantity
        
        # 거래의 출발지와 도착지 주소들을 처리
        added_edges = set()  # 이미 추가된 엣지를 추적하기 위한 집합
        
        for (from_address, to_address, transaction_date), total_quantity in interactions.items():
            # 주소에 해당하는 태그도 함께 가져옴
            from_tag = data.loc[data['From'] == from_address, 'From_PrivateTag'].iloc[0]
            to_tag = data.loc[data['To'] == to_address, 'To_PrivateTag'].iloc[0]
            
            from_label = f"{format_address(from_address, from_tag)}"
            to_label = f"{format_address(to_address, to_tag)}"

            # 엣지 라벨에 수량과 날짜를 추가
            edge_label = f"Qty: {total_quantity:.2f}\nDate: {transaction_date}"

            # 보낸 사람 -> 받은 사람으로 엣지를 추가 (양방향 아님)
            dot.edge(from_label, to_label, label=edge_label)

        # 지정된 경로에 PDF 형식으로 저장 (잔액 없이)
        dot.render(output_file, format="pdf", cleanup=True)
        messagebox.showinfo("완료", f"마인드맵이 {output_file}.pdf로 저장되었습니다.")
    
    except Exception as e:
        messagebox.showerror("오류", f"파일 처리 중 오류가 발생했습니다: {e}")


def upload_file():
    # 파일 대화상자를 열어 CSV 파일을 선택하도록 함
    file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
    if file_path:
        # 업로드된 파일 경로를 저장
        uploaded_file_label.config(text=f"업로드된 파일: {os.path.basename(file_path)}")
        app_data["file_path"] = file_path  # 파일 경로를 app_data 딕셔너리에 저장


def save_file():
    if "file_path" in app_data:
        # 현재 날짜를 "YYYY-MM-DD" 형식으로 가져옴
        current_date = datetime.now().strftime("%Y-%m-%d")
        # 변환할 파일명과 저장 위치를 지정하는 대화상자 열기
        output_file_path = filedialog.asksaveasfilename(
            initialfile=f"csvconvert_{current_date}"  # 기본 파일 이름에 날짜 추가 (확장자 제외)
        )
        if output_file_path:
            # 파일을 저장하고 마인드맵 생성
            create_mindmap(app_data["file_path"], output_file_path)
    else:
        messagebox.showwarning("파일 없음", "먼저 CSV 파일을 업로드해 주세요.")


# 앱 데이터 초기화
app_data = {}

# GUI 창 설정
root = tk.Tk()
root.title("마인드맵 생성기")
root.geometry("400x250")

# 업로드된 파일 라벨
uploaded_file_label = tk.Label(root, text="업로드된 파일: 없음", width=40, height=2)
uploaded_file_label.pack(pady=10)

# 파일 업로드 버튼
upload_button = tk.Button(root, text="CSV 파일 업로드", command=upload_file, width=20, height=2)
upload_button.pack(pady=10)

# 변환 및 저장 버튼
save_button = tk.Button(root, text="변환하기", command=save_file, width=20, height=2)
save_button.pack(pady=10)

# GUI 창 실행
root.mainloop()
