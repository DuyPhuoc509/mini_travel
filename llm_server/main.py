from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

import requests

app = FastAPI()

# URL API của Ollama
OLLAMA_API_URL = "http://localhost:11434/api/generate"


class TripRequest(BaseModel):
    origin: str
    destination: str
    start_date: str   # "YYYY-MM-DD"
    end_date: str     # "YYYY-MM-DD"
    interests: List[str]
    pace: str         # relaxed / normal / tight
    model: str = "llama3"   # mặc định dùng llama3


def build_prompt(req: TripRequest) -> str:
    interests_text = ", ".join(req.interests) if req.interests else "none"

    return f"""
You are a travel planner.

Trip:
- From: {req.origin}
- To: {req.destination}
- Dates: {req.start_date} → {req.end_date}
- Interests: {interests_text}
- Pace: {req.pace} (relaxed/normal/tight)

Create a short day-by-day itinerary.

Rules:
- For EACH day: 3 lines only: Morning, Afternoon, Evening.
- Each line: max 20 words, very concise.
- Focus on interests when choosing activities.
- No extra explanations before or after, just this format:

Day 1 - YYYY-MM-DD
Morning: ...
Afternoon: ...
Evening: ...

Day 2 - YYYY-MM-DD
Morning: ...
Afternoon: ...
Evening: ...
"""

def call_ollama(prompt: str, model_name: str) -> str:
    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": 350  # giới hạn tối đa 350 tokens để trả nhanh hơn
        },
    }
    resp = requests.post(OLLAMA_API_URL, json=payload, timeout=180)
    resp.raise_for_status()
    data = resp.json()
    return data.get("response", "").strip()


@app.post("/generate_itinerary")
def generate_itinerary(req: TripRequest):
    prompt = build_prompt(req)
    itinerary_text = call_ollama(prompt, req.model)
    return {"itinerary": itinerary_text}

from datetime import date

def build_prompt(req: TripRequest) -> str:
    interests_text = ", ".join(req.interests) if req.interests else "none"

    start = date.fromisoformat(req.start_date)
    end = date.fromisoformat(req.end_date)
    day_count = (end - start).days + 1

    if day_count == 1:
        day_rule = """
- This is a SINGLE-DAY trip.
- Only output **Day 1**. Do NOT create Day 2 or later.
"""
    else:
        day_rule = f"""
- This trip has {day_count} days.
- Output exactly {day_count} days: Day 1, Day 2, ..., Day {day_count}.
"""

    return f"""
You are a helpful travel planner.

Trip information:
- Origin city: {req.origin}
- Destination city: {req.destination}
- Start date: {req.start_date}
- End date: {req.end_date}
- Interests: {interests_text}
- Pace: {req.pace} (relaxed/normal/tight)

Task:
- Create a short, clear day-by-day itinerary from start date to end date.
- Each day must have Morning, Afternoon, Evening activities.

{day_rule}

Output format (no extra explanation before or after):

Day 1 - YYYY-MM-DD
Morning: ...
Afternoon: ...
Evening: ...

Day 2 - YYYY-MM-DD
Morning: ...
Afternoon: ...
Evening: ...
"""
