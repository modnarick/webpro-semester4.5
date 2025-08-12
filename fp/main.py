from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from contextlib import asynccontextmanager
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from database import create_db_and_tables, get_session
from model import UserBase, User, Commision
from sqlmodel import Session
from typing import Optional
import base64

SECRET_KEY = "bababooey"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)):
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
    except JWTError:
        raise credentials_exception

    user = session.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

@app.post("/register")
def register(user: UserBase, session: Session = Depends(get_session)):
    existing_user = session.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_pw = get_password_hash(user.password)
    new_user = User(email=user.email, password=hashed_pw)
    session.add(new_user)
    session.commit()
    session.refresh(new_user)

    access_token = create_access_token(data={"sub": new_user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    user = session.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=400, detail="Invalid username or password")

    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/commision")
def post_commision(
    commision_name: str = Form(...),
    commision_desc: str = Form(...),
    commision_image: UploadFile = File(None),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    image_bytes = commision_image.file.read() if commision_image else None

    comms = Commision(
        commision_name=commision_name,
        commision_desc=commision_desc,
        commision_image=image_bytes,
        is_taken=False
    )
    session.add(comms)
    session.commit()
    session.refresh(comms)

    return {
        "id": comms.id,
        "commision_name": comms.commision_name,
        "commision_desc": comms.commision_desc,
        "is_taken": comms.is_taken,
        "owner": current_user.email
    }


@app.get("/commisions")
def get_commisions(session: Session = Depends(get_session)):
    commisions = session.query(Commision).all()
    return [
        {
            "id": c.id,
            "commision_name": c.commision_name,
            "commision_desc": c.commision_desc,
            "is_taken": c.is_taken,
            "image": base64.b64encode(c.commision_image).decode("utf-8") if c.commision_image else None
        }
        for c in commisions
    ]

@app.delete("/commision/{commision_id}")
def delete_commision(
    commision_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    commision = session.query(Commision).filter(Commision.id == commision_id).first()
    if not commision:
        raise HTTPException(status_code=404, detail="Commission not found")
    
    session.delete(commision)
    session.commit()
    
    return {"message": "Commission taken and removed successfully"}

@app.delete("/commision")
def delete_all(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    commisions = session.query(Commision).filter(Commision.commision_name != "ke hack").all()
    for commision in commisions:
        session.delete(commision)
    session.commit()

    return {"message": "Deleted"}
