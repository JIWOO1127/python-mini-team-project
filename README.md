# EV 배터리 진단·충전/서비스 안내

FastAPI 백엔드와 Tkinter 데스크톱 UI로 만든 EV 배터리 진단 및 인프라 안내 서비스입니다. 활성 모델과 피처 계약은 `models/model_manifest.json`을 기준으로 관리합니다.

권장 실행 환경은 Python 3.13.15, LightGBM 4.7.0, XGBoost 3.2.0, Joblib 1.5.3, scikit-learn 1.7.2입니다. 버전 기준은 `runtime_versions.json`에 기록돼 있습니다.

## 기술 스택

![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![Uvicorn](https://img.shields.io/badge/Uvicorn-1F6F5C?style=flat-square)
![Pydantic](https://img.shields.io/badge/Pydantic-v2-E92063?style=flat-square&logo=pydantic&logoColor=white)
![Tkinter](https://img.shields.io/badge/Tkinter-3776AB?style=flat-square&logo=python&logoColor=white)

![LightGBM](https://img.shields.io/badge/LightGBM-4.7.0-2E7D32?style=flat-square)
![scikit-learn](https://img.shields.io/badge/scikit--learn-1.7.2-F7931E?style=flat-square&logo=scikitlearn&logoColor=white)
![pandas](https://img.shields.io/badge/pandas-150458?style=flat-square&logo=pandas&logoColor=white)
![joblib](https://img.shields.io/badge/joblib-1.5.3-5A6772?style=flat-square)

![Selenium](https://img.shields.io/badge/Selenium-43B02A?style=flat-square&logo=selenium&logoColor=white)
![BeautifulSoup](https://img.shields.io/badge/BeautifulSoup-4-8E44AD?style=flat-square)
![requests](https://img.shields.io/badge/requests-2C3E50?style=flat-square)
![pytest](https://img.shields.io/badge/pytest-0A9EDC?style=flat-square&logo=pytest&logoColor=white)

| 레이어 | 주요 기술 | 역할 |
| :--- | :--- | :--- |
| **데스크톱 UI** | `tkinter` · `threading` · `requests` | 2-Step 카드 UI, 비동기 워커로 네트워크 대기 중 화면 멈춤 방지 |
| **API 서버** | `FastAPI` · `Uvicorn` · `Pydantic v2` | REST 엔드포인트, 요청·응답 스키마 검증, Provider 인터페이스로 외부 API 변경 격리 |
| **ML 엔진** | `LightGBM 4.7.0` · `scikit-learn 1.7.2` · `joblib` | 배터리 고장 이진 분류(피처 15종, 임계값 0.2), Imputer 결측 보정, 모델 번들 직렬화 |
| **데이터 처리** | `pandas` | 차량 CSV 조회, 모델 입력 구성, 검색 결과 CSV 캐시 |
| **외부 수집** | `BeautifulSoup4` · `Selenium` | 충전소 HTML 파싱, 제조사 공식 카탈로그 수집(Headless Chrome) |
| **외부 API** | Kakao Local · 기상청 초단기실황 | 주소 → 위경도 지오코딩, 실시간 기온 기반 충전 방식 추천 |

## 시연 영상

https://github.com/user-attachments/assets/769426cb-e80e-4f8f-ba3e-7949a4edeb40

## 아키텍쳐
<img width="2000" height="1400" alt="ev-battery-service-architecture (2)" src="https://github.com/user-attachments/assets/041b194c-6eaf-4553-9df6-3861d604b1aa" />


## 주요 기능

- 테스트용 차량 ID를 이용한 배터리 정상/이상 예측, 고장 확률, 고위험 상태 지표 Top 3
- 모델 메타데이터, EDA 요약, 피처 중요도 대시보드
- Kakao Local API와 KMA 기상청 API를 이용한 온도 기반 충전 방식 추천
- 공식 제조사 카탈로그 기반 Tesla·Nissan·Volkswagen 서비스센터 검색
- 공급처, 수집 시각, 캐시 여부를 포함하는 정규화 응답

## 최초 환경 설정

프로젝트 폴더에서 `01_환경설정.cmd`를 한 번 실행합니다. PowerShell에서는 다음 명령도 사용할 수 있습니다.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

`.env`에 API 키를 입력합니다. 배터리 진단과 대시보드는 키 없이도 실행할 수 있지만 충전소·서비스센터 검색에는 키가 필요합니다.

```text
KAKAO_REST_API_KEY=
KMA_SERVICE_KEY=
BACKEND_BASE_URL=http://127.0.0.1:8000
```

## 실행

환경 설정 후에는 `03_프로그램실행.cmd`를 실행하면 백엔드와 데스크톱 UI가 함께 열립니다. 서버를 직접 관리해야 할 때만 `02_서버실행.cmd`를 별도 터미널에서 사용합니다.

```powershell
.\.venv\Scripts\python.exe run_app.py
```

런처가 시작한 서버는 UI가 종료될 때 함께 정리합니다. 이미 정상 실행 중인 서버나 원격 `BACKEND_BASE_URL`은 재사용하며 런처가 종료하지 않습니다.

기존 로컬 서버가 다른 `active_model`을 보고하면 재사용하지 않습니다. 구버전 서버를 종료하거나 `.env`의 포트를 변경한 뒤 다시 실행하세요.

## 모델·데이터

- 활성 모델: `models/lightgbm-ver2/lgbm_battery_model.pkl`
- 활성 manifest: `models/model_manifest.json`
- 진단 데이터: `data/test/lightgbm-ver2/vehicles.csv`
- 피처 profile: `data/test/lightgbm-ver2/feature_profile.json`

실행 배포에는 활성 모델과 위 테스트 번들만 필요합니다. 학습 원본 데이터와 과거 XGBoost 산출물은 예측 실행에 필요하지 않습니다. GitHub에 올릴 때 `.gitignore`에 의해 활성 `.pkl`·테스트 CSV가 빠지지 않았는지 확인하세요.

테스트 번들은 `python scripts\prepare_model_bundle.py`로 준비할 수 있습니다. `python scripts\train_default_model.py`는 XGBoost 결과를 `models/generated-xgb/`에 별도로 생성하며 활성 LightGBM manifest를 변경하지 않습니다.

## API

- `GET /health`
- `GET /api/v1/dashboard`
- `GET /api/v1/sample-vehicle` (활성 테스트 데이터셋에서 차량 ID를 무작위 반환)
- `POST /api/v1/diagnoses`
- `POST /api/v1/charging-stations`
- `POST /api/v1/service-centers`
- `POST /api/v1/recommendations` (호환용)

## 테스트

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

외부 API는 테스트에서 Mock 처리되며, 실제 서비스 호출은 별도로 수행해야 합니다.
