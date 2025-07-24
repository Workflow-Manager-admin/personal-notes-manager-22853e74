import os
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext

# In a real solution, these would come from env vars/.env
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "TEMP_CHANGE_ME")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Notes on database integration:
# The backend is expected to be connected to an external database handled by the 'notes_database' container.
# Database access code is included as classes and placeholders to be replaced with real queries/ORM as per integration.

app = FastAPI(
    title="Personal Notes API",
    description="API for personal notes management, including user authentication & CRUD.",
    version="1.0.0",
    openapi_tags=[
        {"name": "auth", "description": "Authentication"},
        {"name": "notes", "description": "Note CRUD operations"},
        {"name": "users", "description": "User profile actions"},
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# =======================
# Models & Schemas
# =======================

class UserBase(BaseModel):
    email: EmailStr = Field(..., description="User's email address")

class UserCreate(UserBase):
    password: str = Field(..., min_length=6, description="User password (min 6 chars)")

class UserInDB(UserBase):
    id: int
    hashed_password: str

class UserPublic(UserBase):
    id: int

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class NoteBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=128)
    content: str = Field(..., max_length=2048)

class NoteCreate(NoteBase):
    pass

class NoteUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=128)
    content: Optional[str] = Field(None, max_length=2048)

class NoteInDB(NoteBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

class NotePublic(NoteBase):
    id: int
    created_at: datetime
    updated_at: datetime

# =======================
# Utilities/Auth Helpers
# =======================

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Creates a JWT access token.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# =======================
# Database Placeholders
# =======================

# These classes imitate the database, for production replace with DB queries (SQLAlchemy, Tortoise etc).
class FakeDB:
    """ Fake in-memory database for demonstration (to be replaced by real DB integration). """
    users = []
    notes = []
    user_id_counter = 1
    note_id_counter = 1

    @classmethod
    def get_user_by_email(cls, email):
        for user in cls.users:
            if user['email'] == email:
                return user
        return None

    @classmethod
    def create_user(cls, email, hashed_password):
        user = {
            'id': cls.user_id_counter,
            'email': email,
            'hashed_password': hashed_password
        }
        cls.users.append(user)
        cls.user_id_counter += 1
        return user

    @classmethod
    def get_user(cls, user_id):
        for user in cls.users:
            if user['id'] == user_id:
                return user
        return None

    @classmethod
    def create_note(cls, user_id, title, content):
        now = datetime.utcnow()
        note = {
            'id': cls.note_id_counter,
            'user_id': user_id,
            'title': title,
            'content': content,
            'created_at': now,
            'updated_at': now,
        }
        cls.notes.append(note)
        cls.note_id_counter += 1
        return note

    @classmethod
    def get_notes_by_user(cls, user_id):
        return [n for n in cls.notes if n['user_id'] == user_id]

    @classmethod
    def get_note(cls, user_id, note_id):
        for note in cls.notes:
            if note['user_id'] == user_id and note['id'] == note_id:
                return note
        return None

    @classmethod
    def update_note(cls, user_id, note_id, title=None, content=None):
        note = cls.get_note(user_id, note_id)
        if note:
            if title is not None:
                note['title'] = title
            if content is not None:
                note['content'] = content
            note['updated_at'] = datetime.utcnow()
            return note
        return None

    @classmethod
    def delete_note(cls, user_id, note_id):
        for i, note in enumerate(cls.notes):
            if note['user_id'] == user_id and note['id'] == note_id:
                del cls.notes[i]
                return True
        return False

# =======================
# Dependency/Integration Notes
# =======================
# To integrate with `notes_database`, replace all FakeDB.* usages with actual queries.
# Please refer to database connection env vars and proper ORM or async DB libraries.

# =======================
# Dependency: get_current_user
# =======================
# PUBLIC_INTERFACE
async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserInDB:
    """
    Dependency to get the current user from token.
    Raises 401 if invalid/unauthorized.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    
    user = FakeDB.get_user_by_email(token_data.email)
    if user is None:
        raise credentials_exception
    return UserInDB(**user)

# =======================
# Exception Handling
# =======================
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Override HTTPException for consistent frontend-friendly API error responses
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

# =======================
# API Routes
# =======================

# --- AUTH ENDPOINTS ---

# PUBLIC_INTERFACE
@app.post("/auth/register", response_model=UserPublic, tags=["auth"], summary="Register new user", responses={
    400: {"description": "User already exists"},
    201: {"description": "User created"}
})
def register_user(user: UserCreate):
    """Register a new user with an email and password."""
    if FakeDB.get_user_by_email(user.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = get_password_hash(user.password)
    user_record = FakeDB.create_user(user.email, hashed_password)
    return UserPublic(id=user_record['id'], email=user_record['email'])

# PUBLIC_INTERFACE
@app.post("/auth/login", response_model=Token, tags=["auth"], summary="User login", responses={
    400: {"description": "Invalid credentials"}
})
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Authenticate user and return a JWT access token (Bearer)."""
    user = FakeDB.get_user_by_email(form_data.username)
    if not user or not verify_password(form_data.password, user['hashed_password']):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = create_access_token(
        data={"sub": user['email']}
    )
    return {"access_token": access_token, "token_type": "bearer"}

# --- USER PROFILE ---

# PUBLIC_INTERFACE
@app.get("/users/me", response_model=UserPublic, tags=["users"], summary="Current user profile")
def get_my_details(current_user: UserInDB = Depends(get_current_user)):
    """Get the profile information of the current authenticated user."""
    return UserPublic(id=current_user.id, email=current_user.email)

# --- NOTES ENDPOINTS ---

# PUBLIC_INTERFACE
@app.get("/notes", response_model=List[NotePublic], tags=["notes"], summary="List all notes for current user")
def list_notes(current_user: UserInDB = Depends(get_current_user)):
    """Get all notes belonging to the current user."""
    notes = FakeDB.get_notes_by_user(current_user.id)
    return [NotePublic(**n) for n in sorted(notes, key=lambda x: -x['updated_at'].timestamp())]

# PUBLIC_INTERFACE
@app.post("/notes", response_model=NotePublic, tags=["notes"], summary="Create a note", status_code=201)
def create_note(note: NoteCreate, current_user: UserInDB = Depends(get_current_user)):
    """Create a new note for the authenticated user."""
    note_record = FakeDB.create_note(current_user.id, note.title, note.content)
    return NotePublic(**note_record)

# PUBLIC_INTERFACE
@app.get("/notes/{note_id}", response_model=NotePublic, tags=["notes"], summary="Get a single note")
def get_note(note_id: int, current_user: UserInDB = Depends(get_current_user)):
    """Get a specific note by ID (only if owned by current user)."""
    note = FakeDB.get_note(current_user.id, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return NotePublic(**note)

# PUBLIC_INTERFACE
@app.put("/notes/{note_id}", response_model=NotePublic, tags=["notes"], summary="Update a note")
def update_note(note_id: int, note_update: NoteUpdate, current_user: UserInDB = Depends(get_current_user)):
    """Update the title and/or content of a note they own."""
    note = FakeDB.update_note(current_user.id, note_id, note_update.title, note_update.content)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found or not owned by user")
    return NotePublic(**note)

# PUBLIC_INTERFACE
@app.delete("/notes/{note_id}", status_code=204, tags=["notes"], summary="Delete a note")
def delete_note(note_id: int, current_user: UserInDB = Depends(get_current_user)):
    """Delete a note owned by the current user."""
    success = FakeDB.delete_note(current_user.id, note_id)
    if not success:
        raise HTTPException(status_code=404, detail="Note not found or not owned by user")
    return

# Health endpoint is present.
@app.get("/", tags=["misc"], summary="Health Check")
def health_check():
    """Service health check."""
    return {"message": "Healthy"}

# Custom OpenAPI generator to include detailed descriptions/tags
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
