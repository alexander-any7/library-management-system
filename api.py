from src import create_app

if __name__ == "__main__":
    app = create_app()
    # from src import populate_db # uncomment this to populate the database
    app.run(debug=True)
