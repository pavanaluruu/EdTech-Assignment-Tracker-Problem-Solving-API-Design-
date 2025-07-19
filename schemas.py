from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    role: str  # "student" or "teacher"

class UserLogin(BaseModel):
    email: str
    password: str

class AssignmentCreate(BaseModel):
    title: str
    description: str
    due_date: datetime

class SubmissionOut(BaseModel):
    student_name: str
    submitted_at: datetime
    file_path: str

    class Config:
        orm_mode = True
