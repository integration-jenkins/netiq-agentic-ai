"""Main page route. No sign-in form: it shows the user info that 6061 returned for the logged-in browser session."""

from fastapi.responses import FileResponse, HTMLResponse

from src.settings.env import settings

UI_DIR = settings.project_root / "ui" / "web"
_USER_INFO_UI = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>NETIQ - logged-in user info</title>
  <style>body{font-family:sans-serif;margin:24px} pre{background:#f4f4f4;padding:12px;overflow:auto} .bad{color:#b00020}</style>
</head>
<body>
  <h1>NETIQ - logged-in user info (from 6061)</h1>
  <p>Log in on the NETIQ page first: <a id="login-link" href="#" target="_blank">6061 login</a>, then <button id="reload">Reload user info</button></p>
  <p id="status">Loading...</p>
  <h3>user_info (login JSON taken from 6061)</h3>
  <pre id="user">-</pre>
  <h3>server-side user_info variable (all sessions, testing only)</h3>
  <pre id="store">-</pre>
  <h3>diagnostics (cookies received + endpoints tried)</h3>
  <pre id="diag">-</pre>
  <script>
    const $ = (id) => document.getElementById(id);
    $("login-link").href = location.protocol + "//" + location.hostname + ":6061/login";
    async function load() {
      $("status").textContent = "Loading...";
      try {
        const r = await fetch("/auth/session-info", { credentials: "include" });
        const body = await r.json();
        window.USER_INFO = body.user;               // also available in the browser console
        $("user").textContent = body.user ? JSON.stringify(body.user, null, 2) : "(no user info yet)";
        $("status").textContent = body.user ? "OK - " + body.source : body.message;
        $("status").className = body.user ? "" : "bad";
        $("diag").textContent = JSON.stringify({ cookies_received: body.cookies_received, tried: body.tried,
                                                 test_login_error: body.test_login_error }, null, 2);
      } catch (e) { $("status").textContent = String(e); $("status").className = "bad"; }
      try {
        const s = await fetch("/auth/debug/user_info");
        $("store").textContent = JSON.stringify(await s.json(), null, 2);
      } catch (e) { $("store").textContent = String(e); }
    }
    $("reload").addEventListener("click", load);
    load();
  </script>
</body>
</html>"""


async def main_page():
    index = UI_DIR / "index.html"
    if index.is_file():
        return FileResponse(index)
    return HTMLResponse(_USER_INFO_UI)
