import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

APP_TITLE = "스마트폰 사용과 수면·스트레스 분석실"
APP_ICON = "📱"

st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="wide")

DATA_FILE = "Smartphone_Usage_And_Addiction_Analysis_7500_Rows.csv"
RECORD_DIR = Path("내_기록")
RECORD_DIR.mkdir(exist_ok=True)
NOTES_FILE = RECORD_DIR / "notes.json"

LABELS = {
    "daily_screen_time_hours": "하루 화면 시간",
    "sleep_hours": "수면시간",
    "social_media_hours": "SNS 시간",
    "gaming_hours": "게임 시간",
}
ORDER = {
    "stress_level": ["Low", "Medium", "High"],
    "addiction_level": ["None", "Mild", "Moderate", "Severe"],
}
GROUP_LABELS = {"stress_level": "스트레스 수준", "addiction_level": "중독 수준"}


def load_notes():
    if NOTES_FILE.exists():
        try:
            return json.loads(NOTES_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"meanings": {}, "source": ""}


def save_notes(notes):
    NOTES_FILE.write_text(json.dumps(notes, ensure_ascii=False, indent=2), encoding="utf-8")


def read_csv(source):
    # "None"이라는 글자가 빈 값으로 바뀌지 않도록 기본 빈 값 처리를 끈다.
    return pd.read_csv(source, encoding="utf-8-sig", keep_default_na=False, na_values=[""])


@st.cache_data
def load_local():
    return read_csv(DATA_FILE)


notes = load_notes()

st.title(f"{APP_ICON} {APP_TITLE}")
st.caption("스마트폰 사용 시간이 수면시간·스트레스와 어떤 관계가 있는지 살펴보는 앱입니다.")

# ── 데이터 불러오기 ────────────────────────────────
df = None
if Path(DATA_FILE).exists():
    df = load_local()
else:
    st.warning(f"'{DATA_FILE}' 파일이 앱 폴더에 없어요. 아래에서 직접 올려 주세요.")
    uploaded = st.file_uploader("CSV 파일 선택", type="csv")
    if uploaded is not None:
        try:
            df = read_csv(uploaded)
        except Exception:
            st.error("파일을 읽지 못했어요. CSV 형식을 확인해 주세요.")

needed = list(LABELS) + list(ORDER)
if df is None:
    st.stop()
missing = [c for c in needed if c not in df.columns]
if missing:
    st.error("필요한 열이 없어요: " + ", ".join(missing))
    st.stop()

# ── 숫자 카드 ──────────────────────────────────────
m1, m2, m3, m4 = st.columns(4)
m1.metric("전체 사람 수", f"{len(df):,}명")
m2.metric("열 개수", f"{df.shape[1]}개")
m3.metric("평균 화면 시간", f"{df['daily_screen_time_hours'].mean():.2f}시간")
m4.metric("가장 오래 쓴 사람", f"{df['daily_screen_time_hours'].max():.1f}시간")

if "age" in df.columns:
    st.caption(
        f"참고: 이 데이터의 나이는 {int(df['age'].min())}~{int(df['age'].max())}세예요. "
        "고등학생 자료가 아니라 성인 자료입니다."
    )

# ── 열 설명 표 ─────────────────────────────────────
st.subheader("열 설명 표")
st.caption("'우리말 뜻' 칸은 직접 적을 수 있어요. 적은 뒤 저장 버튼을 눌러 주세요.")
info = pd.DataFrame(
    {
        "열 이름": df.columns,
        "우리말 뜻": [notes["meanings"].get(c, "") for c in df.columns],
        "값의 종류": [df[c].nunique() for c in df.columns],
        "빈 값 개수": [int(df[c].isna().sum()) for c in df.columns],
    }
)
edited = st.data_editor(
    info,
    hide_index=True,
    use_container_width=True,
    disabled=["열 이름", "값의 종류", "빈 값 개수"],
    column_config={"우리말 뜻": st.column_config.TextColumn("우리말 뜻")},
    key="info_editor",
)
if st.button("우리말 뜻 저장"):
    notes["meanings"] = dict(zip(edited["열 이름"], edited["우리말 뜻"]))
    save_notes(notes)
    st.success("저장했어요.")

# ── 처음 다섯 줄 ───────────────────────────────────
st.subheader("데이터 처음 다섯 줄")
st.dataframe(df.head(5), use_container_width=True, hide_index=True)

# ── 막대그래프 ─────────────────────────────────────
st.subheader("집단별 평균 비교")
c1, c2 = st.columns(2)
group_col = c1.selectbox(
    "어떤 기준으로 나눠 볼까요?",
    list(GROUP_LABELS),
    format_func=lambda x: GROUP_LABELS[x],
)
value_col = c2.selectbox(
    "무엇의 평균을 볼까요?",
    list(LABELS),
    format_func=lambda x: LABELS[x],
)
grouped = df.groupby(group_col)[value_col].mean().round(2).reset_index()
bar = px.bar(
    grouped,
    x=group_col,
    y=value_col,
    text_auto=True,
    category_orders={group_col: ORDER[group_col]},
    labels={
        group_col: GROUP_LABELS[group_col],
        value_col: f"평균 {LABELS[value_col]} (시간)",
    },
)
st.plotly_chart(bar, use_container_width=True)

# ── 산점도 ─────────────────────────────────────────
st.subheader("화면 시간과 수면시간")
corr = df["daily_screen_time_hours"].corr(df["sleep_hours"])
st.markdown(f"화면 시간과 수면시간의 상관계수는 **{corr:.2f}** 입니다.")
st.caption("상관계수는 -1~1 사이 값이에요. 0에 가까우면 관계가 약하고, 관계가 있어 보여도 원인이라고 단정할 수는 없어요.")
sample = df.sample(min(len(df), 1500), random_state=0)
scatter = px.scatter(
    sample,
    x="daily_screen_time_hours",
    y="sleep_hours",
    color="stress_level",
    category_orders={"stress_level": ORDER["stress_level"]},
    opacity=0.6,
    labels={
        "daily_screen_time_hours": "하루 화면 시간 (시간)",
        "sleep_hours": "수면시간 (시간)",
        "stress_level": "스트레스 수준",
    },
)
st.plotly_chart(scatter, use_container_width=True)
st.caption("점이 너무 많아 1,500명만 무작위로 골라 그렸어요.")

# ── 출처 ───────────────────────────────────────────
st.subheader("데이터 출처")
source = st.text_area("출처를 적어 주세요.", value=notes.get("source", ""))
if st.button("출처 저장"):
    notes["source"] = source
    save_notes(notes)
    st.success("저장했어요.")
