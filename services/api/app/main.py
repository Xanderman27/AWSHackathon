from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import (attempts, conferences, games, group_activities, login, messages,
                      parent, resources, student, teacher)
from .storage import store

app = FastAPI(title="Adaptive Learning Platform API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(attempts.router)
app.include_router(teacher.router)
app.include_router(parent.router)
app.include_router(conferences.router)
app.include_router(resources.router)
app.include_router(messages.router)
app.include_router(games.router)
app.include_router(group_activities.router)
app.include_router(student.router)
app.include_router(login.router)


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/skills")
def skills():
    return store.read("skills")


@app.post("/demo/reset")
def reset():
    store.reset()
    return {"ok": True}
