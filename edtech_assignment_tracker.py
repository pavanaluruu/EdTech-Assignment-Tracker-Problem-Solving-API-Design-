from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt
from typing import List, Optional

# ---------- CONFIGURATION ----------
DATABASE_URL = "sqlite:///./assignments.db"
SECRET_KEY = "secretkeyexample"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# ---------- DATABASE SETUP ----------
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ---------- MODELS ----------
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    role = Column(String)

class Assignment(Base):
    __tablename__ = "assignments"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    description = Column(Text)
    due_date = Column(DateTime)
    teacher_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

class Submission(Base):
    __tablename__ = "submissions"
    id = Column(Integer, primary_key=True, index=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id"))
    student_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text)
    submitted_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# ---------- AUTH ----------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(lambda: SessionLocal())):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    return user

# ---------- FASTAPI ----------
app = FastAPI()

# ---------- ROUTES ----------
@app.post("/signup")
def signup(name: str, email: str, password: str, role: str, db: Session = Depends(SessionLocal)):
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = get_password_hash(password)
    new_user = User(name=name, email=email, password=hashed_password, role=role)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User created successfully"}

@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(SessionLocal)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/assignments")
def create_assignment(title: str, description: str, due_date: str, user: User = Depends(get_current_user), db: Session = Depends(SessionLocal)):
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can create assignments")
    due = datetime.strptime(due_date, "%Y-%m-%d")
    assignment = Assignment(title=title, description=description, due_date=due, teacher_id=user.id)
    db.add(assignment)
    db.commit()
    return {"message": "Assignment created successfully"}

@app.post("/assignments/{assignment_id}/submit")
def submit_assignment(assignment_id: int, content: str, user: User = Depends(get_current_user), db: Session = Depends(SessionLocal)):
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can submit assignments")
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    submission = Submission(assignment_id=assignment_id, student_id=user.id, content=content)
    db.add(submission)
    db.commit()
    return {"message": "Assignment submitted successfully"}

@app.get("/assignments/{assignment_id}/submissions")
def view_submissions(assignment_id: int, user: User = Depends(get_current_user), db: Session = Depends(SessionLocal)):
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if user.role != "teacher" or user.id != assignment.teacher_id:
        raise HTTPException(status_code=403, detail="Only the teacher who created the assignment can view submissions")
    submissions = db.query(Submission).filter(Submission.assignment_id == assignment_id).all()
    return [{"student_id": s.student_id, "content": s.content, "submitted_at": s.submitted_at} for s in submissions]
