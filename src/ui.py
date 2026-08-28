"""Tkinter desktop UI for the EV battery diagnosis and infrastructure service."""

from __future__ import annotations

import os
import threading
import tkinter as tk
from tkinter import messagebox, ttk

import requests
from dotenv import load_dotenv


load_dotenv()

BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
REQUEST_TIMEOUT = 45

COLORS = {
    "navy": "#17253D",
    "blue": "#2F6FED",
    "blue_soft": "#EDF4FF",
    "background": "#F4F6F9",
    "panel": "#FFFFFF",
    "line": "#D7DEE8",
    "text": "#1F2937",
    "muted": "#6B7A8F",
    "green": "#087B56",
    "green_soft": "#EFFAF5",
    "red": "#D94355",
    "red_soft": "#FFF2F3",
}


class EVGuardApp:
    """A two-page Tkinter client that consumes the stable FastAPI contract."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("EV Guard | 배터리 진단 · 인프라 안내")
        self.root.geometry("1280x820")
        self.root.minsize(1040, 700)
        self.root.configure(bg=COLORS["background"])

        self.last_diagnosis: dict = {}
        self.sample_vehicle_id = ""
        self.active_page = "analysis"

        self._configure_style()
        self._build_shell()
        self._build_analysis_page()
        self._build_infrastructure_page()
        self.show_page("analysis")
        self.load_dashboard()

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("App.TFrame", background=COLORS["background"])
        style.configure("Card.TFrame", background=COLORS["panel"])
        style.configure("Header.TFrame", background=COLORS["panel"])
        style.configure(
            "Title.TLabel",
            background=COLORS["background"],
            foreground=COLORS["text"],
            font=("Malgun Gothic", 22, "bold"),
        )
        style.configure(
            "Subtitle.TLabel",
            background=COLORS["background"],
            foreground=COLORS["muted"],
            font=("Malgun Gothic", 10),
        )
        style.configure(
            "CardTitle.TLabel",
            background=COLORS["panel"],
            foreground=COLORS["text"],
            font=("Malgun Gothic", 12, "bold"),
        )
        style.configure(
            "CardSub.TLabel",
            background=COLORS["panel"],
            foreground=COLORS["muted"],
            font=("Malgun Gothic", 9),
        )
        style.configure(
            "Body.TLabel",
            background=COLORS["panel"],
            foreground=COLORS["text"],
            font=("Malgun Gothic", 10),
        )
        style.configure(
            "Muted.TLabel",
            background=COLORS["panel"],
            foreground=COLORS["muted"],
            font=("Malgun Gothic", 9),
        )
        style.configure(
            "Primary.TButton",
            background=COLORS["blue"],
            foreground="white",
            font=("Malgun Gothic", 10, "bold"),
            borderwidth=0,
            padding=(13, 9),
        )
        style.map("Primary.TButton", background=[("active", "#205ED5"), ("disabled", "#AFC8FA")])
        style.configure(
            "Secondary.TButton",
            background=COLORS["blue_soft"],
            foreground=COLORS["blue"],
            font=("Malgun Gothic", 10, "bold"),
            borderwidth=0,
            padding=(13, 9),
        )
        style.map("Secondary.TButton", background=[("active", "#DCEAFF")])
        style.configure(
            "Nav.TButton",
            background=COLORS["panel"],
            foreground=COLORS["muted"],
            borderwidth=0,
            font=("Malgun Gothic", 10, "bold"),
            padding=(15, 20),
        )
        style.map("Nav.TButton", background=[("active", COLORS["blue_soft"])])
        style.configure(
            "ActiveNav.TButton",
            background=COLORS["blue_soft"],
            foreground=COLORS["blue"],
            borderwidth=0,
            font=("Malgun Gothic", 10, "bold"),
            padding=(15, 20),
        )
        style.configure(
            "Treeview",
            background="white",
            foreground=COLORS["text"],
            rowheight=34,
            fieldbackground="white",
            font=("Malgun Gothic", 9),
            borderwidth=0,
        )
        style.configure(
            "Treeview.Heading",
            background="#F6F8FB",
            foreground="#4B5A6E",
            font=("Malgun Gothic", 9, "bold"),
            relief="flat",
        )
        style.map("Treeview", background=[("selected", COLORS["blue_soft"])], foreground=[("selected", COLORS["text"])])

    def _build_shell(self) -> None:
        header = ttk.Frame(self.root, style="Header.TFrame", padding=(28, 0))
        header.pack(fill="x")
        header.configure(height=64)
        header.pack_propagate(False)

        ttk.Label(
            header,
            text="EV ",
            style="CardTitle.TLabel",
            font=("Malgun Gothic", 16, "bold"),
        ).pack(side="left")
        tk.Label(
            header,
            text="GUARD",
            bg=COLORS["panel"],
            fg=COLORS["blue"],
            font=("Malgun Gothic", 16, "bold"),
        ).pack(side="left")

        self.analysis_nav = tk.Button(header, text="01  분석", command=lambda: self.show_page("analysis"), font=("Malgun Gothic", 10, "bold"), relief="flat", bd=0, padx=15, pady=12, cursor="hand2", highlightthickness=0)
        self.analysis_nav.pack(side="left", padx=(45, 2), pady=12)
        self.infrastructure_nav = tk.Button(header, text="02  충전/서비스", command=lambda: self.show_page("infrastructure"), font=("Malgun Gothic", 10, "bold"), relief="flat", bd=0, padx=15, pady=12, cursor="hand2", highlightthickness=0)
        self.infrastructure_nav.pack(side="left", padx=2, pady=12)

        tk.Label(
            header,
            text="●  REFERENCE DIAGNOSIS",
            bg=COLORS["panel"],
            fg="#5875AF",
            font=("Malgun Gothic", 8, "bold"),
        ).pack(side="right")

        self.content = ttk.Frame(self.root, style="App.TFrame", padding=(28, 25, 28, 20))
        self.content.pack(fill="both", expand=True)

    def _page_heading(self, parent: ttk.Frame, eyebrow: str, title: str, subtitle: str, step: str) -> None:
        heading = ttk.Frame(parent, style="App.TFrame")
        heading.pack(fill="x", pady=(0, 18))
        left = ttk.Frame(heading, style="App.TFrame")
        left.pack(side="left")
        tk.Label(left, text=eyebrow, bg=COLORS["background"], fg="#5673A9", font=("Malgun Gothic", 8, "bold")).pack(anchor="w")
        ttk.Label(left, text=title, style="Title.TLabel").pack(anchor="w", pady=(2, 2))
        ttk.Label(left, text=subtitle, style="Subtitle.TLabel").pack(anchor="w")
        ttk.Label(heading, text=step, style="Subtitle.TLabel").pack(side="right", anchor="s", pady=(0, 3))

    @staticmethod
    def _card(parent: ttk.Frame, title: str, subtitle: str, number: str) -> ttk.Frame:
        card = ttk.Frame(parent, style="Card.TFrame", padding=18)
        card.grid_propagate(True)
        head = ttk.Frame(card, style="Card.TFrame")
        head.pack(fill="x", pady=(0, 13))
        tk.Label(head, text=number, width=3, bg=COLORS["blue_soft"], fg=COLORS["blue"], font=("Malgun Gothic", 8, "bold")).pack(side="left", padx=(0, 8))
        text = ttk.Frame(head, style="Card.TFrame")
        text.pack(side="left")
        ttk.Label(text, text=title, style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(text, text=subtitle, style="CardSub.TLabel").pack(anchor="w")
        return card

    def _build_analysis_page(self) -> None:
        self.analysis_page = ttk.Frame(self.content, style="App.TFrame")
        self._page_heading(
            self.analysis_page,
            "BATTERY DIAGNOSIS",
            "전기차 배터리 상태 분석",
            "테스트 차량 ID로 모델 기반의 참고용 진단 결과를 확인합니다.",
            "STEP 1   차량 조회  →  상태 분석  →  인프라 안내",
        )
        grid = ttk.Frame(self.analysis_page, style="App.TFrame")
        grid.pack(fill="both", expand=True)
        grid.columnconfigure(0, weight=3, minsize=255)
        grid.columnconfigure(1, weight=5, minsize=380)
        grid.columnconfigure(2, weight=3, minsize=275)
        grid.rowconfigure(0, weight=1)

        input_card = self._card(grid, "차량 정보 입력", "테스트 데이터에서 조회합니다.", "01")
        input_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        ttk.Label(input_card, text="차량 ID", style="Body.TLabel").pack(anchor="w")
        self.vehicle_id_var = tk.StringVar()
        ttk.Entry(input_card, textvariable=self.vehicle_id_var).pack(fill="x", pady=(5, 14), ipady=7)
        ttk.Label(input_card, text="현재 주소  (선택)", style="Body.TLabel").pack(anchor="w")
        self.analysis_address_var = tk.StringVar()
        ttk.Entry(input_card, textvariable=self.analysis_address_var).pack(fill="x", pady=(5, 14), ipady=7)
        self.diagnose_button = ttk.Button(input_card, text="데이터 추출 및 분석 시작  →", style="Primary.TButton", command=self.start_diagnosis)
        self.diagnose_button.pack(fill="x")
        ttk.Button(input_card, text="테스트 차량 ID 자동 입력", style="Secondary.TButton", command=self.fill_sample_vehicle).pack(fill="x", pady=(8, 16))
        ttk.Separator(input_card, orient="horizontal").pack(fill="x", pady=(0, 14))
        ttk.Label(input_card, text="추출 데이터 미리보기", style="CardTitle.TLabel").pack(anchor="w")
        self.vehicle_preview = ttk.Frame(input_card, style="Card.TFrame")
        self.vehicle_preview.pack(fill="x", pady=(8, 0))
        self._replace_preview({"차량 ID": "입력 대기"})

        model_card = self._card(grid, "분석 모델 개요", "현재 활성 모델과 데이터 기준입니다.", "02")
        model_card.grid(row=0, column=1, sticky="nsew", padx=8)
        self.model_overview = ttk.Frame(model_card, style="Card.TFrame")
        self.model_overview.pack(fill="x")
        self.importance_frame = ttk.Frame(model_card, style="Card.TFrame")
        self.importance_frame.pack(fill="both", expand=True, pady=(16, 10))
        self.model_status_label = ttk.Label(model_card, text="모델 정보를 불러오는 중입니다...", style="Muted.TLabel", wraplength=370)
        self.model_status_label.pack(fill="x", pady=(4, 0))
        self.eda_label = ttk.Label(model_card, text="분석 정보를 불러오는 중입니다.", style="Muted.TLabel", wraplength=370)
        self.eda_label.pack(fill="x", pady=(8, 0))

        result_card = self._card(grid, "분석 결과", "입력 차량의 예측 결과입니다.", "03")
        result_card.grid(row=0, column=2, sticky="nsew", padx=(8, 0))
        self.status_box = tk.Label(result_card, text="배터리 상태\n분석 전\n차량 ID를 입력해주세요.", anchor="w", justify="left", bg="#F4F6F9", fg=COLORS["text"], padx=17, pady=18, font=("Malgun Gothic", 10))
        self.status_box.pack(fill="x")
        probability = ttk.Frame(result_card, style="Card.TFrame")
        probability.pack(fill="x", pady=18)
        ttk.Label(probability, text="고장 확률", style="Body.TLabel").pack(side="left")
        self.probability_label = tk.Label(probability, text="-", bg=COLORS["panel"], fg=COLORS["blue"], font=("Malgun Gothic", 16, "bold"))
        self.probability_label.pack(side="right")
        self.probability_bar = ttk.Progressbar(result_card, maximum=100, value=0)
        self.probability_bar.pack(fill="x")
        self.go_infrastructure_button = ttk.Button(result_card, text="내 주변 인프라 안내 보기  →", style="Secondary.TButton", command=self.use_diagnosis_for_infrastructure, state="disabled")
        self.go_infrastructure_button.pack(fill="x", pady=(20, 8))
        ttk.Label(result_card, text="합성 데이터 기반의 참고용 결과이며 실제 정비 확정 판정이 아닙니다.", style="Muted.TLabel", wraplength=250).pack(anchor="w")

        risk_card = ttk.Frame(self.analysis_page, style="Card.TFrame", padding=18)
        risk_card.pack(fill="x", pady=(14, 0))
        intro = ttk.Frame(risk_card, style="Card.TFrame")
        intro.pack(side="left", fill="y", padx=(0, 30))
        ttk.Label(intro, text="TOP 3 RISK SIGNALS", style="Muted.TLabel").pack(anchor="w")
        ttk.Label(intro, text="고위험 상태 지표", style="CardTitle.TLabel").pack(anchor="w", pady=(3, 4))
        ttk.Label(intro, text="기준 분포와 비교한 참고 지표입니다.", style="Muted.TLabel").pack(anchor="w")
        self.risk_frame = ttk.Frame(risk_card, style="Card.TFrame")
        self.risk_frame.pack(side="left", fill="both", expand=True)
        self._replace_risks([])

    def _build_infrastructure_page(self) -> None:
        self.infrastructure_page = ttk.Frame(self.content, style="App.TFrame")
        self._page_heading(
            self.infrastructure_page,
            "LOCAL INFRASTRUCTURE",
            "가까운 충전소와 서비스센터",
            "주소와 기온을 반영한 충전 방식, 제조사 공식 서비스센터를 함께 안내합니다.",
            "STEP 2   주소 변환  →  기온 확인  →  맞춤 안내",
        )
        grid = ttk.Frame(self.infrastructure_page, style="App.TFrame")
        grid.pack(fill="both", expand=True)
        grid.columnconfigure(0, weight=3, minsize=280)
        grid.columnconfigure(1, weight=8, minsize=600)
        grid.rowconfigure(0, weight=1)

        search_card = self._card(grid, "검색 조건", "주소와 제조사를 확인하세요.", "01")
        search_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        ttk.Label(search_card, text="기준 주소", style="Body.TLabel").pack(anchor="w")
        self.infrastructure_address_var = tk.StringVar()
        ttk.Entry(search_card, textvariable=self.infrastructure_address_var).pack(fill="x", pady=(5, 13), ipady=7)
        ttk.Label(search_card, text="제조사", style="Body.TLabel").pack(anchor="w")
        self.brand_var = tk.StringVar(value="Tesla")
        ttk.Combobox(search_card, textvariable=self.brand_var, values=("Tesla", "Nissan", "Volkswagen"), state="readonly").pack(fill="x", pady=(5, 13), ipady=5)
        ttk.Label(search_card, text="충전 방식", style="Body.TLabel").pack(anchor="w")
        self.mode_var = tk.StringVar(value="auto")
        mode = ttk.Combobox(search_card, textvariable=self.mode_var, values=("auto", "slow", "fast"), state="readonly")
        mode.pack(fill="x", pady=(5, 13), ipady=5)
        self.search_button = ttk.Button(search_card, text="주변 인프라 검색  →", style="Primary.TButton", command=self.start_infrastructure_search)
        self.search_button.pack(fill="x")
        self.weather_box = tk.Label(search_card, text="현재 온도\n-\n주소 입력 후 조회됩니다.", anchor="w", justify="left", bg=COLORS["navy"], fg="white", padx=16, pady=16, font=("Malgun Gothic", 10))
        self.weather_box.pack(fill="x", pady=(20, 0))
        ttk.Label(search_card, text="주소 → Kakao 좌표 변환 → KMA 온도 조회 → 추천 충전소 검색", style="Muted.TLabel", wraplength=230).pack(anchor="w", pady=(12, 0))

        results = ttk.Frame(grid, style="App.TFrame")
        results.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        results.rowconfigure(0, weight=1)
        results.rowconfigure(1, weight=1)
        results.columnconfigure(0, weight=1)
        charging_card = self._result_card(results, "CHARGING STATION", "추천 충전소", "온도 및 선택 방식에 맞는 상위 결과입니다.")
        charging_card.grid(row=0, column=0, sticky="nsew", pady=(0, 7))
        service_card = self._result_card(results, "OFFICIAL SERVICE CENTER", "공식 서비스센터", "제조사 공식 목록을 기준으로 검색합니다.")
        service_card.grid(row=1, column=0, sticky="nsew", pady=(7, 0))
        self.station_tree = self._build_tree(charging_card, ("name", "address", "available", "fast", "slow"), ("이름", "주소", "사용 가능", "급속", "완속"))
        self.center_tree = self._build_tree(service_card, ("name", "address", "distance", "phone"), ("센터명", "주소", "거리", "전화번호"))

    def _result_card(self, parent: ttk.Frame, eyebrow: str, title: str, subtitle: str) -> ttk.Frame:
        card = ttk.Frame(parent, style="Card.TFrame", padding=18)
        ttk.Label(card, text=eyebrow, style="Muted.TLabel").pack(anchor="w")
        ttk.Label(card, text=title, style="CardTitle.TLabel").pack(anchor="w", pady=(2, 2))
        ttk.Label(card, text=subtitle, style="CardSub.TLabel").pack(anchor="w", pady=(0, 10))
        return card

    @staticmethod
    def _build_tree(parent: ttk.Frame, columns: tuple[str, ...], headings: tuple[str, ...]) -> ttk.Treeview:
        tree = ttk.Treeview(parent, columns=columns, show="headings", height=5)
        widths = {"name": 155, "address": 320, "available": 78, "fast": 60, "slow": 60, "distance": 70, "phone": 120}
        for column, heading in zip(columns, headings):
            tree.heading(column, text=heading)
            tree.column(column, width=widths.get(column, 100), anchor="center" if column != "address" and column != "name" else "w")
        tree.pack(fill="both", expand=True)
        return tree

    def show_page(self, page: str) -> None:
        self.active_page = page
        self.analysis_page.pack_forget()
        self.infrastructure_page.pack_forget()
        if page == "analysis":
            self.analysis_page.pack(fill="both", expand=True)
            self._set_nav_state(self.analysis_nav, True)
            self._set_nav_state(self.infrastructure_nav, False)
        else:
            self.infrastructure_page.pack(fill="both", expand=True)
            self._set_nav_state(self.analysis_nav, False)
            self._set_nav_state(self.infrastructure_nav, True)

    @staticmethod
    def _set_nav_state(button: tk.Button, active: bool) -> None:
        button.configure(
            bg=COLORS["blue_soft"] if active else COLORS["panel"],
            fg=COLORS["blue"] if active else COLORS["muted"],
            activebackground="#DCEAFF" if active else "#F4F7FC",
            activeforeground=COLORS["blue"],
        )

    def fill_sample_vehicle(self) -> None:
        self.vehicle_id_var.set(self.sample_vehicle_id or "EV100001")

    def load_dashboard(self) -> None:
        self._run_async(self._get_dashboard, self._show_dashboard, self._show_dashboard_error)

    def _get_dashboard(self) -> dict:
        return self._request("GET", "/api/v1/dashboard")

    def _show_dashboard(self, data: dict) -> None:
        self.sample_vehicle_id = data.get("sample_vehicle_id", "")
        model = data.get("model", {})
        items = (
            ("모델 종류", model.get("model_type", "-")),
            ("모델 버전", model.get("version", "-")),
            ("입력 변수", f"{model.get('feature_count', '-')}개"),
            ("확률 제공", "지원" if model.get("probability_available") else "미지원"),
        )
        self._replace_key_values(self.model_overview, items)
        self._replace_importance(model.get("feature_importance") or [])
        eda = data.get("eda") or {}
        self.model_status_label.configure(text="모델 정보 로드 완료")
        self.eda_label.configure(text=eda.get("summary", "EDA 요약 정보가 없습니다."))

    def _show_dashboard_error(self, message: str) -> None:
        self.model_status_label.configure(text=f"모델 정보 로드 실패: {message}")
        self.eda_label.configure(text="서버 실행 상태와 활성 모델 파일을 확인해주세요.")
        self._show_error(message)

    def start_diagnosis(self) -> None:
        vehicle_id = self.vehicle_id_var.get().strip()
        if not vehicle_id:
            messagebox.showwarning("차량 ID 필요", "테스트 차량 ID를 입력해주세요.")
            return
        self.diagnose_button.configure(state="disabled", text="분석 중...")
        body = {"vehicle_id": vehicle_id, "address": self.analysis_address_var.get().strip() or None}
        self._run_async(lambda: self._request("POST", "/api/v1/diagnoses", body), self._show_diagnosis, self._show_diagnosis_error)

    def _show_diagnosis(self, data: dict) -> None:
        self.diagnose_button.configure(state="normal", text="데이터 추출 및 분석 시작  →")
        self.last_diagnosis = data
        is_abnormal = data.get("status") == "abnormal"
        status_text = "이상" if is_abnormal else "정상" if data.get("status") == "normal" else "판정 보류"
        box_color = COLORS["red_soft"] if is_abnormal else COLORS["green_soft"] if status_text == "정상" else "#F4F6F9"
        text_color = COLORS["red"] if is_abnormal else COLORS["green"] if status_text == "정상" else COLORS["text"]
        self.status_box.configure(text=f"배터리 상태\n{status_text}\n{data.get('brand', '-')} · {data.get('vehicle_id', '-')}", bg=box_color, fg=text_color)
        probability = data.get("probability")
        percentage = round(float(probability or 0) * 100, 1)
        self.probability_label.configure(text="미제공" if probability is None else f"{percentage:.1f}%")
        self.probability_bar.configure(value=percentage)
        self._replace_preview(data.get("vehicle_summary", {}))
        self._replace_risks(data.get("risk_factors", []))
        self.go_infrastructure_button.configure(state="normal")

    def _show_diagnosis_error(self, message: str) -> None:
        self.diagnose_button.configure(state="normal", text="데이터 추출 및 분석 시작  →")
        self._show_error(message)

    def use_diagnosis_for_infrastructure(self) -> None:
        self.infrastructure_address_var.set(self.analysis_address_var.get().strip())
        if self.last_diagnosis.get("brand") in ("Tesla", "Nissan", "Volkswagen"):
            self.brand_var.set(self.last_diagnosis["brand"])
        self.show_page("infrastructure")

    def start_infrastructure_search(self) -> None:
        address = self.infrastructure_address_var.get().strip()
        if not address:
            messagebox.showwarning("주소 필요", "기준 주소를 입력해주세요.")
            return
        self.search_button.configure(state="disabled", text="검색 중...")
        body = {"address": address, "mode": self.mode_var.get(), "limit": 3}
        center_body = {"address": address, "brand": self.brand_var.get(), "limit": 5}
        self._run_async(
            lambda: (
                self._request("POST", "/api/v1/charging-stations", body),
                self._request("POST", "/api/v1/service-centers", center_body),
            ),
            self._show_infrastructure,
            self._show_infrastructure_error,
        )

    def _show_infrastructure(self, result: tuple[dict, dict]) -> None:
        self.search_button.configure(state="normal", text="주변 인프라 검색  →")
        charging, centers = result
        temperature = charging.get("temperature_celsius")
        recommended = "완속" if charging.get("recommended_mode") == "slow" else "급속"
        temp_text = "-" if temperature is None else f"{float(temperature):.1f}°C"
        self.weather_box.configure(text=f"현재 온도\n{temp_text}\n{recommended} 충전을 권장합니다.")
        self._replace_tree(self.station_tree, charging.get("stations", []), ("name", "address", "available", "fast_available", "slow_available"))
        self._replace_tree(self.center_tree, centers.get("centers", []), ("name", "address", "distance_km", "phone"))

    def _show_infrastructure_error(self, message: str) -> None:
        self.search_button.configure(state="normal", text="주변 인프라 검색  →")
        self._show_error(message)

    def _request(self, method: str, path: str, body: dict | None = None) -> dict:
        response = requests.request(method, f"{BACKEND_BASE_URL}{path}", json=body, timeout=REQUEST_TIMEOUT)
        try:
            payload = response.json()
        except ValueError as error:
            raise RuntimeError("서버가 올바른 JSON 응답을 반환하지 않았습니다.") from error
        if not response.ok:
            raise RuntimeError(payload.get("detail", "요청을 처리하지 못했습니다."))
        return payload

    def _run_async(self, operation, on_success, on_error) -> None:
        def worker() -> None:
            try:
                result = operation()
            except (requests.RequestException, RuntimeError, ValueError) as error:
                self.root.after(0, on_error, str(error) or "요청 처리 중 오류가 발생했습니다.")
            else:
                def finish_success() -> None:
                    try:
                        on_success(result)
                    except Exception as error:
                        on_error(f"화면 표시 중 오류가 발생했습니다: {error}")
                self.root.after(0, finish_success)

        threading.Thread(target=worker, daemon=True).start()

    def _replace_preview(self, data: dict) -> None:
        labels = {
            "vehicle_brand": "제조사", "vehicle_model": "차량 모델", "battery_chemistry": "배터리",
            "odometer_km": "주행거리", "battery_health_percent": "배터리 건강도", "cycle_count": "충방전 횟수",
            "charging_quality_score": "충전 품질 점수", "internal_resistance": "내부 저항",
            "capacity_loss_percent": "용량 손실률",
        }
        self._replace_key_values(self.vehicle_preview, tuple((labels.get(key, key), value) for key, value in data.items()))

    def _replace_key_values(self, parent: ttk.Frame, items) -> None:
        for child in parent.winfo_children():
            child.destroy()
        for key, value in items:
            row = ttk.Frame(parent, style="Card.TFrame")
            row.pack(fill="x", pady=3)
            ttk.Label(row, text=str(key), style="Muted.TLabel").pack(side="left")
            ttk.Label(row, text=str(value), style="Body.TLabel").pack(side="right")

    def _replace_importance(self, items: list[dict]) -> None:
        for child in self.importance_frame.winfo_children():
            child.destroy()
        names = {"battery_health_percent": "배터리 건강도", "voltage_imbalance": "전압 불균형", "thermal_runaway_risk": "열폭주 위험도", "charging_quality_score": "충전 품질 점수"}
        for item in items[:7]:
            row = ttk.Frame(self.importance_frame, style="Card.TFrame")
            row.pack(fill="x", pady=4)
            ttk.Label(row, text=names.get(item.get("feature"), item.get("feature")), style="Muted.TLabel", width=19).pack(side="left")
            try:
                value = max(0.0, min(1.0, float(item.get("importance", 0) or 0)))
            except (TypeError, ValueError):
                value = 0.0
            ttk.Progressbar(row, maximum=1, value=value).pack(side="left", fill="x", expand=True, padx=8)
            ttk.Label(row, text=f"{value * 100:.0f}%", style="Muted.TLabel", width=5).pack(side="right")

    def _replace_risks(self, risks: list[dict]) -> None:
        for child in self.risk_frame.winfo_children():
            child.destroy()
        if not risks:
            ttk.Label(self.risk_frame, text="분석을 시작하면 상위 위험 지표 3개가 표시됩니다.", style="Muted.TLabel").pack(anchor="w", pady=14)
            return
        for item in risks[:3]:
            card = tk.Frame(self.risk_frame, bg="#FBFCFE", highlightbackground="#E1E7EF", highlightthickness=1, padx=14, pady=11)
            card.pack(side="left", fill="both", expand=True, padx=4)
            tk.Label(card, text=item.get("label", "-"), bg="#FBFCFE", fg=COLORS["text"], font=("Malgun Gothic", 10, "bold")).pack(anchor="w")
            tk.Label(card, text=f"{item.get('value', '-')} {item.get('unit', '')}", bg="#FBFCFE", fg="#4B5D74", font=("Malgun Gothic", 12, "bold")).pack(anchor="w", pady=(5, 2))
            tk.Label(card, text=f"위험도 {item.get('severity', 0)}%", bg="#FBFCFE", fg=COLORS["muted"], font=("Malgun Gothic", 8)).pack(anchor="w")

    @staticmethod
    def _replace_tree(tree: ttk.Treeview, rows: list[dict], fields: tuple[str, ...]) -> None:
        for item in tree.get_children():
            tree.delete(item)
        for row in rows:
            tree.insert("", "end", values=tuple(row.get(field, "-") if row.get(field) is not None else "-" for field in fields))

    @staticmethod
    def _show_error(message: str) -> None:
        messagebox.showerror("요청 실패", message or "서버 요청을 처리하지 못했습니다.")


def main() -> None:
    root = tk.Tk()
    EVGuardApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
