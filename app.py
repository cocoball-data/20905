# app.py
import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="서울 기온 변화 분석", page_icon="🌡️", layout="wide")


# ---------- 1. 파일 로드 ----------
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
    df = pd.read_csv(path, encoding="utf-8-sig")
    df["날짜"] = pd.to_datetime(
        df["날짜"].astype(str).str.replace('"', "", regex=False).str.strip(),
        format="%Y-%m-%d",
    )
    df["연도"] = df["날짜"].dt.year
    df["월"] = df["날짜"].dt.month
    return df


df = load_data()
원본_행수 = len(df)

기온_컬럼 = ["평균기온(℃)", "최저기온(℃)", "최고기온(℃)"]

# ---------- 2. 전처리 ----------
기온_있음 = df[기온_컬럼].notna().any(axis=1)
연도_기온일수 = 기온_있음.groupby(df["연도"]).sum()
유효_연도 = 연도_기온일수[연도_기온일수 >= 360].index
df = df[df["연도"].isin(유효_연도)]

연평균 = df.groupby("연도")["평균기온(℃)"].mean().sort_index()
이동평균 = 연평균.rolling(window=5, min_periods=5, center=True).mean().sort_index()

# 연도 범위 슬라이더에 필요한 최소/최대 연도
min_year = int(연평균.index.min())
max_year = int(연평균.index.max())

# 360일 미만 제외 연도 수
제외_연도수 = int((연도_기온일수 < 360).sum())

# 이상치(연평균 기준, 1.5×IQR) 연도
q1 = 연평균.quantile(0.25)
q3 = 연평균.quantile(0.75)
iqr = q3 - q1
이상치_연도 = 연평균[(연평균 < q1 - 1.5 * iqr) | (연평균 > q3 + 1.5 * iqr)].index.tolist()

df["일교차"] = df["최고기온(℃)"] - df["최저기온(℃)"]

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
    """단순 선형 회귀식 y = a + b*x 반환 (데이터 부족 시 None)"""
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

# ---------- 3. 선택 구간 ----------
선택_연도 = st.sidebar.slider("연도 범위", min_year, max_year, (min_year, max_year))

선택_mask = (df["연도"] >= 선택_연도[0]) & (df["연도"] <= 선택_연도[1])
df_선택 = df[선택_mask]

선택_평균 = df_선택["평균기온(℃)"].mean()
선택_최고 = df_선택["최고기온(℃)"].max()
선택_최저 = df_선택["최저기온(℃)"].min()
선택_일교차 = df_선택["일교차"].mean()

전체_평균 = df["평균기온(℃)"].mean()
기간_시작 = int(연평균.index.min())
기간_끝 = int(연평균.index.max())

# 선택 구간 기준 연/이동평균 (연간 차트·자동 요약 공용)
연_선택 = 연평균[(연평균.index >= 선택_연도[0]) & (연평균.index <= 선택_연도[1])]
이_선택 = 이동평균[(이동평균.index >= 선택_연도[0]) & (이동평균.index <= 선택_연도[1])]

# ---------- 4. 사이드바 ----------
st.sidebar.header("연도 범위 선택")
st.sidebar.slider("연도 범위", min_year, max_year, (min_year, max_year))

season = st.sidebar.selectbox("계절 필터", ["전체", "봄", "여름", "가을", "겨울"])

st.sidebar.header("그래프 표시 옵션")
show_연평균 = st.sidebar.checkbox("연평균기온 표시", value=True)
show_이동평균 = st.sidebar.checkbox("5년 이동평균", value=True)
show_추세선 = st.sidebar.checkbox("선형 추세선", value=True)
show_극단 = st.sidebar.checkbox("이상치(최고/최저 연도) 강조", value=True)

c1, c2 = st.sidebar.columns(2)
전체_csv = df.to_csv(index=False).encode("utf-8-sig")
선택_csv = df_선택.to_csv(index=False).encode("utf-8-sig")

with c1:
    st.download_button("전체 데이터 내보내기", data=전체_csv, file_name="seoul_temperature.csv", mime="text/csv")
