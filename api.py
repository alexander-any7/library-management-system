from flask import Flask, Response, request
from flask_restx import Api, Resource

app = Flask(__name__)
api = Api(app)

random_data = [{i: f"Book Title {i}"} for i in range(10)]


@api.route("/hello")
class HelloWorld(Resource):
    def get(self):
        return {"hello": "world"}


@api.route("/books")
class Books(Resource):
    def get(self):
        return random_data

    def post(self):     
        data = request.json
        print(data)   
        return Response(status=201)


@api.route("/books/<int:id>")
@api.doc(params={"id": "Book ID"})
class Book(Resource):
    def get(self, id):
        try:
            return random_data[id][id]
        except IndexError:
            return {"message": "Book not found"}, 404


if __name__ == "__main__":
    app.run(debug=True)
