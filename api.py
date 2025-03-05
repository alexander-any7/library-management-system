if __name__ == "__main__":
    import os

    os.environ["FLASK_ENV"] = "dev"
    from src import create_app

    app = create_app()
    # from src import populate_db # uncomment this to populate the database
    app.run(debug=True)
