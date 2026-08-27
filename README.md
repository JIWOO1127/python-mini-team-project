# EV Charging Assistant

현재 위치의 기온과 전기차 충전소 가용 정보를 조회하여 충전 방식을 추천하고, 차량 배터리 상태를 진단하는 Python 애플리케이션입니다. FastAPI 백엔드와 Tkinter 데스크톱 UI로 구성되어 있습니다.

## 주요 기능

- 입력한 주소를 좌표로 변환하고 기상청 초단기실황에서 현재 기온 조회
- 기온 또는 사용자 선택에 따라 완속·급속 충전 방식 결정
- ChargeCheck에서 주변 충전소와 사용 가능한 충전기 수 검색
- 충전 방식별 가용 충전기 수를 기준으로 충전소 정렬 및 추천
- 차량 ID로 샘플 CSV 데이터를 조회하고 XGBoost 모델로 배터리 상태 진단
- 이상 차량 진단 시 선택한 브랜드의 주변 서비스센터 검색
- 충전소 및 서비스센터 검색 결과를 CSV로 캐시
- FastAPI REST API와 Tkinter 데스크톱 UI 제공

## 실행 환경

- Python 3.11
- 인터넷 연결
- 서비스센터 검색 기능을 위한 Chrome 및 Selenium에서 사용할 수 있는 ChromeDriver
- 카카오 로컬 API REST API 키
- 공공데이터포털 기상청 단기예보 조회서비스의 서비스 키

## 설치

프로젝트 루트에서 Python 3.11 가상환경을 생성합니다.

### Windows PowerShell

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

PowerShell 실행 정책 때문에 활성화가 차단되면 현재 프로세스에만 정책을 적용한 후 다시 활성화합니다.

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### macOS/Linux

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 환경변수 설정

`.env.example`을 복사하여 프로젝트 루트에 `.env`를 만듭니다.

### Windows PowerShell

```powershell
Copy-Item .env.example .env
```

### macOS/Linux

```bash
cp .env.example .env
```

생성한 `.env`에 본인의 키와 백엔드 주소를 설정합니다.

```dotenv
KAKAO_REST_API_KEY=발급받은_카카오_REST_API_키
KMA_SERVICE_KEY=발급받은_기상청_서비스_키
BACKEND_BASE_URL=http://127.0.0.1:8000
```

- `KAKAO_REST_API_KEY`: 주소를 위도·경도로 변환할 때 사용합니다.
- `KMA_SERVICE_KEY`: 기상청 초단기실황에서 현재 기온을 조회할 때 사용합니다. Encoding 키와 Decoding 키 모두 처리할 수 있도록 코드에서 URL 디코딩합니다.
- `BACKEND_BASE_URL`: Tkinter UI가 호출할 FastAPI 서버 주소입니다. 생략하면 `http://127.0.0.1:8000`을 사용합니다.

`.env`는 `.gitignore`에 포함되어 있습니다. 실제 API 키를 README, 소스 코드 또는 Git 저장소에 기록하지 마세요.

## 실행

모든 명령은 가상환경을 활성화한 뒤 프로젝트 루트에서 실행합니다.

### FastAPI 서버

```powershell
uvicorn src.backend.main:app --reload
```

- 서버 기본 주소: `http://127.0.0.1:8000`
- 상태 확인: `http://127.0.0.1:8000/health`
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

### Tkinter UI

FastAPI 서버를 먼저 실행한 뒤 별도의 터미널에서 다음 명령을 실행합니다.

```powershell
python src/ui.py
```

UI에서는 위치와 충전 방식을 선택하여 충전소를 조회할 수 있습니다. 차량 ID, 위치, 브랜드를 입력하면 배터리 상태를 진단하고, 이상으로 판정된 경우 주변 서비스센터를 표시합니다.

## API 엔드포인트

### `GET /health`

서버가 실행 중인지 확인합니다.

응답 예시:

```json
{
  "status": "ok"
}
```

### `POST /api/v1/recommendations`

현재 기온을 조회하고 요청한 충전 방식에 맞는 충전소를 추천합니다.

요청 본문:

```json
{
  "location": "경기도 수원시 영통구 영통동",
  "mode": "auto",
  "limit": 3
}
```

| 필드 | 형식 | 설명 |
| --- | --- | --- |
| `location` | 문자열 | 검색할 주소. 빈 문자열은 허용되지 않습니다. |
| `mode` | `auto`, `slow`, `fast` | 기본값은 `auto`입니다. |
| `limit` | 정수 | 반환할 최대 충전소 수로, 1~10 범위이며 기본값은 3입니다. |

