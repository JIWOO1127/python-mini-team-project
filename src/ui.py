import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox

import requests
from dotenv import load_dotenv


load_dotenv()

BACKEND_BASE_URL = os.getenv(
    "BACKEND_BASE_URL",
    "http://127.0.0.1:8000",
).rstrip("/")
REQUEST_TIMEOUT = 30


class EVChargingApp:

    def __init__(self, root):
        self.root = root
        self.root.title("EV Charging Assistant")
        self.root.geometry("1100x900")

        self.temperature = None
        self.stations = []
        self.mode = "auto"
        self.requested_mode = "auto"
        self.recommended_mode = None

        self.create_widgets()

    # 입력창
    def create_widgets(self):

        # 제목
        title = ttk.Label(
            self.root,
            text="EV Charging Assistant",
            font=("맑은 고딕", 20, "bold")
        )
        title.pack(pady=20)

        # 위치 입력
        location_frame = ttk.Frame(self.root)
        location_frame.pack(fill="x", padx=20, pady=10)

        ttk.Label(
            location_frame,
            text="현재 위치"
        ).pack(side="left")

        self.location_entry = ttk.Entry(
            location_frame,
            width=60
        )
        self.location_entry.pack(
            side="left",
            padx=10
        )

        self.location_entry.insert(
            0,
            "경기도 수원시 영통구 영통동"
        )

        ttk.Button(
            location_frame,
            text="조회",
            command=self.start_search
        ).pack(side="left")


        # 날씨
        weather_frame = ttk.Frame(self.root)
        weather_frame.pack(fill="x", padx=20, pady=10)

        self.temperature_label = ttk.Label(
            weather_frame,
            text="현재 기온: -"
        )
        self.temperature_label.pack(side="left")

        self.recommend_label = ttk.Label(
            weather_frame,
            text="추천 충전 방식: -"
        )
        self.recommend_label.pack(
            side="left",
            padx=30
        )


        # 충전 방식 버튼
        mode_frame = ttk.Frame(self.root)
        mode_frame.pack(fill="x", padx=20, pady=10)

        ttk.Button(
            mode_frame,
            text="자동 추천",
            command=self.set_auto
        ).pack(side="left", padx=5)

        ttk.Button(
            mode_frame,
            text="완속",
            command=self.set_slow
        ).pack(side="left", padx=5)

        ttk.Button(
            mode_frame,
            text="급속",
            command=self.set_fast
        ).pack(side="left", padx=5)


        # 차량 상태 진단
        diagnosis_frame = ttk.LabelFrame(
            self.root,
            text="차량 배터리 상태 진단"
        )
        diagnosis_frame.pack(fill="x", padx=20, pady=10)

        ttk.Label(
            diagnosis_frame,
            text="차량 ID"
        ).pack(side="left", padx=10, pady=10)

        self.vehicle_id_entry = ttk.Entry(diagnosis_frame, width=18)
        self.vehicle_id_entry.pack(side="left", padx=5, pady=10)
        self.vehicle_id_entry.insert(0, "EV135476")

        ttk.Label(
            diagnosis_frame,
            text="브랜드",
        ).pack(side="left", padx=(10, 5), pady=10)

        self.brand_var = tk.StringVar(value="Tesla")
        self.brand_combo = ttk.Combobox(
            diagnosis_frame,
            textvariable=self.brand_var,
            values=("Tesla", "Volkswagen", "Nissan"),
            state="readonly",
            width=12,
        )
        self.brand_combo.pack(side="left", padx=5, pady=10)

        ttk.Button(
            diagnosis_frame,
            text="진단",
            command=self.start_diagnosis,
        ).pack(side="left", padx=5, pady=10)

        self.diagnosis_label = ttk.Label(
            diagnosis_frame,
            text="진단 결과: -"
        )
        self.diagnosis_label.pack(side="left", padx=20)

        self.diagnosis_message_label = ttk.Label(
            self.root,
            text="차량 ID를 입력하면 조회용 CSV 데이터로 진단합니다."
        )
        self.diagnosis_message_label.pack(
            anchor="w",
            padx=20,
            pady=(0, 5)
        )


        # 상태 메시지
        self.status_label = ttk.Label(
            self.root,
            text="위치를 입력해주세요."
        )
        self.status_label.pack(
            anchor="w",
            padx=20,
            pady=10
        )


        # 충전소 표
        columns = (
            "name",
            "address",
            "available",
            "slow",
            "fast"
        )

        self.tree = ttk.Treeview(
            self.root,
            columns=columns,
            show="headings",
            height=5
        )

        self.tree.heading(
            "name",
            text="충전소명"
        )

        self.tree.heading(
            "address",
            text="주소"
        )

        self.tree.heading(
            "available",
            text="전체"
        )

        self.tree.heading(
            "slow",
            text="완속"
        )

        self.tree.heading(
            "fast",
            text="급속"
        )

        self.tree.column(
            "name",
            width=180,
            stretch=False,
        )

        self.tree.column(
            "address",
            width=360,
            stretch=False,
        )

        self.tree.column(
            "available",
            width=70,
            anchor="center",
            stretch=False,
        )

        self.tree.column(
            "slow",
            width=70,
            anchor="center",
            stretch=False,
        )

        self.tree.column(
            "fast",
            width=70,
            anchor="center",
            stretch=False,
        )

        self.tree.pack(
            fill="x",
            expand=False,
            padx=20,
            pady=10
        )


        # 추천 서비스센터 표
        self.center_title = ttk.Label(
            self.root,
            text="추천 서비스센터"
        )
        self.center_title.pack(anchor="w", padx=20, before=self.tree)

        center_columns = (
            "name",
            "address",
            "phone",
            "brand"
        )

        self.center_tree = ttk.Treeview(
            self.root,
            columns=center_columns,
            show="headings",
            height=5
        )

        self.center_tree.heading("name", text="서비스센터명")
        self.center_tree.heading("address", text="주소")
        self.center_tree.heading("phone", text="전화번호")
        self.center_tree.heading("brand", text="브랜드")

        self.center_tree.column("name", width=230)
        self.center_tree.column("address", width=480)
        self.center_tree.column("phone", width=150, anchor="center")
        self.center_tree.column("brand", width=120, anchor="center")

        self.center_tree.pack(
            fill="x",
            padx=20,
            pady=(5, 15),
            before=self.tree,
        )


    def start_search(self):
        location = self.location_entry.get().strip()

        if location == "":
            messagebox.showwarning(
                "입력 오류",
                "현재 위치를 입력해주세요."
            )
            return

        self.status_label.config(
            text="조회 중..."
        )

        mode = self.mode
        thread = threading.Thread(
            target=self.load_data,
            args=(location, mode)
        )

        thread.daemon = True
        thread.start()


    def load_data(self, location, mode):
        try:
            response = requests.post(
                f"{BACKEND_BASE_URL}/api/v1/recommendations",
                json={
                    "location": location,
                    "mode": mode,
                    "limit": 5,
                },
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            result = response.json()
        except requests.HTTPError as error:
            try:
                message = response.json().get("detail", str(error))
            except ValueError:
                message = str(error)
            self.root.after(
                0,
                self.show_error,
                message,
            )
            return
        except (requests.RequestException, ValueError):
            self.root.after(
                0,
                self.show_error,
                "FastAPI 서버에 연결하지 못했습니다. 서버 실행 상태를 확인해 주세요.",
            )
            return

        self.temperature = result.get("temperature")
        self.requested_mode = result.get("requested_mode", mode)
        self.recommended_mode = result.get("recommended_mode")
        self.stations = result.get("stations", [])

        self.root.after(
            0,
            self.show_result
        )


    def show_result(self):
        if self.temperature is not None:
            self.temperature_label.config(
                text=(
                    f"현재 기온: "
                    f"{self.temperature:.1f}℃"
                )
            )
        else:
            self.temperature_label.config(
                text="현재 기온: 조회 실패"
            )

        if self.recommended_mode == "slow":
            mode_text = "완속"
        else:
            mode_text = "급속"

        if self.requested_mode == "auto":
            self.recommend_label.config(
                text=f"추천 충전 방식: {mode_text}"
            )
        else:
            self.recommend_label.config(
                text=f"선택한 충전 방식: {mode_text}"
            )

        self.status_label.config(
            text=(
                f"충전소 "
                f"{len(self.stations)}곳 검색 완료"
            )
        )

        self.update_station_list()


    def set_auto(self):
        self.mode = "auto"
        self.start_search()


    def set_slow(self):
        self.mode = "slow"
        self.start_search()


    def set_fast(self):
        self.mode = "fast"
        self.start_search()


    def start_diagnosis(self):
        location = self.location_entry.get().strip()
        vehicle_id = self.vehicle_id_entry.get().strip()
        brand = self.brand_var.get()

        if location == "":
            messagebox.showwarning("입력 오류", "현재 위치를 입력해주세요.")
            return

        if vehicle_id == "":
            messagebox.showwarning("입력 오류", "차량 ID를 입력해주세요.")
            return

        self.diagnosis_label.config(
            text=f"진단 결과: {vehicle_id} 분석 중..."
        )
        self.diagnosis_message_label.config(
            text="차량 모델을 실행하고 있습니다."
        )

        thread = threading.Thread(
            target=self.load_diagnosis,
            args=(vehicle_id, location, brand),
            daemon=True,
        )
        thread.start()


    def load_diagnosis(self, vehicle_id, location, brand):
        try:
            response = requests.post(
                f"{BACKEND_BASE_URL}/api/v1/diagnoses",
                json={
                    "vehicle_id": vehicle_id,
                    "location": location,
                    "brand": brand,
                },
                timeout=60,
            )
            response.raise_for_status()
            result = response.json()
        except requests.HTTPError as error:
            try:
                message = response.json().get("detail", str(error))
            except ValueError:
                message = str(error)
            self.root.after(
                0,
                self.show_diagnosis_error,
                message,
            )
            return
        except (requests.RequestException, ValueError):
            self.root.after(
                0,
                self.show_diagnosis_error,
                "FastAPI 서버에 연결하지 못했습니다.",
            )
            return

        self.root.after(
            0,
            self.show_diagnosis,
            result,
        )


    def show_diagnosis(self, result):
        status_text = {
            "normal": "정상",
            "abnormal": "이상 감지",
            "unknown": "판정 보류",
        }.get(result.get("status"), "알 수 없음")

        probability = result.get("probability")
        probability_text = (
            f" · 불량 확률 {probability * 100:.1f}%"
            if probability is not None
            else ""
        )

        self.diagnosis_label.config(
            text=(
                f"진단 결과: {result.get('vehicle_id')} · "
                f"{status_text} · 모델 출력 {result.get('prediction')}"
                f"{probability_text}"
            )
        )
        self.diagnosis_message_label.config(
            text=result.get("message", "")
        )
        self.display_service_centers(result.get("service_centers", []))


    def show_diagnosis_error(self, message):
        self.diagnosis_label.config(
            text="진단 결과: 실행 실패"
        )
        self.diagnosis_message_label.config(text=message)
        self.display_service_centers([])


    def display_service_centers(self, centers):
        for item in self.center_tree.get_children():
            self.center_tree.delete(item)

        for center in centers:
            self.center_tree.insert(
                "",
                "end",
                values=(
                    center.get("name"),
                    center.get("address"),
                    center.get("phone"),
                    center.get("brand"),
                )
            )


    def update_station_list(self):
        self.display_stations(self.stations)


    def display_stations(self, stations):

        # 기존 데이터 삭제
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 새 데이터 출력
        for station in stations:

            self.tree.insert(
                "",
                "end",
                values=(
                    station.get("name"),
                    station.get("address"),
                    station.get("available"),
                    station.get("slow_available"),
                    station.get("fast_available")
                )
            )


    def show_error(self, message):

        self.status_label.config(
            text="조회 실패"
        )

        messagebox.showerror(
            "오류",
            message
        )


def main():
    root = tk.Tk()

    app = EVChargingApp(root)

    root.mainloop()


if __name__ == "__main__":
    main()
