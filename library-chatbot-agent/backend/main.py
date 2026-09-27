from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from chatbot import LibraryChatbot

app = FastAPI(title="College Library Chatbot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

chatbot = LibraryChatbot()


class ChatRequest(BaseModel):
    message: str


@app.get("/")
def home():
    return {"message": "College Library Chatbot API is running"}


@app.post("/chat")
def chat(request: ChatRequest):
    response = chatbot.reply(request.message)
    return {"response": response}