`auto` 모드는 현재 기온이 30°C 이상이면 `slow`, 그보다 낮으면 `fast`를 선택합니다. `slow` 또는 `fast`를 지정하면 기온은 조회하되 지정한 방식을 그대로 사용합니다.

응답 예시:

```json
{
  "location": "경기도 수원시 영통구 영통동",
  "temperature": 24.5,
  "requested_mode": "auto",
  "recommended_mode": "fast",
  "stations": [
    {
      "name": "충전소 이름",
      "address": "충전소 주소",
      "available": 5,
      "slow_available": 2,
      "fast_available": 3
    }
  ]
}
```

카카오 주소 조회, 기상청 조회 또는 ChargeCheck 조회가 실패하면 `502 Bad Gateway`를 반환합니다. 요청값이 스키마에 맞지 않으면 FastAPI가 `422 Unprocessable Entity`를 반환합니다.

### `POST /api/v1/diagnoses`

`data/vehicle_samples/vehicles.csv`에서 차량 ID를 찾고 저장된 모델로 배터리 상태를 진단합니다.

요청 본문:

```json
{
  "vehicle_id": "EV135476",
  "location": "경기도 수원시",
  "brand": "Tesla"
}
```

| 필드 | 형식 | 설명 |
| --- | --- | --- |
| `vehicle_id` | 문자열 | CSV에서 조회할 차량 ID. 대소문자를 구분하지 않습니다. |
| `location` | 문자열 | 이상 진단 시 서비스센터를 검색할 지역입니다. |
| `brand` | `Tesla`, `Volkswagen`, `Nissan` | 검색할 서비스센터 브랜드입니다. |

응답 예시:

```json
{
  "vehicle_id": "EV135476",
  "brand": "Tesla",
  "status": "abnormal",
  "prediction": "1",
  "probability": 0.82,
  "message": "배터리 불량 가능성이 감지되어 주변 서비스센터를 검색했습니다.",
  "service_centers": [
    {
      "name": "서비스센터 이름",
      "address": "서비스센터 주소",
      "phone": "전화번호",
      "link": "https://place.map.kakao.com/...",
      "brand": "Tesla"
    }
  ]
}
```

`status`는 모델 예측값에 따라 `normal`, `abnormal`, `unknown` 중 하나입니다. 실패 클래스 `1`의 확률을 구할 수 없는 모델에서는 `probability`가 `null`일 수 있습니다. 서비스센터는 `abnormal`인 경우에만 검색합니다.

- 모델 파일 또는 차량 CSV가 없으면 `503 Service Unavailable`
- 차량 ID를 찾을 수 없거나 데이터·모델 형식이 올바르지 않으면 `400 Bad Request`
- 요청값이 스키마에 맞지 않으면 `422 Unprocessable Entity`

## 전체 처리 흐름

### 충전소 검색 및 기온 조회

1. 클라이언트가 위치, 충전 모드, 결과 개수를 `/api/v1/recommendations`로 전송합니다.
2. 카카오 로컬 API가 주소를 위도·경도로 변환합니다.
3. 좌표를 기상청 격자 좌표로 변환하고 초단기실황 API에서 `T1H` 기온을 조회합니다.
4. `auto` 모드라면 30°C를 기준으로 완속 또는 급속을 선택합니다.
5. 동일 위치의 유효한 충전소 캐시가 있으면 재사용합니다. 캐시 유효시간은 10분입니다.
6. 캐시가 없으면 ChargeCheck를 조회하고 HTML에서 충전소 이름, 주소, 전체·급속 가용 수량을 추출합니다. 완속 가용 수량은 전체 가용 수량에서 급속 가용 수량을 빼서 계산합니다.
7. 선택한 충전 방식의 가용 충전기가 있는 충전소만 남기고 가용 수량 내림차순으로 정렬한 뒤 `limit`만큼 반환합니다.

충전소 캐시는 실행 중 `data/processed/charging_station_cache.csv`에 생성됩니다.

### 차량 진단

1. 클라이언트가 차량 ID, 위치, 브랜드를 `/api/v1/diagnoses`로 전송합니다.
2. `data/vehicle_samples/vehicles.csv`에서 차량 ID를 대소문자 구분 없이 조회합니다.
3. 모델 학습 때 사용한 18개 특성 순서로 한 행의 입력 데이터를 구성합니다.
4. `models/battery_failure_model.pkl`을 로드하여 예측값과 실패 클래스 확률을 계산합니다.
5. 예측값 `0`은 `normal`, `1`은 `abnormal`, 그 밖의 값은 `unknown`으로 변환합니다.
6. `abnormal`이면 Selenium의 headless Chrome으로 카카오맵에서 해당 지역과 브랜드의 서비스센터를 검색합니다.
7. 정확한 지역에서 결과를 찾지 못하면 첫 번째 지역명으로 검색 범위를 넓힙니다. 예를 들어 `경북 경산시`는 `경북`으로 다시 검색합니다.
8. 진단 결과와 필요한 경우 서비스센터 목록을 반환합니다.

