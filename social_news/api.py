"""Webpage that lists news stories and allows users to upvote/downvote them."""
import psycopg2
import psycopg2.extras
from flask import Flask, current_app, jsonify, request, Response
from news_scaper import get_db_connection

app = Flask(__name__)

conn = get_db_connection()

def execute_db_query(query: str, params: tuple = ()) -> dict:
    """Executes query on database and returns relevant data."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as curs:
        curs.execute(query, params)
        db_data = curs.fetchall()
    if len(list(db_data)) == 0:
        raise TypeError("No query matches.")
    return db_data

@app.route("/", methods=["GET"])
def index() -> Response:
    """Displays homepage in window."""
    return current_app.send_static_file("index.html")

@app.route("/stories", methods=["GET"])
def stories() -> dict:
    """Gets all stories from the database."""
    try:
        db_data = execute_db_query("""SELECT stories.id, title, url, stories.created_at, stories.updated_at,
                                      SUM(CASE direction WHEN 'up' THEN 1 WHEN 'down' THEN -1 ELSE 0 END) AS score 
                                      FROM stories LEFT JOIN votes ON stories.id=votes.story_id 
                                      GROUP BY stories.id, title, url, stories.created_at, stories.updated_at 
                                      ORDER BY score DESC;""")
        stories_dict = {"stories": db_data,
                        "success": True,
                        "total_stories": len(list(db_data))}
        return jsonify(stories_dict), 200
    except TypeError as err:
        print(err)
        return jsonify({"error": True,
                        "message": "Unable to retrieve stories."}), 500

@app.route("/stories/<int:id>/votes", methods=["POST"])
def vote(id: int) -> list:
    """Increments score of an article if upvote; decrements if downvote."""
    if request.method == 'POST':
        try:
            data = request.json
            command = """WITH ROWS AS (INSERT INTO votes (direction, created_at, updated_at, story_id)
                         VALUES (%s, DEFAULT, DEFAULT, %s))
                         SELECT * FROM votes;"""
            value = data['direction']
            db_data = execute_db_query(command, (value, id))
            return jsonify(db_data), 200
        except TypeError as err:
            print(err)
            return jsonify([{"error": True,
                             "message": "Unable to vote for stories."}]), 400
        except KeyError as err:
            print(err)
            return jsonify([{"error": True,
                             "message": "Malformed request body."}]), 400

@app.route("/search", methods=["GET"])
def search() -> list:
    """Finds stories with tags given in query."""
    tags = request.args.get('tags').split(",")
    result = []
    for tag in tags:
        query = """SELECT title, url, tags.description FROM stories
                   JOIN metadata ON stories.id = metadata.story_id
                   JOIN tags ON metadata.tag_id = tags.id
                   WHERE tags.description = %s"""
        tag = tag[0].upper() + tag[1:].lower()
        params = (tag,)

        try:
            db_data = execute_db_query(query, params)
        except Exception as err:
            print(err)
            return jsonify(["Invalid tag."]), 400

        for i in range(len(db_data)):
            title = db_data[i]['title']
            url = db_data[i]['url']
            description = db_data[i]['description']
            result.append([title, url, description])
    return jsonify(result)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)