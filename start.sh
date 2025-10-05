#!/bin/bash
# фоновый Telegram-бот
python -m bot.bot &
# веб-интерфейс (Flask-обёртка над Streamlit)
gunicorn streamlit_wsgi:app -b 0.0.0.0:8000 --workers 1 --timeout 120
