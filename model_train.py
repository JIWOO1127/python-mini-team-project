import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
from imblearn.under_sampling import RandomUnderSampler
import xgboost as xgb
from google.colab import files

#변수설정 과정 코드는 따로 있음 필요하다면 드리겠습니다.
df=pd.read_csv("df_cleaned_nocenter.csv")

# ── 1. 통합 변수 정의 ─────────────────────────────────────
final_cols = [
    'manufacturing_year', 'odometer_km', 'cycle_count',
    'battery_health_percent', 'internal_resistance', 'charge_efficiency',
    'remaining_capacity', 'charging_cycles_last_month', 'fast_charge_ratio',
    'average_trip_distance', 'daily_distance', 'cooling_system_health',
    'thermal_runaway_risk', 'voltage_imbalance', 'battery_stress_index',
    'thermal_health_score', 'charging_quality_score',
    'predicted_remaining_life_cycles'
]

# ── 2. 3개 브랜드 데이터 합치기 ───────────────────────────
brands = ['Tesla', 'Volkswagen', 'Nissan']
# ✅ 수정 - vehicle_id 추가
df_merged = df[df['vehicle_brand'].isin(brands)][final_cols + ['battery_failure', 'vehicle_brand', 'vehicle_id']].copy()

print(f"통합 데이터: {df_merged.shape}")
print(df_merged['vehicle_brand'].value_counts())
print(f"\n불량 분포:\n{df_merged['battery_failure'].value_counts()}")

# ── 3. 결측치 보정 (중앙값) ───────────────────────────────
for col in final_cols:
    df_merged[col] = df_merged[col].fillna(df_merged[col].median())

# ── 4. 이상치 제거 (정상 클래스만 IQR) ───────────────────
df_normal  = df_merged[df_merged['battery_failure'] == 0].copy()
df_failure = df_merged[df_merged['battery_failure'] == 1].copy()

for col in final_cols:
    Q1, Q3 = df_normal[col].quantile([0.25, 0.75])
    IQR = Q3 - Q1
    df_normal = df_normal[
        (df_normal[col] >= Q1 - 1.5 * IQR) &
        (df_normal[col] <= Q3 + 1.5 * IQR)
    ]

df_clean = pd.concat([df_normal, df_failure], ignore_index=True)
print(f"\n이상치 제거 후: {df_clean.shape}")
print(f"정상: {(df_clean['battery_failure']==0).sum()} / 불량: {(df_clean['battery_failure']==1).sum()}")

# ── 5. Train / Val / Test 분리 (60/20/20) ─────────────────
X = df_clean[final_cols]
y = df_clean['battery_failure']

X_train, X_temp, y_train, y_temp = train_test_split(
    X, y, test_size=0.4, stratify=y, random_state=42)
X_val, X_test, y_val, y_test = train_test_split(
    X_temp, y_temp, test_size=0.5, stratify=y_temp, random_state=42)

# ── test 저장 시 vehicle_id 포함 ──────────────────────────
# X_test에는 vehicle_id가 없으니까 원본에서 가져와야 해요
vehicle_ids_test = df_clean.loc[X_test.index, 'vehicle_id'].values

X_test_save = X_test.copy()
X_test_save.insert(0, 'vehicle_id', vehicle_ids_test)
X_test_save['battery_failure'] = y_test.values
X_test_save.to_csv('merged_test.csv', index=False)

print(f"\nTrain {X_train.shape} | Val {X_val.shape} | Test {X_test.shape}")
print(f"Train 정상: {(y_train==0).sum()} / 불량: {(y_train==1).sum()}")

# ── 6. Undersampling (정상:불량 = 2:1) ───────────────────
rus = RandomUnderSampler(sampling_strategy=0.5, random_state=42)
X_train_res, y_train_res = rus.fit_resample(X_train, y_train)

print(f"\nUndersampling 후 → 정상: {(y_train_res==0).sum()} / 불량: {(y_train_res==1).sum()}")

# ── 7. XGBoost 학습 ───────────────────────────────────────
model = xgb.XGBClassifier(
    n_estimators=200,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    eval_metric='logloss',
    early_stopping_rounds=20,
    random_state=42
)
model.fit(
    X_train_res, y_train_res,
    eval_set=[(X_val, y_val)],
    verbose=50
)

# ── 8. 성능 평가 ──────────────────────────────────────────
def evaluate(X_data, y_data, name):
    y_pred = model.predict(X_data)
    y_prob = model.predict_proba(X_data)[:, 1]
    print(f"\n{'='*50}")
    print(f"  [{name}] 평가 결과")
    print(f"{'='*50}")
    print(classification_report(y_data, y_pred, target_names=['정상', '불량']))
    print(f"ROC-AUC: {roc_auc_score(y_data, y_prob):.4f}")

evaluate(X_val,  y_val,  "Validation")
evaluate(X_test, y_test, "Test")

# ── 9. 특성 중요도 Top 10 ─────────────────────────────────
feat_imp = pd.Series(model.feature_importances_, index=final_cols)
print("\n[ 특성 중요도 Top 10 ]")
print(feat_imp.sort_values(ascending=False).head(10).to_string())

# ── 10. 데이터셋 저장 & 다운로드 ─────────────────────────
def save_df(X_data, y_data, fname):
    tmp = X_data.copy()
    tmp['battery_failure'] = y_data.values
    tmp.to_csv(fname, index=False)

save_df(X_train_res, y_train_res, 'merged_train_final.csv')
save_df(X_val,       y_val,       'merged_val_final.csv')
save_df(X_test,      y_test,      'merged_test_final.csv')

files.download('merged_train_final.csv')
files.download('merged_val_final.csv')
print("\n다운로드 완료: merged_train / val / test.csv")