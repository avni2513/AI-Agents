from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.travel_agent import TripRequest, generate_offline, format_full

app = FastAPI(title="AI Travel Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class TripRequestAPI(BaseModel):
    destination: str
    days: int
    budget: str
    interests: str = ""


@app.get("/")
def root():
    return {"message": "AI Travel Agent API is running"}


@app.post("/plan")
def plan_trip(request: TripRequestAPI):
    interests = [
        item.strip()
        for item in request.interests.split(",")
        if item.strip()
    ]

    trip = TripRequest(
        destination=request.destination,
        days=request.days,
        budget_level=request.budget,
        interests=interests,
        travelers=1,
    )

    state = generate_offline(trip)

    return {
        "result": format_full(state),
        "data": state,
    }