with c2:
    st.download_button("선택 구간 내보내기", data=선택_csv, file_name=f"seoul_{선택_연도[0]}_{선택_연도[1]}.csv", mime="text/csv")

# ---------- 5. 화면 구성 ----------
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

c1, c2, c3, c4 = st.columns(4)
c1.metric("선택 구간 평균기온", f"{선택_평균:.2f} ℃")
c2.metric("선택 구간 최고기온", f"{선택_최고:.2f} ℃")
c3.metric("선택 구간 최저기온", f"{선택_최저:.2f} ℃")
c4.metric("선택 구간 평균 일교차", f"{선택_일교차:.2f} ℃")
st.caption(
    f"선택 구간: {선택_연도[0]}~{선택_연도[1]}년 | 데이터 {len(df_선택)}일 | "
    f"그래프는 선택한 연도 범위로 표시"
)

# ---------- 6. 데이터 정보 ----------
st.subheader("데이터 정보")
with st.expander("전처리 요약"):
    지점_목록 = sorted(df["지점"].unique().tolist()) if len(df) else []
    c1, c2 = st.columns(2)
    with c1:
        st.metric("시작 연도", f"{기간_시작}")
        st.metric("종료 연도", f"{기간_끝}")
        st.metric("총 데이터 행 수", f"{원본_행수}")
    with c2:
        st.metric("사용 연도 수", f"{len(연평균)}")
        st.metric("360일 미만 제외 연도 수", f"{제외_연도수}")
        st.metric("지점", " / ".join(map(str, 지점_목록)) if 지점_목록 else "없음")
    st.caption(
        "컬럼 설명 — 날짜: 관측일 | 평균기온(℃): 일평균기온 | "
        "최저기온(℃): 일최저기온 | 최고기온(℃): 일최고기온 | "
        "일교차 = 최고기온 − 최저기온 (앱에서 자동 계산)"
    )

# ---------- 7. 자동 요약 (통계 기반) ----------
st.subheader("자동 요약 (통계 기반)")
if len(연평균) > 0:
    summary_lines = [
        f"선택 구간({선택_연도[0]}~{선택_연도[1]}) 평균기온 {선택_평균:.2f}℃ | "
        f"최고기온 {선택_최고:.2f}℃ | 최저기온 {선택_최저:.2f}℃",
        f"전체 기간 평균기온 {전체_평균:.2f}℃ 대비 선택 구간 {선택_평균-전체_평균:+.2f}℃",
    ]
    trend_sel = linear_fit(list(연_선택.index), list(연_선택.values))
    if trend_sel is not None:
        summary_lines.append(f"연평균기온 추세선 기울기 {trend_sel[1]:+.2f}℃/년 (선택 구간 기준)")
    else:
        summary_lines.append("연평균기온 추세선: 데이터 부족 (계산 불가)")
    summary_lines.append(f"이상치(연평균 기준) {len(이상치_연도)}개")
    for line in summary_lines:
        st.markdown(f"• {line}")
else:
    st.info("계산할 데이터가 없습니다.")

# ---------- 8. 연간 차트 ----------
st.subheader("연도별 평균기온 (5년 이동평균 + 선형 추세선)")
st.caption("왼쪽 체크박스로 계열 표시 여부를 조절할 수 있습니다.")

fig_annual = go.Figure()
if show_연평균:
    fig_annual.add_trace(go.Scatter(
        x=연_선택.index, y=연_선택.values, mode="lines+markers",
        name="연평균기온", line=dict(color="#1f77b4", width=2.5)))
if show_이동평균:
    fig_annual.add_trace(go.Scatter(
        x=이_선택.index, y=이_선택.values, mode="lines+markers",
        name="5년 이동평균", line=dict(color="#d62728", width=2.5, dash="dash")))
if show_추세선 and trend_sel is not None:
    a, b = trend_sel
    trend_x = [연_선택.index.min(), 연_선택.index.max()]
    fig_annual.add_trace(go.Scatter(
        x=trend_x, y=[a + b * x for x in trend_x], mode="lines",
        name="선형 추세선", line=dict(color="#ff7f0e", width=2.5, dash="dash")))

