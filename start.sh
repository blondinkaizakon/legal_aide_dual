#!/bin/bash
# фоновый бот
python -m bot.bot &
# wsgi-веб (flask-обёртка над streamlit)
gunicorn streamlit_wsgi:app -b 0.0.0.0:8000 --workers 1 --timeout 120
