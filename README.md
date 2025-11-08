## Các lệnh cần chạy

# TERMINAL 1
cd mini-travel-assistant
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
ollama run llama3

# TERMINAL 2
cd mini-travel-assistant
source .venv/bin/activate
python -m uvicorn llm_server.main:app --reload --port 8000

# TERMINAL 3
cd mini-travel-assistant
source .venv/bin/activate
streamlit run app.py