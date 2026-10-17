# app.py
import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="서울 기온 변화 분석", page_icon="🌡️", layout="wide")

# ============================================================
# 1) 데이터 로드 (파일명 자동 탐색)
# ============================================================
def find_csv_path():
    candidates = [
        "seoul_temperature.csv",
        "엑셀-seoul_temperature.csv",
        "/mnt/files/seoul_temperature.csv",
        "/mnt/files/엑셀-seoul_temperature.csv",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None

def load_data():
    path = find_csv_path()
    if path is None:
        st.error("온도 데이터 파일을 찾지 못했습니다.")
        st.info("Files 탭에 올린 파일명이 코드와 일치하는지 확인하세요.")
        st.stop()
    return pd.read_csv(path, encoding="utf-8-sig")

df = load_data()

기온_컬럼 = ["평균기온(℃)", "최저기온(℃)", "최고기온(℃)"]

# ============================================================
# 2) 데이터 전처리
# ============================================================
기온_있음 = df[기온_컬럼].notna().any(axis=1)
연도_기온일수 = 기온_있음.groupby(df["연도"]).sum()
유효_연도 = 연도_기온일수[연도_기온일수 >= 360].index
df = df[df["연도"].isin(유효_연도)]

# 연평균 (기온 값이 있는 날만 사용)
연평균 = df.groupby("연도")["평균기온(℃)"].mean().sort_index()

# 5년 이동평균: 5개 연도 모두 값이 있을 때만 계산 (중심 5년 기준)
이동평균 = 연평균.rolling(window=5, min_periods=5, center=True).mean().sort_index()

# 일교차 컬럼
df["일교차"] = df["최고기온(℃)"] - df["최저기온(℃)"]

# 계절 분류 (겨울 = 1·2·12월)
def assign_season(m):
    if 3 <= m <= 5:
        return "봄"
    if 6 <= m <= 8:
        return "여름"
    if 9 <= m <= 11:
        return "가을"
    return "겨울"

df["계절"] = df["월"].apply(assign_season)

def linear_fit(x, y):
    """단순 선형 회귀식 y = a + b*x 를 반환 (데이터 부족 시 None)"""
    n = len(x)
    if n < 2:
        return None
    mx = sum(x) / n
    my = sum(y) / n
    sxy = sum((x[i] - mx) * (y[i] - my) for i in range(n))
    sxx = sum((xi - mx) ** 2 for xi in x)
    if sxx == 0:
        return None
    b = sxy / sxx
    a = my - b * mx
    return a, b

# ============================================================
# 3) 사이드바: 연도 범위 슬라이더
# ============================================================
st.sidebar.header("연도 범위 선택")
min_year = int(연평균.index.min())
max_year = int(연평균.index.max())
선택_연도 = st.sidebar.slider("연도 범위", min_year, max_year, (min_year, max_year))

선택_mask = (df["연도"] >= 선택_연도[0]) & (df["연도"] <= 선택_연도[1])
df_선택 = df[선택_mask]

선택_평균 = df_선택["평균기온(℃)"].mean()
선택_최고 = df_선택["최고기온(℃)"].max()
선택_최저 = df_선택["최저기온(℃)"].min()
선택_일교차 = df_선택["일교차"].mean()

# ============================================================
# 4) 화면 구성
# ============================================================
st.title("서울의 기온 변화 분석")

st.markdown(
    """
- **연도 선별**: 기온 값이 있는 날이 360일 미만인 해는 연평균 계산에서 제외
- **5년 이동평균**: 5개 연도 모두 값이 있을 때만 계산 (중심 5년 기준)
- **추세선**: 연평균기온에 대한 선형 회귀선
- 값이 없는 연도는 꺾은선 그래프에서 선이 끊겨 표시됨
"""
)

if len(연평균) == 0:
    st.error("연평균 계산에 사용할 수 있는 연도가 없습니다. 데이터 파일을 확인해 주세요.")
    st.stop()

# ---------- 선택 구간 핵심 지표 ----------
c1, c2, c3, c4 = st.columns(4)
c1.metric("선택 구간 평균기온", f"{선택_평균:.2f} ℃")
c2.metric("선택 구간 최고기온", f"{선택_최고:.2f} ℃")
c3.metric("선택 구간 최저기온", f"{선택_최저:.2f} ℃")
c4.metric("선택 구간 평균 일교차", f"{선택_일교차:.2f} ℃")
st.caption(
    f"선택 구간: {선택_연도[0]}~{선택_연도[1]}년 | 데이터 {len(df_선택)}일 | "
    f"그래프는 선택한 연도 범위로 표시"
)

# ---------- 1. 연도별 평균기온 + 5년 이동평균 + 선형 추세선 ----------
연_선택 = 연평균[(연평균.index >= 선택_연도[0]) & (연평균.index <= 선택_연도[1])]
이_선택 = 이동평균[(이동평균.index >= 선택_연도[0]) & (이동평균.index <= 선택_연도[1])]

trend = linear_fit(list(연_선택.index), list(연_선택.values))

fig_annual = go.Figure()
fig_annual.add_trace(
    go.Scatter(
        x=연_선택.index, y=연_선택.values,
        mode="lines+markers", name="연평균기온",
        line=dict(color="#1f77b4", width=2.5),
    )
)
fig_annual.add_trace(
    go.Scatter(
        x=이_선택.index, y=이_선택.values,
        mode="lines+markers", name="5년 이동평균",
        line=dict(color="#d62728", width=2.5, dash="dash"),
    )
)
if trend is not None:
    a, b = trend
    trend_x = [연_선택.index.min(), 연_선택.index.max()]
    fig_annual.add_trace(
        go.Scatter(
            x=trend_x, y=[a + b * x for x in trend_x],
            name="선형 추세선", mode="lines",
            line=dict(color="#ff7f0e", width=2.5, dash="dash"),
        )
    )
fig_annual.update_layout(
    title="연도별 평균기온과 5년 이동평균 · 선형 추세선",
    xaxis_title="연도", yaxis_title="기온(℃)",
    hovermode="x unified",
    margin=dict(l=40, r=20, t=50, b=30),
)
st.plotly_chart(fig_annual, use_container_width=True)

# ---------- 2. 계절별 평균기온 ----------
계절별 = df.pivot_table(index="연도", columns="계절", values="평균기온(℃)", aggfunc="mean")
계절별 = 계절별[["봄", "여름", "가을", "겨울"]]

계절_색상 = {
    "봄": "#2ca02c",
    "여름": "#ff7f0e",
    "가을": "#d62728",
    "겨울": "#1f77b4",
}

fig_season = go.Figure()
for season in ["봄", "여름", "가을", "겨울"]:
    fig_season.add_trace(
        go.Bar(
            x=계절별.index, y=계절별[season],
            name=season, marker_color=계절_색상[season],
            hovertemplate=f"{season}: %{{y:.2f}} ℃<extra></extra>",
        )
    )
fig_season.update_layout(
    title="계절별 평균기온 (연도별)",
    xaxis_title="연도", yaxis_title="평균기온(℃)",
    barmode="group",
    legend_title="계절",
    margin=dict(l=40, r=20, t=50, b=30),
)
st.plotly_chart(fig_season, use_container_width=True)

계절_요약 = {s: df[df["계절"] == s]["평균기온(℃)"].mean() for s in ["봄", "여름", "가을", "겨울"]}
성_a, 성_b, 성_c, 성_d = st.columns(4)
성_a.metric("봄 평균기온", f"{계절_요약['봄']:.2f} ℃")
성_b.metric("여름 평균기온", f"{계절_요약['여름']:.2f} ℃")
성_c.metric("가을 평균기온", f"{계절_요약['가을']:.2f} ℃")
성_d.metric("겨울 평균기온", f"{계절_요약['겨울']:.2f} ℃")
st.caption("전체 기간 기준 계절별 평균기온 (겨울: 1·2·12월)")

# ---------- 3. 월별 히트맵 ----------
월별 = df.pivot_table(index="연도", columns="월", values="평균기온(℃)", aggfunc="mean")

fig_heatmap = go.Figure(
    go.Heatmap(
        z=월별.values,
        x=월별.columns.astype(int),
        y=월별.index,
        hovertemplate="연도=%{y}<br>월=%{x}<br>평균기온=%{z:.2f} ℃<extra></extra>",
    )
)
fig_heatmap.update_layout(
    title="월별 평균기온 히트맵",
    xaxis_title="월", yaxis_title="연도",
    coloraxis_colorbar_title="평균기온(℃)",
    margin=dict(l=40, r=20, t=50, b=30),
)
st.plotly_chart(fig_heatmap, use_container_width=True)

# ---------- 4. 기온 극단일 ----------
top10 = (
    df.nlargest(10, "최고기온(℃)")[["날짜", "평균기온(℃)", "최저기온(℃)", "최고기온(℃)"]]
    .copy()
)
top10["날짜"] = top10["날짜"].dt.strftime("%Y-%m-%d")

bottom10 = (
    df.nsmallest(10, "최저기온(℃)")[["날짜", "평균기온(℃)", "최저기온(℃)", "최고기온(℃)"]]
    .copy()
)
bottom10["날짜"] = bottom10["날짜"].dt.strftime("%Y-%m-%d")

c4a, c4b = st.columns(2)
with c4a:
    st.write("**최고기온 상위 10일**")
    st.dataframe(top10.style.format({"평균기온(℃)": "{:.2f}", "최저기온(℃)": "{:.2f}", "최고기온(℃)": "{:.2f}"}))
with c4b:
    st.write("**최저기온 하위 10일**")
    st.dataframe(bottom10.style.format({"평균기온(℃)": "{:.2f}", "최저기온(℃)": "{:.2f}", "최고기온(℃)": "{:.2f}"}))

# ---------- 5. 연평균 일교차 (연도별) ----------
일교차_연도 = df.groupby("연도")["일교차"].mean().sort_index()

fig_range = go.Figure()
fig_range.add_trace(
    go.Scatter(
        x=일교차_연도.index, y=일교차_연도.values,
        mode="lines+markers", name="평균 일교차",
        line=dict(color="#2ca02c", width=2.5),
    )
)
fig_range.update_layout(
    title="연도별 평균 일교차",
    xaxis_title="연도", yaxis_title="일교차(℃)",
    hovermode="x unified",
    margin=dict(l=40, r=20, t=40, b=30),
)
st.plotly_chart(fig_range, use_container_width=True)

# ---------- 6. 연간 기온 변화량 (전년대비) ----------
연간변화 = 연평균.diff().dropna()

fig_diff = go.Figure()
if len(연간변화) > 0:
    fig_diff.add_trace(
        go.Bar(
            x=연간변화.index, y=연간변화.values,
            name="연평균기온 변화량",
            marker_color=["#d62728" if v >= 0 else "#1f77b4" for v in 연간변화.values],
            hovertemplate="연도=%{x}<br>변화량=%{y:.2f} ℃<extra></extra>",
        )
    )
    fig_diff.update_layout(
        title="연도별 연평균기온 변화량 (전년대비)",
        xaxis_title="연도", yaxis_title="변화량(℃)",
        margin=dict(l=40, r=20, t=40, b=30),
    )
    st.plotly_chart(fig_diff, use_container_width=True)
else:
    st.info("변화를 계산할 수 있는 데이터가 부족합니다.")

# ---------- 7. 연도별 상세 데이터 ----------
with st.expander("연도별 상세 데이터 보기"):
    table = pd.DataFrame(
        {
            "연평균기온(℃)": 연평균,
            "5년 이동평균(℃)": 이동평균,
        }
    )
    table["봄"] = 계절별["봄"]
    table["여름"] = 계절별["여름"]
    table["가을"] = 계절별["가을"]
    table["겨울"] = 계절별["겨울"]
    st.dataframe(table.style.format("{:.2f}"))