서비스센터 캐시는 실행 중 `data/processed/service_center_cache.csv`에 생성되며, 동일 지역·브랜드의 저장된 결과를 우선 사용합니다.

## 프로젝트 구조

```text
python-mini-team-project/
├── .env.example                     # 환경변수 템플릿
├── requirements.txt                 # Python 의존성 목록
├── README.md                        # 프로젝트 문서
├── READ.md                          # 기존 프로젝트 메모
├── data/
│   ├── processed/                   # 실행 중 생성되는 CSV 캐시
│   ├── raw/                         # 원본 데이터 보관 위치
│   └── vehicle_samples/
│       └── vehicles.csv             # 차량 ID와 모델 입력 특성 데이터
├── models/
│   └── battery_failure_model.pkl    # 배터리 고장 진단 모델
├── src/
│   ├── ui.py                        # Tkinter 데스크톱 클라이언트
│   ├── apis/
│   │   └── temperature.py           # 주소 좌표 변환, 기온 조회 및 충전 모드 추천
│   ├── backend/
│   │   ├── main.py                  # FastAPI 앱과 엔드포인트
│   │   ├── schemas.py               # API 요청·응답 Pydantic 모델
│   │   └── services.py              # 추천 및 진단 유스케이스 조합
│   ├── crawlers/
│   │   ├── crawler.py               # ChargeCheck 충전소 검색과 정렬
│   │   ├── crawler2.py              # 카카오맵 서비스센터 검색과 캐시
│   │   └── charging_cache.py        # 충전소 검색 결과의 10분 CSV 캐시
│   └── ml/
│       └── predictor.py             # 차량 CSV 조회, 모델 로드 및 예측값 정규화
└── tests/
    ├── test_api.py                  # API 상태 코드와 응답 테스트
    ├── test_charging_cache.py       # 충전소 캐시 테스트
    ├── test_crawler2.py             # 서비스센터 유틸리티와 캐시 테스트
    ├── test_predictor.py            # 모델 입력 및 예측 처리 테스트
    └── test_services.py             # 추천·진단 서비스 테스트
```

## 테스트

가상환경에 의존성을 설치한 후 프로젝트 루트에서 실행합니다.

```powershell
pytest
```

상세한 테스트 이름을 함께 보려면 다음과 같이 실행합니다.

```powershell
pytest -v
```

테스트에서는 외부 API와 크롤러의 주요 호출을 모킹하므로 실제 API 키 없이도 대부분의 API·서비스 로직을 검증할 수 있습니다.

## XGBoost 모델 호환성 주의사항

이 프로젝트의 모델은 Python pickle 형식인 `models/battery_failure_model.pkl`로 저장되어 있습니다. pickle 모델은 저장할 때 사용한 라이브러리 버전과 로드할 때의 버전 차이에 민감합니다.

- 현재 `requirements.txt`는 `xgboost==3.2.0`과 `joblib==1.5.3`을 사용합니다.
- 임의로 XGBoost 버전을 변경하면 모델 로딩 오류, 경고 또는 예측 결과 차이가 발생할 수 있습니다.
- 새 환경에서는 반드시 프로젝트의 `requirements.txt`로 의존성을 설치하세요.
- 버전을 변경해야 한다면 원래 학습 환경에서 모델을 XGBoost의 안정적인 모델 형식으로 다시 저장하거나, 변경한 환경에서 모델 로딩과 예측 테스트를 먼저 수행하세요.
- 신뢰할 수 없는 출처의 pickle 파일은 임의 코드 실행 위험이 있으므로 로드하지 마세요.

## 외부 서비스

이 애플리케이션은 다음 외부 서비스의 응답과 페이지 구조에 의존합니다.

- 카카오 로컬 API: 주소 좌표 변환
- 기상청 단기예보 조회서비스: 현재 기온 조회
- ChargeCheck: 충전소 검색
- 카카오맵: 브랜드 서비스센터 검색

API 사용 권한, 네트워크 상태 또는 웹페이지 구조가 변경되면 관련 조회 기능이 실패할 수 있습니다.
=======
# python-mini-team-project
8/24~8/28 파이썬 미니 프로젝트