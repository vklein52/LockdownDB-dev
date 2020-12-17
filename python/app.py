from flask import Flask
from flask import render_template
from flask import g
from flask import request
import json
from lockdown import Cell

import lockdown

app = Flask(__name__, static_folder="static")

DATABASE = 'demodb.sqlite'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = lockdown.LockdownConnection(DATABASE)
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/insert_test', methods=['POST'])
def insert_test():
  j = json.loads(request.data)
  cur = get_db().cursor()
  cur.execute("INSERT INTO Tweets (Content, Owner, SSN) VALUES (?, ?, ?)", (Cell.from_json(request.data), 0,""))
  return "GOOD JOB LOSER"

@app.route('/search_test', methods=['POST'])
def search_test():
  j = json.loads(request.data)
  cur = get_db().cursor()
  cur.execute("SELECT id, Content FROM Tweets WHERE Content LIKE '%im_useless%'", pub_key=j["pub_key"], search_keys=j["search_keys"])
  fetch = cur.fetchall()
  return json.dumps(fetch)

@app.route('/')
def index():
  return render_template("index.html")
