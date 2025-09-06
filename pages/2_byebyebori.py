import streamlit as st

col1, col2 = st.columns(2)

with col1:
    st.title("How Cute")
    st.subheader("보리가 귀여웠다면\n")
    st.subheader("그만큼 눌러주세요\n")

    if "customer_count" not in st.session_state:
        st.session_state.customer_count = 0

    if st.button('하나도 안 귀여옹😾'):
        st.session_state.customer_count -= 1

    if st.button('쫌 귀여옹😺'):
        st.session_state.customer_count += 1

    if st.button('짱 귀여옹😻😻😻'):
        st.session_state.customer_count += 100


    st.title(f"How Cute Bori😽: {st.session_state.customer_count}")
    st.header("보리의 소식이 앞으로도 궁금하다면: @boribehealthy")

with col2:
    st.title(" ")
    st.title(" ") 
    video_file = open("C:/Bori/KakaoTalk_20250702_172054364.mp4", 'rb')
    st.video(video_file)

    st.markdown("[👉 인스타그램에서 보리 보기](https://www.instagram.com/boribehealthy?igsh=MXNvcnh6eDhsY2RvZA%3D%3D&utm_source=qr)",unsafe_allow_html=True)