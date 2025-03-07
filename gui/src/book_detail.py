import flet as ft
from fetch import FetchHelper


class BookDetail:
    def __init__(self, page: ft.Page, id) -> None:
        self.page = page
        self.book_id = id
        self.fetch_helper = FetchHelper()
        self.response = self.fetch_helper.fetch(f"http://localhost:5000/books/{self.book_id}")
        self.book = self.response.book
        self.queries = self.response.queries
        self.page.title = self.book.title

    def get_view(self):
        return ft.View(f"/books/{self.book_id}", list(self.view_build()))

    def view_build(self):
        return [self.book_detail()]

    def book_detail(self):
        return ft.Container(
            ft.Column(
                [
                    ft.Text(self.book.title),
                    ft.Text(self.book.author),
                ],
                alignment=ft.CrossAxisAlignment.START,
            ),
        )
