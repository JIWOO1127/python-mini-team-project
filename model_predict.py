import joblib
import pandas as pd
import numpy as np

#model 가중치, test csv 파일 다운받아야 함
# ── 모델 & 테스트 데이터 로드 ─────────────────────────────
model   = joblib.load('ev_xgb_model_2.pkl')
df_test = pd.read_csv('merged_test_final.csv')   # vehicle_id 포함된 버전

final_cols = [
    'manufacturing_year', 'odometer_km', 'cycle_count',
    'battery_health_percent', 'internal_resistance', 'charge_efficiency',
    'remaining_capacity', 'charging_cycles_last_month', 'fast_charge_ratio',
    'average_trip_distance', 'daily_distance', 'cooling_system_health',
    'thermal_runaway_risk', 'voltage_imbalance', 'battery_stress_index',
    'thermal_health_score', 'charging_quality_score',
    'predicted_remaining_life_cycles'
]

def predict_by_id(vehicle_id):
    # ── 1. ID로 행 검색 ───────────────────────────────────
    row = df_test[df_test['vehicle_id'] == vehicle_id]

    if row.empty:
        print(f"❌ '{vehicle_id}' 는 테스트 데이터에 없어요.")
        print(f"   사용 가능한 ID 예시: {df_test['vehicle_id'].sample(5).tolist()}")
        return

    row = row.iloc[0]

    # ── 2. 18개 변수 추출 → float 변환 ───────────────────
    X_input = pd.DataFrame([row[final_cols].values],
                            columns=final_cols,
                            dtype=float)

    # ── 3. 결측치 처리 ───────────────────────────────────
    for col in final_cols:
        if X_input[col].isnull().any():
            X_input[col] = X_input[col].fillna(float(df_test[col].median()))

    # ── 4. 예측 ──────────────────────────────────────────
    proba  = model.predict_proba(X_input)[0]
    p_ok   = proba[0] * 100
    p_fail = proba[1] * 100
    pred   = '불량' if p_fail >= 50 else '정상'
    actual = '불량' if row['battery_failure'] == 1 else '정상'
    match  = '✅ 정답' if pred == actual else '❌ 오답'

    if p_fail >= 70:
        status, icon = '불량 위험 높음', '🔴'
    elif p_fail >= 40:
        status, icon = '주의 필요',      '🟡'
    else:
        status, icon = '정상',           '🟢'

    print("=" * 52)
    print(f"  차량 ID   : {vehicle_id}")
    print(f"  실제 정답 : {actual}  |  {match}")
    print("-" * 52)
    print(f"  {icon}  판정 결과 : {status}")
    print(f"  정상 확률 :  {p_ok:.2f}%  {'█' * int(p_ok  / 5)}")
    print(f"  불량 확률 :  {p_fail:.2f}%  {'█' * int(p_fail / 5)}")
    print("=" * 52)


# ── vehicle_id 입력받기 ───────────────────────────────────
vehicle_id = input("차량 ID를 입력하세요 (예: EV102835): ").strip()
predict_by_id(vehicle_id)