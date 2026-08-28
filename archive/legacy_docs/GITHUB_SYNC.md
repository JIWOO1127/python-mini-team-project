# EV Diag Final 공유본

이 폴더는 `JIWOO1127/python-mini-team-project` 원격 저장소의 `origin/main`
커밋 `ed5ab07`을 기준으로 최신 크롤링·데이터분석 파일을 반영한 공유 패키지입니다.

2026-08-27 업데이트: `model_ver2` 브랜치의 커밋 `be7caf5`를 반영했습니다.

- 활성 모델을 LightGBM ver2(`lgbm_battery_model.pkl`)로 교체했습니다.
- 15개 입력 변수, 학습 imputer, 고장 확률 0.2 임계값을 모델 어댑터가 사용합니다.
- LightGBM 테스트 차량 6,433건을 별도 번들로 추가했습니다.
- 차량 제조사·모델·배터리 표시는 기존 ID 메타데이터 파일과 연결해 유지합니다.
- 통합 API에서 폭스바겐 공식 목록이 비면 GitHub의 `crawler2.py`를 주소 기반 fallback으로 호출합니다.

반영한 주요 항목:

- `src/apis/temperature.py`: Kakao 주소 변환 및 KMA 격자·기온 조회
- `src/crawlers/`: 충전소·서비스센터 크롤링과 CSV 캐시 코드
- `src/ml/predictor.py`: 18개 입력 피처 순서 검증, 차량 ID 조회, XGBoost 예측·확률 계산
- `models/reviewed-xgb-3.2.0/battery_failure_model.pkl`: 원격 저장소 최신 모델
- `data/test/default/vehicles.csv`: 원격 저장소의 테스트 차량 6,433건

기존 확장형 FastAPI·Tkinter UI와 모델 매니페스트는 유지했으며, UI가 사용하는 API 계약은
변경하지 않았습니다. 모델 파일은 `model_manifest.json`의 SHA-256으로 검증됩니다.
