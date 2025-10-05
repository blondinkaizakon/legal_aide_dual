#!/bin/bash
python -m bot.bot &
gunicorn streamlit_wsgi:app -b 0.0.0.0:8000 --workers 1 --timeout 120
