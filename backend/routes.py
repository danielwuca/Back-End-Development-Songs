from . import app
import os
import json
import pymongo
from flask import jsonify, request, make_response, abort, url_for  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
from pymongo.results import InsertOneResult
from bson.objectid import ObjectId
import sys

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

# client = MongoClient(
#     f"mongodb://{app.config['MONGO_USERNAME']}:{app.config['MONGO_PASSWORD']}@localhost")
mongodb_service = os.environ.get('MONGODB_SERVICE')
mongodb_username = os.environ.get('MONGODB_USERNAME')
mongodb_password = os.environ.get('MONGODB_PASSWORD')
mongodb_port = os.environ.get('MONGODB_PORT')

print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service == None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    # abort(500, 'Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

if mongodb_username and mongodb_password:
    url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}"
else:
    url = f"mongodb://{mongodb_service}"


print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")

db = client.songs
db.songs.drop()
db.songs.insert_many(songs_list)

def parse_json(data):
    return json.loads(json_util.dumps(data))

######################################################################
# INSERT CODE HERE
######################################################################
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok', 'message': 'Service is up and running!'}), 200

@app.route('/count', methods=['GET'])
def count_num():
    count = db.songs.count_documents({})
    return jsonify({"count": count}), 200

@app.route('/song', methods=['GET'])
def songs():
    try:
        songs_cursor = db.songs.find({})
        songs_list = [parse_json(song) for song in songs_cursor]
        return jsonify({"songs": songs_list}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/song/<int:id>', methods=['GET'])
def get_song_by_id(id):
    try:
        find_song = db.songs.find_one({"id": id})
        if find_song:
            return jsonify(parse_json(find_song)), 200
        else:
            return jsonify({"message": "song with id not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/song', methods=['POST'])
def create_song():
    try:
        song = request.get_json()
        existing_song = db.songs.find_one({"id": song['id']})
        if existing_song:
            return jsonify({"Message": f"song with id {song['id']} already present"}), 302  # HTTP 302 Found
        

        result = db.songs.insert_one(song)
        return jsonify({"inserted id": str(result.inserted_id)}), 201  
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/song/<int:id>', methods=['PUT'])
def update_song(id):
    song_data = request.json
    existing_song = db.songs.find_one({"id": id})

    if existing_song:
        update_status = db.songs.update_one({"id": id}, {"$set": song_data})
        if update_status.modified_count:
            updated_song = db.songs.find_one({"id": id})
            return jsonify(updated_song), 201
        else:
            return jsonify({"message": "song found, but nothing updated"}), 200
    else:
        return jsonify({"message": "song not found"}), 404

@app.route('/song/<int:id>', methods=['DELETE'])
def delete_song(id):
    delete_status = db.songs.delete_one({"id": id})
    if delete_status.deleted_count == 1:
        return '', 204
    else:
        return jsonify({"message": "song not found"}), 404

