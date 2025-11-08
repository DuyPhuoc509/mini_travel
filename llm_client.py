import requests
from datetime import timedelta

# Backend FastAPI local
BACKEND_URL = "http://localhost:8000"


def _dummy_itinerary(origin, destination, start_date, end_date, interests, pace):
    """Fallback nếu backend lỗi – để app vẫn chạy được."""
    interests_text = ", ".join(interests) if interests else "no specific interests"

    days = []
    current = start_date
    idx = 1
    while current <= end_date:
        days.append(
            f"Day {idx} - {current.strftime('%Y-%m-%d')}\n"
            f"- Morning: Explore local cafes in {destination}.\n"
            f"- Afternoon: Activity related to {interests_text}.\n"
            f"- Evening: {pace.capitalize()} walk in the city center.\n"
        )
        current += timedelta(days=1)
        idx += 1

    header = (
        f"Trip from {origin} to {destination} ({start_date} → {end_date})\n"
        f"Interests: {interests_text}\n"
        f"Pace: {pace}\n\n"
    )
    return header + "\n".join(days)


def generate_itinerary(
    origin,
    destination,
    start_date,
    end_date,
    interests,
    pace,
    model="llama3",   # mặc định llama3
):
    try:
        payload = {
            "origin": origin,
            "destination": destination,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "interests": interests,
            "pace": pace,
            "model": model,
        }
        resp = requests.post(
            f"{BACKEND_URL}/generate_itinerary",
            json=payload,
            timeout=180,
        )
        resp.raise_for_status()
        data = resp.json()
        if "itinerary" in data:
            return data["itinerary"]
    except Exception as e:
        print("Error calling local LLM server:", e)

    # fallback nếu có lỗi
    return _dummy_itinerary(origin, destination, start_date, end_date, interests, pace)