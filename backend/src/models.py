from datetime import datetime
from typing import List

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass

    def __str__(self):
        return self.__repr__()


class UserAccount(Base):
    __tablename__ = "user_account"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(50), unique=True)
    first_name: Mapped[str] = mapped_column(String(20), nullable=False)
    last_name: Mapped[str] = mapped_column(String(20), nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, server_default="1"
    )
    role: Mapped[str] = mapped_column(
        String(20), default="student", nullable=False, server_default="student"
    )
    categories_added: Mapped[List["Category"]] = relationship(
        "Category", back_populates="category_added_by"
    )
    books_added: Mapped[List["Book"]] = relationship("Book", back_populates="book_added_by")

    # Explicitly specify foreign_keys
    books_borrowed: Mapped[List["Borrow"]] = relationship(
        "Borrow", back_populates="borrowed_by", foreign_keys="[Borrow.borrowed_by_id]"
    )
    books_given: Mapped[List["Borrow"]] = relationship(
        "Borrow", back_populates="given_by", foreign_keys="[Borrow.given_by_id]"
    )
    books_received: Mapped[List["Borrow"]] = relationship(
        "Borrow", back_populates="received_by", foreign_keys="[Borrow.received_by_id]"
    )
    fines_collected: Mapped[List["Fine"]] = relationship(
        "Fine", back_populates="collected_by", foreign_keys="[Fine.collected_by_id]"
    )

    def __repr__(self):
        return self.first_name + " " + self.last_name


class Category(Base):
    __tablename__ = "category"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(20), nullable=False)
    added_by_id = mapped_column(ForeignKey("user_account.id"))

    category_added_by: Mapped[UserAccount] = relationship(back_populates="categories_added")
    books: Mapped[List["Book"]] = relationship("Book", back_populates="book_category")

    def __repr__(self):
        return self.name


class Book(Base):
    __tablename__ = "book"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    author: Mapped[str] = mapped_column(String(50), nullable=False)
    isbn: Mapped[str] = mapped_column(String(25), unique=True, nullable=False)
    category_id = mapped_column(ForeignKey("category.id"))
    original_quantity: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False, server_default="1"
    )
    current_quantity: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False, server_default="1"
    )
    date_added: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    added_by_id = mapped_column(ForeignKey("user_account.id"))
    is_available: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, server_default="1"
    )
    location: Mapped[str] = mapped_column(String(20))

    book_category: Mapped[Category] = relationship(back_populates="books")
    book_added_by: Mapped[UserAccount] = relationship(back_populates="books_added")

    borrows: Mapped[List["Borrow"]] = relationship("Borrow", back_populates="borrowed_book")

    def __repr__(self):
        return self.title


class Borrow(Base):
    __tablename__ = "borrow"

    id: Mapped[int] = mapped_column(primary_key=True)
    book_id = mapped_column(ForeignKey("book.id"))
    borrowed_by_id = mapped_column(ForeignKey("user_account.id"))
    given_by_id = mapped_column(ForeignKey("user_account.id"))
    received_by_id = mapped_column(ForeignKey("user_account.id"))
    borrow_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    due_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    return_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    comments: Mapped[str] = mapped_column(String, nullable=True)
    is_returned: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default="0"
    )

    borrowed_book: Mapped[Book] = relationship(back_populates="borrows")

    # Explicitly specify foreign_keys
    borrowed_by: Mapped[UserAccount] = relationship(
        "UserAccount", back_populates="books_borrowed", foreign_keys=[borrowed_by_id]
    )
    given_by: Mapped[UserAccount] = relationship(
        "UserAccount", back_populates="books_given", foreign_keys=[given_by_id]
    )
    received_by: Mapped[UserAccount] = relationship(
        "UserAccount", back_populates="books_received", foreign_keys=[received_by_id]
    )
    fines: Mapped[List["Fine"]] = relationship("Fine", back_populates="borrow")

    def __repr__(self):
        return self.borrowed_book.title


class Fine(Base):
    __tablename__ = "fine"

    id: Mapped[int] = mapped_column(primary_key=True)
    borrow_id = mapped_column(ForeignKey("borrow.id"))
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    paid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default="0")
    date_created: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    date_paid: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    payment_method: Mapped[str] = mapped_column(String(15), nullable=True)
    transaction_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=True)
    collected_by_id = mapped_column(ForeignKey("user_account.id"), nullable=True)

    borrow: Mapped[Borrow] = relationship(back_populates="fines")
    collected_by: Mapped[UserAccount] = relationship(back_populates="fines_collected")
