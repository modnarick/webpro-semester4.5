from sqlmodel import Field, SQLModel
from sqlalchemy import LargeBinary
from typing import Optional

class UserBase(SQLModel):
    email: str
    password: str

class User(UserBase, table=True):
    id: int = Field(default=None, primary_key=True)

class Commision(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    commision_name: str
    commision_desc: str
    commision_image: Optional[bytes] = Field(default=None, sa_column=LargeBinary)
    is_taken: bool = Field(default=False)
