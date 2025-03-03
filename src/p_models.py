from datetime import datetime
from typing import Optional

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict, field_validator


class BaseModel(PydanticBaseModel):
    model_config = ConfigDict(from_attributes=True)


class ListUsersSchema(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    is_active: bool
    role: str


class UserDetailSchema(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    is_active: bool
    role: str
    # categories_added: List["Category"] = []
    # books_added: List["Book"] = []


class ListCategorySchema(BaseModel):
    id: int
    name: str


class CategoryDetailSchema(BaseModel):
    id: int
    name: str
    category_added_by: str
    # books: List["Book"] = []

    @field_validator("category_added_by", mode="before")
    def convert_added_by_to_string(cls, value):
        return str(value)


class ListBookSchema(BaseModel):
    id: int
    title: str
    author: str
    isbn: str
    book_category: str
    current_quantity: int
    date_added: datetime
    location: str
    is_available: bool

    @field_validator("book_category", mode="before")
    def convert_category_to_string(cls, value):
        return str(value)


class BookDetailSchema(ListBookSchema):
    book_added_by: str
    original_quantity: int

    @field_validator("book_added_by", mode="before")
    def convert_added_by_to_string(cls, value):
        return str(value)


class ListBorrowSchema(BaseModel):
    id: int
    borrowed_book: str
    borrowed_by: str
    borrow_date: datetime
    given_by: str
    due_date: datetime
    is_returned: bool = False
    received_by: Optional[str]

    @field_validator("borrowed_book", mode="before")
    def convert_category_to_string(cls, value):
        return str(value)

    @field_validator("borrowed_by", mode="before")
    def convert_borrowed_by_to_string(cls, value):
        return str(value)

    @field_validator("given_by", mode="before")
    def convert_given_by_to_string(cls, value):
        return str(value)

    @field_validator("received_by", mode="before")
    def convert_received_by_to_string(cls, value):
        return str(value)


class DetailBorrowSchema(ListBorrowSchema):
    comments: Optional[str]


class FineListSchema(BaseModel):
    id: int
    borrow: str
    amount: float
    paid: bool = False
    date_created: datetime
    date_paid: Optional[datetime]

    @field_validator("borrow", mode="before")
    def convert_borrow_to_string(cls, value):
        return str(value)


class FineDetailSchema(FineListSchema):
    payment_method: Optional[datetime]
    transaction_id: Optional[str]
    collected_by: Optional[str]

    @field_validator("collected_by", mode="before")
    def convert_collected_by_to_string(cls, value):
        return str(value)
