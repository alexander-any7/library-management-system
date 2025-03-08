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


class MoreUserDetailSchema(UserDetailSchema):
    books_borrowed: list["MinimalBorrowSchema"]
    fines_collected: Optional[list["FineListSchema"]]

    @field_validator("books_borrowed", mode="before")
    def list_borrows(cls, value):
        return [MinimalBorrowSchema.model_validate(borrow) for borrow in value]


class AdminUserDetailSchema(MoreUserDetailSchema):
    categories_added: list["ListCategorySchema"]
    books_added: list["ListBookSchema"]


class ListCategorySchema(BaseModel):
    id: int
    name: str


class CategoryDetailSchema(BaseModel):
    id: int
    name: str
    books: list["MinimalBookDetailSchema"]

    @field_validator("books", mode="before")
    def list_books(cls, value):
        return [MinimalBookDetailSchema.model_validate(book) for book in value]


class AdminCategoryDetailSchema(CategoryDetailSchema):
    category_added_by: str

    @field_validator("category_added_by", mode="before")
    def convert_category_added_by_to_string(cls, value):
        return str(value)


class MinimalBookDetailSchema(BaseModel):
    id: int
    title: str
    author: str
    location: str
    is_available: bool


class ListBookSchema(MinimalBookDetailSchema):
    isbn: str
    book_category: str
    current_quantity: int
    date_added: datetime

    @field_validator("book_category", mode="before")
    def convert_book_category_to_string(cls, value):
        return str(value)


class BookDetailSchema(ListBookSchema):
    book_added_by: str
    original_quantity: int

    @field_validator("book_added_by", mode="before")
    def convert_added_by_to_string(cls, value):
        return str(value)


class MoreBookDetailSchema(BookDetailSchema):
    borrows: list["ListBorrowSchema"]

    @field_validator("borrows", mode="before")
    def list_borrows(cls, value):
        return [ListBorrowSchema.model_validate(borrow) for borrow in value]


class MinimalBorrowSchema(BaseModel):
    id: int
    borrowed_book: str
    borrow_date: datetime
    is_returned: bool = False
    fines: list["FineListSchema"]

    @field_validator("borrowed_book", mode="before")
    def convert_borrowed_book_to_string(cls, value):
        return str(value)

    @field_validator("fines", mode="before")
    def list_fines(cls, value):
        return [FineListSchema.model_validate(fine) for fine in value]


class ListBorrowSchema(MinimalBorrowSchema):
    borrowed_by: str
    given_by: str
    due_date: datetime
    received_by: Optional[str]

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


class AdminListBorrowSchema(MinimalBorrowSchema):
    given_by: str
    due_date: datetime
    received_by: Optional[str]
    borrowed_by: ListUsersSchema

    @field_validator("borrowed_by", mode="before")
    def borrowed_by(cls, value):
        return ListUsersSchema.model_validate(value)

    @field_validator("given_by", mode="before")
    def convert_given_by_to_string(cls, value):
        return str(value)

    @field_validator("received_by", mode="before")
    def convert_received_by_to_string(cls, value):
        return str(value)


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
    payment_method: Optional[str]
    transaction_id: Optional[str]
    collected_by: Optional[str]

    @field_validator("collected_by", mode="before")
    def convert_collected_by_to_string(cls, value):
        return str(value)


class AdminFineListSchema(BaseModel):
    id: int
    borrow: AdminListBorrowSchema
    amount: float
    paid: bool = False
    date_created: datetime
    date_paid: Optional[datetime]
    payment_method: Optional[str]
    transaction_id: Optional[str]
    collected_by: Optional[str]

    @field_validator("collected_by", mode="before")
    def convert_collected_by_to_string(cls, value):
        return str(value)

    @field_validator("borrow", mode="before")
    def display_borrow(cls, value):
        return AdminListBorrowSchema.model_validate(value)
