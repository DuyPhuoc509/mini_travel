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
You are a helpful travel planner.

Origin city: {req.origin}
Destination city: {req.destination}
Start date: {req.start_date}
End date: {req.end_date}
Interests: {interests_text}
Pace: {req.pace} (relaxed/normal/tight)

Task:
- Create a detailed day-by-day itinerary from start date to end date.
- For EACH day, include 3 sections: Morning, Afternoon, Evening.
- Each activity should have 1-2 sentences description.
- Focus on the interests when choosing activities.
- Output format exactly like this (no extra text before or after):

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