차트에_표시 = show_연평균 or show_이동평균 or show_추세선
if show_극단 and 차트에_표시:
    hottest_year = int(연평균.idxmax()); hottest_val = float(연평균.max())
    coldest_year = int(연평균.idxmin()); coldest_val = float(연평균.min())
    fig_annual.add_trace(go.Scatter(
        x=[hottest_year], y=[hottest_val], mode="markers+text",
        name="가장 더운 해", marker=dict(color="#d62728", size=13),
        text=[f"가장 더운 해 · {hottest_val:.1f}℃"],
        textposition="top center", hovertemplate="%{y:.1f}℃<extra></extra>"))
    fig_annual.add_trace(go.Scatter(
        x=[coldest_year], y=[coldest_val], mode="markers+text",
        name="가장 추운 해", marker=dict(color="#1f77b4", size=13),
        text=[f"가장 추운 해 · {coldest_val:.1f}℃"],
        textposition="bottom center", hovertemplate="%{y:.1f}℃<extra></extra>"))

if 차트에_표시:
    fig_annual.update_layout(
        title="연도별 평균기온과 5년 이동평균 · 선형 추세선 (선택 구간)",
        xaxis_title="연도", yaxis_title="기온(℃)",
        hovermode="x unified", margin=dict(l=40, r=20, t=50, b=30),
    )
    st.plotly_chart(fig_annual, use_container_width=True)
else:
    st.info("그래프에 표시할 계열을 하나 이상 선택하세요.")

# ---------- 9. 계절별 ----------
st.subheader("계절별 평균기온")
계절별 = df.pivot_table(index="연도", columns="계절", values="평균기온(℃)", aggfunc="mean")
계절별 = 계절별[["봄", "여름", "가을", "겨울"]]

계절_월 = {"봄": [3, 4, 5], "여름": [6, 7, 8], "가을": [9, 10, 11], "겨울": [12, 1, 2]}
if season == "전체":
    seasons = ["봄", "여름", "가을", "겨울"]
else:
    seasons = [season]

계절_색상 = {"봄": "#2ca02c", "여름": "#ff7f0e", "가을": "#d62728", "겨울": "#1f77b4"}
계절_요약 = {s: df[df["계절"] == s]["평균기온(℃)"].mean() for s in seasons}

fig_season = go.Figure()
for s in seasons:
    fig_season.add_trace(go.Bar(
        x=계절별.index, y=계절별[s], name=s,
        marker_color=계절_색상[s],
        hovertemplate=f"{s}: %{{y:.2f}} ℃<extra></extra>"))

if season == "전체":
    c1, c2, c3, c4 = st.columns(4)
    for col, s in zip([c1, c2, c3, c4], seasons):
        with col:
            st.metric(f"{s} 평균기온", f"{계절_요약[s]:.2f} ℃")
else:
    st.metric(f"{season} 평균기온", f"{계절_요약[season]:.2f} ℃")

fig_season.update_layout(
    title="계절별 평균기온 (연도별)",
    xaxis_title="연도", yaxis_title="평균기온(℃)",
    barmode="group", legend_title="계절",
    margin=dict(l=40, r=20, t=50, b=30),
)
st.plotly_chart(fig_season, use_container_width=True)

# ---------- 10. 월별 히트맵 ----------
st.subheader("월별 히트맵")
월별 = df.pivot_table(index="연도", columns="월", values="평균기온(℃)", aggfunc="mean")
if season == "전체":
    월별_보기 = 월별
else:
    월별_보기 = 월별[계절_월[season]]

fig_heatmap = go.Figure(
    go.Heatmap(
        z=월별_보기.values,
        x=월별_보기.columns.astype(int),
        y=월별_보기.index,
        hovertemplate="연도=%{y}<br>월=%{x}<br>평균기온=%{z:.2f} ℃<extra></extra>",
    )
)
fig_heatmap.update_layout(
    title=f"월별 평균기온 히트맵 (계절: {season})",
    xaxis_title="월", yaxis_title="연도",
    coloraxis_colorbar_title="평균기온(℃)",
    margin=dict(l=40, r=20, t=50, b=30),
)
st.plotly_chart(fig_heatmap, use_container_width=True)

