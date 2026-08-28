# EV 배터리 진단·충전/서비스 안내

FastAPI 백엔드와 Tkinter 데스크톱 UI로 만든 EV 배터리 진단 및 인프라 안내 서비스입니다. 모델과 외부 수집 제공자를 공통 인터페이스로 분리하여, 모델·크롤러·추천 정책을 교체해도 화면 및 API 계약을 유지합니다.

권장 실행 환경은 Python 3.13.15, XGBoost 3.2.0, Joblib 1.5.3, scikit-learn 1.6.1입니다. 버전 기준은 `runtime_versions.json`에 기록돼 있습니다.

## 주요 기능

- 테스트용 차량 ID를 이용한 배터리 정상/이상 예측, 고장 확률, 고위험 상태 지표 Top 3
- 모델 메타데이터, EDA 요약, 피처 중요도 대시보드
- 주소를 Kakao Local API로 좌표화하고 KMA 기상청 API의 온도에 따라 충전 방식을 추천
- 공식 제조사 카탈로그 기반 Tesla·Nissan·Volkswagen 서비스센터 검색
- 공급처, 수집 시각, 캐시 여부를 포함하는 정규화 응답

## 실행 방법

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

`.env`에 본인의 API 키를 설정합니다. `.env`는 Git에서 제외됩니다.

```text
KAKAO_REST_API_KEY=
KMA_SERVICE_KEY=
```

원본 데이터가 프로젝트 상위 폴더의 `archive/ev_battery_failure_dataset.csv`에 있다면 아래 명령으로 모델과 분리된 테스트 차량 번들을 준비합니다.

```powershell
python scripts\prepare_model_bundle.py
python scripts\train_default_model.py
```

다른 위치의 원본 데이터를 사용할 때는 `EV_SOURCE_DATA_PATH` 환경 변수를 설정합니다. 학습 스크립트는 테스트 차량 ID를 학습에서 제외합니다.

프로젝트 폴더에서 가상환경의 Uvicorn으로 백엔드를 실행합니다.

```powershell
cd "C:\Users\한국전파진흥협회\Desktop\DA\python-mini-team-project"
.\.venv\Scripts\uvicorn.exe src.backend.main:app --host 127.0.0.1 --port 8000
```

별도 PowerShell 창에서 아래 명령으로 데스크톱 앱을 엽니다.

```powershell
.\.venv\Scripts\python.exe -m src.ui
```

Tkinter 앱은 `http://127.0.0.1:8000`의 FastAPI 백엔드에 연결합니다. 다른 주소를 사용할 때는 `.env`에 `BACKEND_BASE_URL`을 설정합니다.

## API

- `GET /api/v1/dashboard`
- `POST /api/v1/diagnoses`
- `POST /api/v1/charging-stations`
- `POST /api/v1/service-centers`
- `GET /health`

## 확장 지점

- 모델: `src/ml/model_adapter.py`, `models/model_manifest.json`
- 외부 제공자: `src/providers/`
- 서비스 조합 및 추천 정책: `src/services/`, `config/providers.json`
- 데스크톱 UI: `src/ui.py`

생성된 모델 파일, 전체 테스트 데이터, 캐시와 API 키는 저장소에 포함하지 않습니다.
