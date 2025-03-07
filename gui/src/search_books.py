import flet as ft
from fetch import FetchHelper


class SearchBook:
    def __init__(self, page: ft.Page, url: str = None, query_params: dict = None):
        self.page = page
        self.search_term = None
        self.search_field = ft.TextField(
            label="Search books...", on_change=self.update_search, on_submit=self.update_search
        )
        self.fetch_helper = FetchHelper()
        self.url = "http://localhost:5000/books"
        self.query_params = query_params

    def get_view(self):
        return ft.View("/books", self.view_build())

    def view_build(self):
        self.page.title = "Search Books"
        return self.search_box_row(), self.search_results()

    def search_box_row(self):
        return ft.Container(
            ft.Column(
                [
                    ft.Row(
                        [
                            self.search_field,
                        ]
                    ),
                    ft.Row(
                        [
                            ft.TextButton(
                                "Add new book",
                                icon=ft.icons.ADD_CIRCLE,
                                on_click=lambda _: self.page.go("/add-book"),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                ]
            ),
            margin=ft.margin.only(top=20, bottom=40),
        )

    def update_search(self, _):
        self.search_term = self.search_field.value
        self.page.views.clear()
        self.page.views.append(self.get_view())
        self.page.update()

    def clear_search(self, e):
        self.search_field.value = None
        self.update_search(e)

    def search_results(self):
        return ft.ListView(spacing=3, controls=self.results(), expand=1)

    def results(self):
        if self.search_term is None:
            response = self.fetch_helper.fetch(self.url, method="get")

        results = []
        for book in response.books:
            # create the on_click function that goes to the book detail for BookDetail
            column = ft.Column(
                [
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Row(
                                    [
                                        ft.Text(book.title),
                                    ]
                                ),
                                ft.Row(
                                    [
                                        ft.IconButton(
                                            icon=ft.icons.NAVIGATE_NEXT,
                                            on_click=lambda _, s_id=book.id: self.page.go(
                                                f"/books/{s_id}"
                                            ),
                                        ),
                                    ]
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                    ),
                    ft.Divider(height=9, thickness=3),
                ],
            )

            results.append(column)

        return results
