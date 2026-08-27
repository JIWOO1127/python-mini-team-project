"""공식 제조사 서비스센터 로컬 목록 검색 UI."""

from __future__ import annotations

import threading
import webbrowser

import customtkinter as ctk

from service_center_store import refresh_catalog, refresh_if_stale, search_centers


BG = "#F3F5F8"
NAVY = "#132238"
BLUE = "#2563EB"
GREEN = "#27804A"
RED = "#D32F2F"
MUTED = "#64748B"
BORDER = "#DDE3EA"
BRANDS = ["Nissan", "Volkswagen", "Tesla"]

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


class ServiceCenterApp(ctk.CTk):
    """지역과 제조사를 입력해 로컬 서비스센터 목록을 조회한다."""

    def __init__(self) -> None:
        super().__init__()
        self.title("EV 서비스센터 찾기")
        self.geometry("960x800")
        self.minsize(820, 650)
        self.configure(fg_color=BG)
        self.current_results: list[dict] = []
        self._build_ui()
        self.after(300, self._start_background_refresh)

    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, height=126, corner_radius=0, fg_color=NAVY)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(
            header, text="EV SERVICE NETWORK", font=("Arial", 12, "bold"),
            text_color="#7EA8FF",
        ).pack(anchor="w", padx=36, pady=(23, 3))
        ctk.CTkLabel(
            header, text="가까운 서비스센터 찾기", font=("맑은 고딕", 26, "bold"),
            text_color="white",
        ).pack(anchor="w", padx=36)
        ctk.CTkLabel(
            header, text="공식 제조사 목록을 로컬에서 검색하여 빠르게 안내합니다.",
            font=("맑은 고딕", 11), text_color="#C8D0DC",
        ).pack(anchor="w", padx=36, pady=(3, 0))

        search_card = ctk.CTkFrame(self, fg_color="white", corner_radius=16)
        search_card.pack(fill="x", padx=30, pady=(22, 10))
        search_card.grid_columnconfigure(0, weight=3)
        search_card.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            search_card, text="지역 또는 주소", font=("맑은 고딕", 11, "bold"),
            text_color=NAVY,
        ).grid(row=0, column=0, sticky="w", padx=(20, 8), pady=(16, 5))
        self.region_entry = ctk.CTkEntry(
            search_card, height=42, placeholder_text="예: 서울 강남구",
            font=("맑은 고딕", 11),
        )
        self.region_entry.grid(row=1, column=0, sticky="ew", padx=(20, 8), pady=(0, 18))
        self.region_entry.insert(0, "서울 강남구")

        ctk.CTkLabel(
            search_card, text="제조사", font=("맑은 고딕", 11, "bold"),
            text_color=NAVY,
        ).grid(row=0, column=1, sticky="w", padx=8, pady=(16, 5))
        self.brand_combo = ctk.CTkComboBox(
            search_card, values=BRANDS, state="readonly", height=42,
            font=("Arial", 11),
        )
        self.brand_combo.grid(row=1, column=1, sticky="ew", padx=8, pady=(0, 18))
        self.brand_combo.set("Tesla")
        self.search_button = ctk.CTkButton(
            search_card, text="서비스센터 검색", height=42, width=145,
            font=("맑은 고딕", 11, "bold"), command=self.start_search,
        )
        self.search_button.grid(row=1, column=2, padx=(8, 20), pady=(0, 18))

        status_row = ctk.CTkFrame(self, fg_color="transparent")
        status_row.pack(fill="x", padx=36, pady=(0, 8))
        self.status_label = ctk.CTkLabel(
            status_row, text="지역과 제조사를 선택해주세요.", text_color=MUTED,
            anchor="w", font=("맑은 고딕", 10),
        )
        self.status_label.pack(side="left", fill="x", expand=True)
        self.refresh_button = ctk.CTkButton(
            status_row, text="공식 목록 새로고침", width=126, height=28,
            fg_color="transparent", border_width=1, border_color="#C9D0D8",
            text_color=MUTED, font=("맑은 고딕", 9), command=self.start_refresh,
        )
        self.refresh_button.pack(side="right")

        self.recommendation_frame = ctk.CTkFrame(
            self, fg_color="#EAF1FF", border_width=1,
            border_color="#AFC7FF", corner_radius=15,
        )
        self.recommendation_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            self.recommendation_frame, text="RECOMMENDED", font=("Arial", 10, "bold"),
            text_color="#255CB8",
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(14, 2))
        self.best_name = ctk.CTkLabel(
            self.recommendation_frame, text="", font=("맑은 고딕", 18, "bold"),
            text_color="#172B4D",
        )
        self.best_name.grid(row=1, column=0, sticky="w", padx=20)
        self.best_detail = ctk.CTkLabel(
            self.recommendation_frame, text="", justify="left",
            font=("맑은 고딕", 10), text_color="#52647A",
        )
        self.best_detail.grid(row=2, column=0, sticky="w", padx=20, pady=(5, 14))
        self.best_button = ctk.CTkButton(
            self.recommendation_frame, text="공식 페이지 보기", width=140,
            height=38, font=("맑은 고딕", 10, "bold"),
        )
        self.best_button.grid(row=1, column=1, rowspan=2, padx=22)

        ctk.CTkLabel(
            self, text="검색 결과", font=("맑은 고딕", 16, "bold"),
            text_color="#20252B",
        ).pack(anchor="w", padx=36, pady=(10, 3))
        self.result_scroll = ctk.CTkScrollableFrame(self, fg_color=BG, corner_radius=0)
        self.result_scroll.pack(fill="both", expand=True, padx=24, pady=(0, 18))
        self.region_entry.bind("<Return>", lambda _event: self.start_search())

    def start_search(self) -> None:
        region = self.region_entry.get().strip()
        brand = self.brand_combo.get().strip()
        if not region:
            self.status_label.configure(text="검색할 지역을 입력해주세요.", text_color=RED)
            return
        self._clear_results()
        self.search_button.configure(state="disabled", text="검색 중...")
        self.status_label.configure(
            text=f"{region}의 {brand} 서비스센터를 검색하고 있습니다.", text_color=MUTED,
        )
        threading.Thread(
            target=self._search_worker, args=(region, brand), daemon=True,
        ).start()

    def _search_worker(self, region: str, brand: str) -> None:
        try:
            results = search_centers(region, brand, limit=20)
            self.after(0, lambda: self._show_results(region, brand, results))
        except Exception as exc:
            self.after(0, lambda error=str(exc): self._show_error(error))

    def _show_results(self, region: str, brand: str, results: list[dict]) -> None:
        self.current_results = results
        self.search_button.configure(state="normal", text="서비스센터 검색")
        if not results:
            self.status_label.configure(
                text=f"{region} 및 인접 지역에서 {brand} 서비스센터를 찾지 못했습니다.",
                text_color=RED,
            )
            ctk.CTkLabel(
                self.result_scroll, text="검색 결과가 없습니다.",
                font=("맑은 고딕", 14), text_color=MUTED,
            ).pack(pady=70)
            return

        if results[0].get("fallback") == "1":
            fallback_region = results[0].get("fallback_region", "인접")
            self.status_label.configure(
                text=(f"{region}에 센터가 없어 가장 가까운 "
                      f"{fallback_region} 지역 센터 {len(results)}개를 추천합니다."),
                text_color="#E67E22",
            )
        else:
            self.status_label.configure(
                text=f"{region}에서 {len(results)}개의 센터를 찾았습니다.",
                text_color=GREEN,
            )
        self._show_recommendation(results[0])
        for index, center in enumerate(results, start=1):
            self._create_result_card(index, center)

    def _show_recommendation(self, center: dict) -> None:
        self.best_name.configure(text=center.get("name", "서비스센터"))
        self.best_detail.configure(
            text=(f"주소  {center.get('address') or '정보 없음'}\n"
                  f"전화  {center.get('phone') or '정보 없음'}")
        )
        self.best_button.configure(command=lambda: self._open_center(center))
        self.recommendation_frame.pack(fill="x", padx=30, pady=(3, 4))

    def _create_result_card(self, index: int, center: dict) -> None:
        card = ctk.CTkFrame(
            self.result_scroll, fg_color="white", border_width=1,
            border_color=BORDER, corner_radius=12,
        )
        card.pack(fill="x", padx=7, pady=6)
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            card, text=f"{index}. {center.get('name', '서비스센터')}",
            font=("맑은 고딕", 13, "bold"), text_color="#20252B", anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=17, pady=(13, 3))
        ctk.CTkLabel(
            card,
            text=(f"주소  {center.get('address') or '정보 없음'}\n"
                  f"전화  {center.get('phone') or '정보 없음'}"),
            justify="left", anchor="w", font=("맑은 고딕", 10), text_color=MUTED,
        ).grid(row=1, column=0, sticky="ew", padx=17, pady=(0, 13))
        ctk.CTkButton(
            card, text="상세 보기", width=90, height=32, fg_color="transparent",
            border_width=1, border_color="#AFC7FF", text_color=BLUE,
            font=("맑은 고딕", 9, "bold"),
            command=lambda data=center: self._open_center(data),
        ).grid(row=0, column=1, rowspan=2, padx=17)

    def _clear_results(self) -> None:
        self.current_results = []
        self.recommendation_frame.pack_forget()
        for widget in self.result_scroll.winfo_children():
            widget.destroy()

    def _open_center(self, center: dict) -> None:
        link = center.get("link", "")
        if link:
            webbrowser.open(link)
        else:
            self.status_label.configure(text="제공된 상세 링크가 없습니다.", text_color=RED)

    def start_refresh(self) -> None:
        self.refresh_button.configure(state="disabled", text="갱신 중...")
        self.status_label.configure(text="공식 제조사 목록을 갱신하고 있습니다.", text_color=MUTED)
        threading.Thread(target=self._refresh_worker, daemon=True).start()

    def _refresh_worker(self) -> None:
        try:
            counts = refresh_catalog()
            message = (
                f"갱신 완료 · Nissan {counts.get('Nissan', 0)}개 · "
                f"Volkswagen {counts.get('Volkswagen', 0)}개 · "
                f"Tesla {counts.get('Tesla', 0)}개"
            )
            self.after(0, lambda: self._finish_refresh(message, GREEN))
        except Exception as exc:
            self.after(0, lambda error=str(exc): self._finish_refresh(f"갱신 실패: {error}", RED))

    def _finish_refresh(self, message: str, color: str) -> None:
        self.refresh_button.configure(state="normal", text="공식 목록 새로고침")
        self.status_label.configure(text=message, text_color=color)

    def _start_background_refresh(self) -> None:
        threading.Thread(target=refresh_if_stale, daemon=True).start()

    def _show_error(self, error: str) -> None:
        self.search_button.configure(state="normal", text="서비스센터 검색")
        self.status_label.configure(text=f"검색 중 오류가 발생했습니다: {error}", text_color=RED)


if __name__ == "__main__":
    ServiceCenterApp().mainloop()
