import flet as ft
from fetch import FetchHelper  # noqa
from fields import TextField


class BookAdd:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.name_field = TextField(label="Name")

    def get_view(self):
        """Returns the view"""
        self.page.title = "Add Book"
        return ft.View("/add-book", self.view_build())

    def view_build(self):
        """Returns the stack to be used for the view"""
        return [
            ft.Container(
                ft.TextButton(
                    "Back",
                    icon=ft.icons.ARROW_BACK_IOS,
                    on_click=lambda _: self.page.go("/books"),
                ),
                alignment=ft.alignment.top_right,
            )
        ]

    def close_dialogue(self, dialog: ft.AlertDialog):
        """Just closes whichever dialog is passed to it and updates the page"""
        dialog.open = False
        self.page.update()
