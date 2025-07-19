from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base, User
from fastapi.middleware.cors import CORSMiddleware
import bcrypt

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Assignment Submission System 🎓",
    docs_url=None,         # disable /docs
    redoc_url="/redoc",    # keep ReDoc at /redoc
)

# Enable CORS (so frontend can talk to backend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or restrict to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Models
class SignupRequest(BaseModel):
    username: str
    password: str
    role: str

# Routes
@app.get("/", response_class=HTMLResponse)
async def landing_page():
    return """
    <html>
        <head>
            <title>Assignment Submission Portal</title>
            <style>
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    text-align: center;
                    padding-top: 10%;
                    background-color: #f8f9fa;
                    color: #333;
                }
                a {
                    text-decoration: none;
                    color: #007bff;
                    font-weight: bold;
                }
            </style>
        </head>
        <body>
            <h1>🎓 Assignment Submission System</h1>
            <p>Welcome! This is a backend prototype built with FastAPI.</p>
            <p>To test the API, visit the <a href="/redoc">ReDoc API Interface</a>.</p>
        </body>
    </html>
    """

@app.post("/signup", tags=["User"])
def signup(user: SignupRequest, db: Session = Depends(get_db)):
    # Check if user already exists
    existing_user = db.query(User).filter(User.username == user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt())

    new_user = User(
        username=user.username,
        password=hashed_password.decode('utf-8'),
        role=user.role,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User signed up successfully", "user": user.username}
