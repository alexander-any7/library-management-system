from src import create_app

if __name__ == "__main__":
    # from src import populate_db # uncomment this to populate the database
    app = create_app()
    app.run(debug=True)
