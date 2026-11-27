"""No login form: the chat opens for the user who is already logged in to NETIQ in this browser.

Browsers send cookies by host name, not port, so NETIQ's login cookie (JSESSIONID) also reaches
this page when NETIQ and this page are opened with the same host name (localhost and 127.0.0.1
count as different). The backend asks NETIQ who owns that cookie. Streamlit reads the cookies
when the page is opened, so after logging in to NETIQ the user reloads this page.
"""

import streamlit as st

from ui.streamlit.api_client import NetiqApiClient, NetiqApiError
from ui.streamlit.config import get_ui_config
from ui.streamlit.session_manager import start_login


def browser_cookie_header() -> str:
    """This browser's cookies for this host name, NETIQ's login cookie among them."""
    return "; ".join(f"{name}={value}" for name, value in st.context.cookies.items())


def _netiq_url() -> str:
    host = (st.context.headers.get("host") or "localhost").rsplit(":", 1)[0]
    return get_ui_config().netiq_web_url or f"http://{host}:6061"


def render_login_panel(api_client: NetiqApiClient) -> None:
    problem = None
    cookies = browser_cookie_header()
    if cookies:
        try:
            data = api_client.start_session_from_netiq(cookies)
        except NetiqApiError as err:
            problem = None if err.status_code == 401 else str(err)
        else:
            start_login(data["session_id"], data.get("user") or {})
            st.rerun()

    st.title("NETIQ Agentic AI")
    if st.session_state.get("login_note"):
        st.info(st.session_state["login_note"])
    if problem:
        st.error(f"Could not check your NETIQ login: {problem}")
    url = _netiq_url()
    st.warning(f"Log in to NETIQ first at [{url}]({url}), then reload this page. "
               "Open NETIQ and this page with the same host name (localhost and 127.0.0.1 count as different).")
