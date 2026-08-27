# AI Agent Operations

## EV Charging Assistant 실행

프로젝트 폴더에서 의존성을 설치합니다.

```powershell
pip install -r requirements.txt
```

`.env.example`을 참고해 `.env`에 API 키를 설정합니다. `.env`는 Git에 포함하지 않습니다.

첫 번째 터미널에서 FastAPI 백엔드를 실행합니다.

```powershell
uvicorn src.backend.main:app --reload
```

서버 상태는 `http://127.0.0.1:8000/health`, API 문서는
`http://127.0.0.1:8000/docs`에서 확인할 수 있습니다.

두 번째 터미널에서 Tkinter 프런트엔드를 실행합니다.

```powershell
python src/ui.py
```

UI는 `BACKEND_BASE_URL` 환경변수의 FastAPI 서버에 연결하며, 기본값은
`http://127.0.0.1:8000`입니다.

CSV 형식의 원본 데이터를 불러와 정제하고 분석하는 프로젝트입니다.

## 폴더 구조

- `data/raw`: 전달받은 원본 CSV 파일
- `data/processed`: 정제하거나 분석한 결과 데이터
- `models`: 향후 학습된 배터리 고장 예측 모델 저장
- `scripts`: Kaggle 커널 다운로드 스크립트
- `src`: 데이터 처리 및 분석 코드
- `src/ml`: 배터리 고장 예측 모델 코드
- `assets/images`: 분석 결과 이미지
- `assets/icons`: 프로젝트에서 사용하는 아이콘

## 실행 방법

1. `data/raw`에 분석할 CSV 파일을 넣습니다.
2. 필요한 패키지를 설치합니다.

   ```bash
   pip install -r requirements.txt
   ```

3. 프로젝트 폴더에서 분석 스크립트를 실행합니다.

   ```bash
   python src/analyze.py data/raw/파일명.csv
   ```

## EV 배터리 고장 예측 커널

Python 3.10 이상 환경에서 다음 순서로 실행합니다.

```bash
py -3.11 scripts/download_dataset.py
```

위 스크립트는 프로젝트 경로에 맞춰 다음 Kaggle CLI 명령을 실행합니다.

```bash
kaggle kernels pull aamir444/project-ev-battery-failure-prediction-binary-cl
```

실행 전 `kaggle auth login`으로 Kaggle CLI 인증이 필요합니다. 내려받은
노트북 소스와 메타데이터는 `notebook/ev_battery_failure`에 저장됩니다.

`kernels pull`은 커널의 소스 코드를 받는 명령입니다. 커널 실행 결과로
생성된 모델이나 데이터가 필요하면 `kaggle kernels output`을 사용해야 합니다.
