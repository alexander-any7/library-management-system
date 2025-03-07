import flet as ft
from book_add import BookAdd
from book_detail import BookDetail
from search_books import SearchBook


def main(page: ft.Page):
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    def route_change(route):
        page.views.clear()
        page.views.append(SearchBook(page).get_view())

        if "/books/" in page.route:
            # get the path and query
            split_url = page.route.split("?")
            path = split_url[0]
            page_id = int(path.split("/")[-1])
            page.views.append(BookDetail(page=page, id=page_id).get_view())

        elif "/add-book" in page.route:
            page.views.append(BookAdd(page=page).get_view())

        page.update()

    def view_pop(view):
        page.views.pop()
        top_view = page.views[-1]
        page.go(top_view.route)

    page.on_route_change = route_change
    page.on_view_pop = view_pop
    page.go(page.route)


ft.app(main)
