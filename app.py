import re
import streamlit as st
from datetime import date
import time

from firebase_config import auth, db
from llm_client import generate_itinerary


# ---------- Format itinerary: in đậm & giới hạn số ngày ----------
def format_itinerary_md(text: str, day_count: int | None = None) -> str:
    """
    Đổi itinerary text sang Markdown:
    - Day X thành heading, tự đánh lại Day 1, Day 2, ...
    - Morning/Afternoon/Evening thành gạch đầu dòng, in đậm.
    - Giới hạn tối đa day_count ngày (1 ngày chỉ Day 1, 2 ngày chỉ Day 1 & Day 2).
    """

    # Nếu biết chính xác số ngày thì cắt bớt text trước khi format
    if day_count is not None and day_count >= 1:
        pattern = re.compile(r"Day\s+\d+", re.IGNORECASE)
        matches = list(pattern.finditer(text))

        if matches:
            # Vị trí bắt đầu của Day đầu tiên
            first_start = matches[0].start()

            if len(matches) > day_count:
                # Có nhiều hơn day_count block "Day"
                # -> giữ từ Day đầu tiên tới trước Day thứ (day_count + 1)
                end = matches[day_count].start()
                text = text[first_start:end]
            else:
                # Ít block hơn hoặc bằng day_count -> giữ từ Day đầu tiên tới hết
                text = text[first_start:]

    # Chuẩn hóa xuống dòng để dễ xử lý
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")

    # Ép xuống dòng trước các từ khóa, phòng trường hợp Ollama trả liền 1 dòng
    for token in ["Day ", "Morning:", "Afternoon:", "Evening:"]:
        normalized = normalized.replace(token, "\n" + token)

    raw_lines = [l.strip() for l in normalized.splitlines()]

    # Bỏ dòng trống đầu
    while raw_lines and not raw_lines[0]:
        raw_lines.pop(0)

    lines: list[str] = []
    started = False  # chỉ bắt đầu giữ nội dung từ khi gặp "Day ..."
    day_index = 0    # tự đánh lại số ngày

    for line in raw_lines:
        if not line:
            continue

        lower = line.lower()

        if lower.startswith("day "):
            started = True
            day_index += 1

            # chèn dòng trống giữa các Day
            if lines:
                lines.append("")

            # Lấy phần sau chữ "Day <số>" để giữ lại date nếu có
            m = re.match(r"day\s+\d+(.*)", line, re.IGNORECASE)
            suffix = ""
            if m:
                suffix = m.group(1).strip()

            # Bỏ dấu "-" thừa ở đầu
            if suffix.startswith("-"):
                suffix = suffix[1:].strip()

            title = f"Day {day_index}"
            if suffix:
                title = f"{title} - {suffix}"

            lines.append(f"### {title}")

        elif lower.startswith("morning:"):
            started = True
            content = line[len("Morning:"):].lstrip()
            lines.append(f"- **Morning:** {content}")

        elif lower.startswith("afternoon:"):
            started = True
            content = line[len("Afternoon:"):].lstrip()
            lines.append(f"- **Afternoon:** {content}")

        elif lower.startswith("evening:"):
            started = True
            content = line[len("Evening:"):].lstrip()
            lines.append(f"- **Evening:** {content}")

        else:
            # Bỏ phần mở đầu trước Day 1 (kiểu "Here is your detailed itinerary...")
            if not started:
                continue
            # Các dòng khác (ghi chú cuối, tips) vẫn giữ lại
            lines.append(line)

    return "\n".join(lines)


# ---------- Firebase helper ----------
def signup(email, password):
    return auth.create_user_with_email_and_password(email, password)


def login(email, password):
    return auth.sign_in_with_email_and_password(email, password)


def save_chat(uid, user_input, itinerary_text):
    timestamp = int(time.time())
    chat_id = str(timestamp)
    data = {
        "timestamp": timestamp,
        "origin": user_input["origin"],
        "destination": user_input["destination"],
        "start_date": str(user_input["start_date"]),
        "end_date": str(user_input["end_date"]),
        "interests": user_input["interests"],
        "pace": user_input["pace"],
        "itinerary": itinerary_text,
    }
    db.child("users").child(uid).child("chats").child(chat_id).set(data)


def load_chats(uid):
    res = db.child("users").child(uid).child("chats").get()
    if not res.each():
        return []
    chats = [item.val() for item in res.each()]
    chats.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
    return chats


