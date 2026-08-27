import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from matplotlib import font_manager

# ── 한글 폰트 설정 (Windows 기준) ────────────────────────
# Mac이면 'AppleGothic', Linux면 'NanumGothic'
matplotlib.rc('font', family='Malgun Gothic')
matplotlib.rcParams['axes.unicode_minus'] = False

df = pd.read_csv("df_cleaned_nocenter.csv")

brands    = ['Tesla', 'Nissan', 'Volkswagen']
threshold = 0.3

# ════════════════════════════════════════════════════════
# STEP 1. 브랜드별 상관변수 추출
# ════════════════════════════════════════════════════════
brand_results = {}   # 브랜드별 최종 변수 저장

for brand in brands:
    df_brand = df[df['vehicle_brand'] == brand].copy()
    num_cols = df_brand.select_dtypes(include='number').columns.tolist()

    # Step 1-1. battery_failure 상관계수
    corr = df_brand[num_cols].corr()['battery_failure'].drop('battery_failure')
    corr_df = pd.DataFrame({
        '상관계수': corr,
        '절대값':   corr.abs()
    }).sort_values('절대값', ascending=False)

    # Step 1-2. |r| >= 0.3 필터
    selected = corr_df[corr_df['절대값'] >= threshold].index.tolist()

    # Step 1-3. 다중공선성 제거
    feat_corr = df_brand[selected].corr().abs()
    upper     = feat_corr.where(~np.tril(np.ones(feat_corr.shape, dtype=bool)))
    drop_cols = set()
    for col in upper.columns:
        high = upper[col][upper[col] >= 0.9].index.tolist()
        for h in high:
            if corr_df.loc[col, '절대값'] >= corr_df.loc[h, '절대값']:
                drop_cols.add(h)
            else:
                drop_cols.add(col)

    final_cols = [c for c in selected if c not in drop_cols]

    brand_results[brand] = {
        'corr_df'   : corr_df,
        'selected'  : selected,
        'drop_cols' : drop_cols,
        'final_cols': final_cols,
    }

    print(f"\n{'='*55}")
    print(f"  {brand}")
    print(f"{'='*55}")
    print(f"  1차 선택 ({len(selected)}개, |r|≥{threshold}): {selected}")
    print(f"  다중공선성 제거: {sorted(drop_cols)}")
    print(f"  최종 변수 ({len(final_cols)}개): {final_cols}")


# ════════════════════════════════════════════════════════
# STEP 2. 브랜드별 상관계수 시각화
# ════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 3, figsize=(20, 7))
fig.suptitle('브랜드별 battery_failure 상관계수 (최종 선택 변수)',
             fontsize=15, fontweight='bold')

colors_pos = '#FF7B3A'
colors_neg = '#7B8EFF'

for ax, brand in zip(axes, brands):
    res      = brand_results[brand]
    corr_df  = res['corr_df']
    final    = res['final_cols']

    # 최종 변수만 필터링 후 정렬
    plot_df  = corr_df.loc[final].sort_values('상관계수')
    bar_cols = [colors_pos if v >= 0 else colors_neg
                for v in plot_df['상관계수']]

    bars = ax.barh(plot_df.index, plot_df['상관계수'],
                   color=bar_cols, alpha=0.85, height=0.6)

    # 값 레이블
    for bar, val in zip(bars, plot_df['상관계수']):
        offset = 0.005 if val >= 0 else -0.005
        ha     = 'left' if val >= 0 else 'right'
        ax.text(val + offset, bar.get_y() + bar.get_height()/2,
                f'{val:.3f}', va='center', ha=ha, fontsize=8.5)

    ax.axvline(0,          color='gray',  linewidth=0.8, linestyle='--')
    ax.axvline( threshold, color='green', linewidth=1.0, linestyle=':',
                alpha=0.6, label=f'+{threshold}')
    ax.axvline(-threshold, color='green', linewidth=1.0, linestyle=':',
                alpha=0.6, label=f'-{threshold}')

    ax.set_title(f'{brand}  ({len(final)}개 변수)', fontsize=12, fontweight='bold')
    ax.set_xlabel('상관계수', fontsize=10)
    ax.set_xlim(-0.85, 0.85)
    ax.grid(axis='x', alpha=0.3)
    ax.spines[['top', 'right']].set_visible(False)

plt.tight_layout()
plt.savefig('brand_correlation.png', dpi=150, bbox_inches='tight')
plt.show()
print("\n시각화 저장: brand_correlation.png")


# ════════════════════════════════════════════════════════
# STEP 3. 상관변수 합집합
# ════════════════════════════════════════════════════════
union_cols = set()
for brand in brands:
    union_cols.update(brand_results[brand]['final_cols'])

union_cols = sorted(union_cols)

print(f"\n{'='*55}")
print(f"  브랜드별 최종 변수 수")
print(f"{'='*55}")
for brand in brands:
    cols = brand_results[brand]['final_cols']
    print(f"  {brand:12s}: {len(cols)}개  {cols}")

print(f"\n  합집합 변수 ({len(union_cols)}개):")
for c in union_cols:
    in_brands = [b for b in brands if c in brand_results[b]['final_cols']]
    print(f"    {c:45s} ← {', '.join(in_brands)}")

# 합집합 변수로 데이터셋 생성
df_union = df[df['vehicle_brand'].isin(brands)][union_cols + ['battery_failure', 'vehicle_brand']].copy()
df_union.to_csv('df_union.csv', index=False)
print(f"\n합집합 데이터셋 저장: df_union.csv  {df_union.shape}")