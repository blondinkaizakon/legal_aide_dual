import os, sys
from flask import Flask, request, Response
from streamlit.web.bootstrap import run
from threading import Thread

app   = Flask(__name__)
PORT  = int(os.getenv("PORT", 8000))

def _run_st():
    os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
    os.environ["STREAMLIT_SERVER_PORT"] = str(PORT)
    os.environ["STREAMLIT_SERVER_ADDRESS"] = "0.0.0.0"
    run("web/web.py", "", [], {})

Thread(target=_run_st, daemon=True).start()

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def root(path):
    return Response("Streamlit loading...", 200)