# ---------- Streamlit UI ----------
st.set_page_config(page_title="Mini Travel Planner", page_icon="✈️", layout="wide")
st.title("✈️ Mini Travel Planner (Streamlit + Firebase + Ollama)")


if "user" not in st.session_state:
    st.session_state.user = None
if "uid" not in st.session_state:
    st.session_state.uid = None

# --------- Auth screen ---------
if st.session_state.user is None:
    tab_login, tab_signup = st.tabs(["Login", "Sign up"])

    with tab_login:
        st.subheader("Login")
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login"):
            try:
                user = login(email, password)
                st.session_state.user = user
                st.session_state.uid = user["localId"]
                st.success("Login successful!")
                st.rerun()
            except Exception as e:
                st.error(f"Login failed: {e}")

    with tab_signup:
        st.subheader("Create new account")
        email_su = st.text_input("Email", key="su_email")
        pass_su = st.text_input("Password", type="password", key="su_password")
        if st.button("Sign up"):
            try:
                signup(email_su, pass_su)
                st.success("Sign up successful! Now you can login.")
            except Exception as e:
                st.error(f"Sign up failed: {e}")

else:
    st.sidebar.write(f"Logged in as: **{st.session_state.user['email']}**")
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.session_state.uid = None
        st.rerun()

    col_form, col_history = st.columns([2, 1])

    # ---- Form nhập thông tin chuyến đi ----
    with col_form:
        st.subheader("Plan your trip")

        origin = st.text_input("Origin city", value="Ho Chi Minh City")
        destination = st.text_input("Destination city", value="Da Nang")

        col_d1, col_d2 = st.columns(2)
        with col_d1:
            start_date = st.date_input("Start date", value=date.today())
        with col_d2:
            end_date = st.date_input("End date", value=date.today())

        interests = st.multiselect(
            "Interests",
            ["Food", "Museums", "Nature", "Nightlife"],
            default=["Food", "Nature"],
        )

        pace = st.selectbox("Pace", ["relaxed", "normal", "tight"], index=1)

        # Chỗ để hiển thị trạng thái
        status_placeholder = st.empty()

        if st.button("Generate itinerary"):
            if start_date > end_date:
                status_placeholder.error("End date must be after or equal to start date.")
            else:
                # Thông báo cho user biết thời gian chờ
                status_placeholder.info(
                    "⏳ This process can take around 1–2 minutes, please wait..."
                )

                from datetime import datetime

                with st.spinner(
                    "Generating itinerary using Ollama... (this may take 1–2 minutes)"
                ):
                    itinerary = generate_itinerary(
                        origin,
                        destination,
                        start_date,
                        end_date,
                        interests,
                        pace,
                    )

                status_placeholder.success("✅ Itinerary generated!")

                # Tính số ngày để format đúng (1 ngày chỉ Day 1, v.v.)
                day_count = (end_date - start_date).days + 1

                st.subheader("Your itinerary")
                st.markdown(format_itinerary_md(itinerary, day_count=day_count))

                user_input = {
                    "origin": origin,
                    "destination": destination,
                    "start_date": start_date,
                    "end_date": end_date,
                    "interests": interests,
                    "pace": pace,
                }
                save_chat(st.session_state.uid, user_input, itinerary)

    # ---- History ----
    with col_history:
        st.subheader("History")
        chats = load_chats(st.session_state.uid)
        if not chats:
            st.info("No history yet.")
        else:
            from datetime import datetime

            for c in chats:
                st.markdown(
                    f"**{c['origin']} → {c['destination']}** "
                    f"({c['start_date']} → {c['end_date']})  "
                    f"<br/>Pace: `{c['pace']}`<br/>Interests: {', '.join(c['interests'])}",
                    unsafe_allow_html=True,
                )

                # Tính lại số ngày từ dữ liệu đã lưu
                try:
                    start_d = date.fromisoformat(c["start_date"])
                    end_d = date.fromisoformat(c["end_date"])
                    day_count_hist = (end_d - start_d).days + 1
                except Exception:
                    day_count_hist = None  # nếu parse lỗi thì không giới hạn

                with st.expander("Show itinerary"):
                    st.markdown(
                        format_itinerary_md(c["itinerary"], day_count=day_count_hist)
                    )