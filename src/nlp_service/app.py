import os

from flask import Flask
from flask import request
from controllers import nlpController
import util

util.load_src_dir_to_sys_path()
from postgresql_db import database

app = Flask(__name__)

# DB Setup
db = database.connect(app, 'postgres', os.environ['POSTGRES_PASSWORD'], 'postgres')
#db = database.connect(app, 'postgres', 'postgres', 'postgres', host='127.0.0.1')


@app.route("/claim_category", methods=['POST'])
def classify_claim_category():
    input = request.get_json()
    return nlpController.classify_claim_category(input['conversation_id'], input['message'])


@app.route("/submit_message", methods=['POST'])
def submit_message():
    input = request.get_json()
    return nlpController.process_user_input(input['conversation_id'], input['message'])
