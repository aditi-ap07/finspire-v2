import streamlit as st
from ui.pages import run_app


def main():
    st.set_page_config(
        page_title="FINSPIRE",
        page_icon="📰",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    run_app()


if __name__ == "__main__":
    main()
