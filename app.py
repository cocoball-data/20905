# app.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="서울 기온 변화 분석", page_icon="🌡️", layout="wide")

# ============================================================
# 1) 데이터 로드
# ============================================================
@st.cache_data
def load_data(path: str = "seoul_temperature.csv") -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    df["날짜"] = pd.to_datetime(
        df["날짜"].astype(str).str.replace('"', "", regex=False).str.strip(),
        format="%Y-%m-%d",
    )
    df["연도"] = df["날짜"].dt.year
    df["월"] = df["날짜"].dt.month
    return df


df = load_data()

기온_컬럼 = ["평균기온(℃)", "최저기온(℃)", "최고기온(℃)"]

# ============================================================
# 2) 데이터 전처리
# ============================================================
기온_있음 = df[기온_컬럼].notna().any(axis=1)
연도_기온일수 = 기온_있음.groupby(df["연도"]).sum()
유효_연도 = 연도_기온일수[연도_기온일수 >= 360].index
df = df[df["연도"].isin(유효_연도)]

연평균 = df.groupby("연도")["평균기온(℃)"].mean().sort_index()
이동평균 = 연평균.rolling(window=5, min_periods=5, center=True).mean().sort_index()

# 일교차 컬럼
df["일교차"] = df["최고기온(℃)"] - df["최저기온(℃)"]

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

# ============================================================
# 4) 화면 구성
# ============================================================
st.title("서울의 기온 변화 분석")

st.markdown(
    """
- **연도 선별**: 기온 값이 있는 날이 360일 미만인 해는 연평균 계산에서 제외
- **5년 이동평균**: 5개 연도 모두 값이 있을 때만 계산 (중심 5년 기준)
- 값이 없는 연도는 꺾은선 그래프에서 선이 끊겨 표시됨
"""
)

if len(연평균) == 0:
    st.error("연평균 계산에 사용할 수 있는 연도가 없습니다. 데이터 파일을 확인해 주세요.")
    st.stop()

c1, c2, c3 = st.columns(3)
c1.metric("선택 구간 평균기온", f"{선택_평균:.2f} ℃")
c2.metric("선택 구간 최고기온", f"{선택_최고:.2f} ℃")
c3.metric("선택 구간 최저기온", f"{선택_최저:.2f} ℃")
st.caption(
    f"선택 구간: {선택_연도[0]}~{선택_연도[1]}년 | 데이터 {len(df_선택)}일 | "
    f"그래프는 선택한 연도 범위로 표시"
)

# --- 1. 월별 히트맵 ---
st.subheader("월별 평균기온 히트맵")
월별 = df.pivot_table(index="연도", columns="월", values="평균기온(℃)", aggfunc="mean")

fig_heatmap = go.Figure(
    go.Heatmap(
        z=m월별.values,
        x=m월별.columns.astype(int),
        y=m월별.index,
        coloraxis="coloraxis",
        hovertemplate="연도=%{y}<br>월=%{x}<br>평균기온=%{z:.2f} ℃<extra></extra>",
    )
)
fig_heatmap.update_layout(
    title="월별 평균기온",
    xaxis_title="월",
    yaxis_title="연도",
    coloraxis_colorbar_title="평균기온(℃)",
    margin=dict(l=40, r=20, t=50, b=30),
)
st.plotly_chart(fig_heatmap, use_container_width=True)

# --- 2. 최고기온 상위 10일 / 최저기온 하위 10일 ---
st.subheader("기온 극단일")

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

c4, c5 = st.columns(2)
with c4:
    st.write("**최고기온 상위 10일**")
    st.dataframe(top10.style.format({"평균기온(℃)": "{:.2f}", "최저기온(℃)": "{:.2f}", "최고기온(℃)": "{:.2f}"}))
with c5:
    st.write("**최저기온 하위 10일**")
    st.dataframe(bottom10.style.format({"평균기온(℃)": "{:.2f}", "최저기온(℃)": "{:.2f}", "최고기온(℃)": "{:.2f}"}))

# --- 3. 연도별 평균 일교차 그래프 ---
st.subheader("연도별 평균 일교차")
일교차_연도 = df.groupby("연도")["일교차"].mean().sort_index()

fig_range = go.Figure()
fig_range.add_trace(
    go.Scatter(
        x=일교차_연도.index,
        y=일교차_연도.values,
        mode="lines+markers",
        name="평균 일교차",
        line=dict(color="#2ca02c", width=2.5),
    )
)
fig_range.update_layout(
    title="연도별 평균 일교차",
    xaxis_title="연도",
    yaxis_title="일교차(℃)",
    hovermode="x unified",
    margin=dict(l=40, r=20, t=40, b=30),
)
st.plotly_chart(fig_range, use_container_width=True)

# --- 4. 연도별 상세 ---
with st.expander("연도별 상세 데이터 보기"):
    table = pd.DataFrame(
        {
            "연평균기온(℃)": 연평균,
            "5년 이동평균(℃)": 이동평균,
        }
    )
    st.dataframe(table.style.format("{:.2f}"))