# ---------- 11. 월별 박스플롯 ----------
st.subheader("월별 분포")
fig_box = go.Figure()
fig_box.add_trace(go.Box(
    x=[f"{m}월" for m in range(1, 13)],
    y=df["평균기온(℃)"], name="평균기온",
    marker_color="#1f77b4",
))
fig_box.update_layout(
    title="월별 평균기온 분포 (전체 기간)",
    xaxis_title="월", yaxis_title="평균기온(℃)",
    margin=dict(l=40, r=20, t=40, b=30),
)
st.plotly_chart(fig_box, use_container_width=True)

# ---------- 12. 기온 극단일 ----------
st.subheader("기온 극단일 (최고/최저)")
top10 = df.nlargest(10, "최고기온(℃)")[["날짜", "평균기온(℃)", "최저기온(℃)", "최고기온(℃)"]].copy()
top10["날짜"] = top10["날짜"].dt.strftime("%Y-%m-%d")

bottom10 = df.nsmallest(10, "최저기온(℃)")[["날짜", "평균기온(℃)", "최저기온(℃)", "최고기온(℃)"]].copy()
bottom10["날짜"] = bottom10["날짜"].dt.strftime("%Y-%m-%d")

c4a, c4b = st.columns(2)
with c4a:
    st.write("**최고기온 상위 10일**")
    st.dataframe(top10.style.format({"평균기온(℃)": "{:.2f}", "최저기온(℃)": "{:.2f}", "최고기온(℃)": "{:.2f}"}))
with c4b:
    st.write("**최저기온 하위 10일**")
    st.dataframe(bottom10.style.format({"평균기온(℃)": "{:.2f}", "최저기온(℃)": "{:.2f}", "최고기온(℃)": "{:.2f}")})

# ---------- 13. 일교차 및 변화량 ----------
st.subheader("일교차 및 연평균 변화량")
col_r1, col_r2 = st.columns(2)

일교차_연도 = df.groupby("연도")["일교차"].mean().sort_index()
fig_range = go.Figure()
fig_range.add_trace(go.Scatter(
    x=일교차_연도.index, y=일교차_연도.values,
    mode="lines+markers", name="평균 일교차",
    line=dict(color="#2ca02c", width=2.5)))
fig_range.update_layout(
    title="연도별 평균 일교차",
    xaxis_title="연도", yaxis_title="일교차(℃)",
    margin=dict(l=40, r=20, t=40, b=30),
)
with col_r1:
    st.plotly_chart(fig_range, use_container_width=True)

연간변화 = 연평균.diff().dropna()
fig_diff = go.Figure()
if len(연간변화) > 0:
    fig_diff.add_trace(go.Bar(
        x=연간변화.index, y=연간변화.values, name="변화량",
        marker_color=["#d62728" if v >= 0 else "#1f77b4" for v in 연간변화.values],
        hovertemplate="연도=%{x}<br>변화량=%{y:.2f} ℃<extra></extra>"))
    fig_diff.update_layout(
        title="연평균기온 변화량 (전년대비)",
        xaxis_title="연도", yaxis_title="변화량(℃)",
        margin=dict(l=40, r=20, t=40, b=30),
    )
with col_r2:
    if len(연간변화) > 0:
        st.plotly_chart(fig_diff, use_container_width=True)
    else:
        st.info("변화를 계산할 수 있는 데이터가 부족합니다.")

# ---------- 14. 상세 데이터 ----------
with st.expander("연도별 상세 데이터 보기"):
    table = pd.DataFrame({
        "연평균기온(℃)": 연평균,
        "5년 이동평균(℃)": 이동평균,
    })
    table["이상치 여부"] = table.index.map(lambda y: "●" if y in 이상치_연도 else "")
    st.dataframe(table.style.format({"연평균기온(℃)": "{:.2f}", "5년 이동평균(℃)": "{:.2f}")))

    if 이상치_연도:
        st.write(f"**이상치 연도 ({len(이상치_연도)}개)**")
        st.dataframe(
            pd.DataFrame({
                "연도": 이상치_연도,
                "연평균기온(℃)": [float(연평균[y]) for y in 이상치_연도],
            }).style.format({"연평균기온(℃)": "{:.2f}"}))
