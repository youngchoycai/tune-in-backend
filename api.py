from flask import Flask, request, redirect 
from flask import session as flasksession
from flask_cors import CORS, cross_origin
#from spot_auth import user_id, user_name, user_profile_pic
from spot_calls import get_top_tracks, get_top_tracks_all_terms, get_top_artists_all_terms, get_top_artists, recommend_tracks, generate_party_playlist
from database import Database, TopTracks, TopArtists, Users, Party, PartyTracks
from sqlalchemy.orm import Session
from contextlib import contextmanager
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import creds
import json
from coolname import generate_slug
import base64
import os

app = Flask("__main__")
CORS(app, resources={r"/*": {"origins": "*"}})
app.config['CORS_HEADERS'] = 'Content-Type'
# db = Database()
# party_id = 'able-shrewd-sunfish'
# with session_scope(db) as session:
#   db.grant_host(user_id, party_id, session)
#   db.create_party(696969, session)
#   db.delete_user_from_database(user_id, session)
#   db.delete_user_data(user_id, Users, session)
#   db.delete_user_data(user_id, TopTracks, session)
#   db.delete_user_data(user_id, TopArtists, session)

@contextmanager
def session_scope(db):
    #Provides a transactional scope around our session operations.
    session = Session(bind=db.connection)
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()

CACHE = ".userinfo"
scope = base64.b64encode('playlist-modify-public user-read-email user-top-read') #user-follow-read
spotify_obj = None
top_tracks_all_terms = None 
top_artists_all_terms = None 
user_id = None
user_name = None
user_profile_pic = None
spot_client_id = os.environ.get("SPOTIPY_CLIENT_ID", None)
spot_client_secret = os.environ.get("SPOTIPY_CLIENT_SECRET", None)
spot_client_redirect = base64.b64encode("https://tune-in-pp-llc.herokuapp.com/api_callback/") #"http://localhost:8888/" 

@app.route('/', methods = ['GET'])
def hello():
    return "hello"

@app.route('/api/test', methods = ['GET'])
def test():
    return "kekw why doesnt this work"


@app.route('/api/login', methods = ['GET'])
@cross_origin(origin='*',headers=['Content-Type','Authorization'])
def login_user():
    """
    global user_id, user_name, user_profile_pic, spotify_obj, top_artists_all_terms, top_tracks_all_terms
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(spot_client_id, spot_client_secret, spot_client_redirect, scope=scope))
    #user_id = sp.me()['id']
    user_name = sp.me()['display_name']
   # user_profile_pic = sp.me()['images'][0]['url'] if not '' else 'https://www.uokpl.rs/fpng/d/490-4909214_swag-wooper-png.png'
    #spotify_obj = sp
    #top_tracks_all_terms = get_top_tracks_all_terms(spotify_obj)
    #top_artists_all_terms = get_top_artists_all_terms(spotify_obj)
    #db = Database()
    #with session_scope(db) as session:
       # update_user_data(user_id, db, session)

    return str(user_name) 
    """
    sp_oauth = spotipy.oauth2.SpotifyOAuth(client_id = spot_client_id, client_secret = spot_client_secret,redirect_uri = spot_client_redirect, scope=scope)
    auth_url = sp_oauth.get_authorize_url()
    print(auth_url)
    print("ooh")
    return auth_url

@app.route("/api_callback/")
def api_callback():
    """
    # Don't reuse a SpotifyOAuth object because they store token info and you could leak user tokens if you reuse a SpotifyOAuth object
    sp_oauth = spotipy.oauth2.SpotifyOAuth(spot_client_id, spot_client_secret, spot_client_redirect, scope=scope)
    flasksession.clear()
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)

    # Saving the access token along with all other token related info
    flasksession["token_info"] = token_info


    return redirect("index")
    """
    return "aye lmao"
    
@app.route('/api/create', methods = ['GET'])
def create_party():
    new_party_name = generate_slug(3)
    db = Database()
    with session_scope(db) as session:
        return party_creation_helper(new_party_name, user_id, db, session)
    
#if people create multiple parties, we leave them. create function later to delete them after a day or something if no one else adds to it
def party_creation_helper(party_id, user_id, db, session): 
    while db.party_id_exists_in_table(party_id, Party, session):
        party_id = generate_slug(3)
    db.create_party(party_id, user_id, session)
    return party_id

@app.route('/api/join', methods = ['POST'])
def join_party():
    if request.method == 'POST':
        json_data = request.get_json()
        party_name = json_data['partyNameToJoin']
        db = Database()
        with session_scope(db) as session:
            return party_joining_helper(user_id, party_name, db, session)
        

def party_joining_helper(user_id, party_id, db, session):
    if db.party_id_exists_in_table(party_id, Party, session):
        if db.user_exists_in_party(user_id, party_id, session):
            return "You're already in this party!"
        else:
            db.add_to_party(user_id, party_id, session)
            return "Joined Successfully!"
    else: 
        return "This party doesn't exist!"

@app.route('/api/find', methods = ['POST'])
def find_party_playlist():
    if request.method == 'POST':
        json_data = request.get_json()
        party_name = json_data['partyNameToFind']
        db = Database()
        with session_scope(db) as session:
            return party_finding_helper(user_id, party_name, db, session)

def party_finding_helper(user_id, party_id, db, session):
    if db.party_id_exists_in_table(party_id, Party, session):
        if db.user_exists_in_party(user_id, party_id, session):
            playlist = preview_party_playlist(party_id)
            playlist_name = save_party_playlist(party_id)
            playlist_link = get_playlist_link(playlist_name)
            return json.dumps({'playlistLink': playlist_link, 'cardInfo': scrape_tracks(playlist['tracks'], 7)})
        else: 
            return "Hey! You're not in this party!"
    else:
        return "This party doesn't exist!"
     
def scrape_tracks(tracks, num_to_scrape):
    return [get_track_card_info(track) for track in tracks[0:num_to_scrape+1]]
    
def get_track_card_info(track_obj): 
    song_name = track_obj['name']
    artist = track_obj['artists'][0]['name']
    track_image = track_obj['album']['images'][0]['url']
    song_url = track_obj["external_urls"]["spotify"]
    return [song_name, artist, track_image, song_url]

def update_user_data(user_id, db, session):
    # user_id = '696969'
    if db.user_exists_in_table(user_id, Users, session):
        assert db.user_exists_in_table(user_id, TopTracks, session) and db.user_exists_in_table(user_id, TopArtists, session)
        db.update_login_time(user_id, session)
        db.save_user_tops(user_id, top_tracks_all_terms, top_artists_all_terms, session, update=True)
    else:
        db.create_user(user_id, user_name, user_profile_pic, session)
        db.save_user_tops(user_id, top_tracks_all_terms, top_artists_all_terms, session)

def preview_party_playlist(party_id):
    # on click, calculates seeds for users in party and displays recommended tracks, can be refreshed
    #party_id = fetch_party_id_from_url()
    db = Database()
    with session_scope(db) as session:
        party_users = db.get_party_users(party_id, session)
        shared_tracks = db.get_shared(party_users, TopTracks, session)
        shared_artists = db.get_shared(party_users, TopArtists, session)
        seed_tracks = db.get_k_seeds(shared_tracks, 3)
        seed_artists = db.get_k_seeds(shared_artists, 2)
        results = recommend_tracks(spotify_obj, tracks=seed_tracks, artists=seed_artists)

        # save results to database
        if db.party_id_exists_in_table(party_id, PartyTracks, session):
            recommended_tracks = [{'b_party_id': party_id, 'b_track_id': track['id'], 'b_track_number': i} for i, track in enumerate(results['tracks'])]
            db.update_party_tracks(recommended_tracks, session)
        else:
            recommended_tracks = [PartyTracks(party_id=party_id, track_id=track['id'], track_number=i) for i, track in enumerate(results['tracks'])]
            db.bulk_save_data(recommended_tracks, session)
    return results
    # display proposed tracks on front-end here
    # print("Recommended tracks:")
    # for track in results['tracks']:
    #     print(track['name'], "by", track['artists'][0]['name'])

def save_party_playlist(party_id): # button appears after displaying recommended tracks
    #party_id = fetch_party_id_from_url()
    db = Database()
    with session_scope(db) as session:
        recommended_tracks = db.get_party_tracks(party_id, session)

    playlist_name = "it is PIZZATIME."
    playlist_desc = "ah sahhhhhhhhh düd"
    with open("playlistpic.jpg", "rb") as image_file:
        playlist_jpg = base64.b64encode(image_file.read())
    #spotify_obj.playlist_upload_cover_image(playlist_name, playlist_jpg)
    return generate_party_playlist(spotify_obj, user_id, playlist_name, recommended_tracks, playlist_desc, playlist_jpg)
    
def get_playlist_link(playlist_id):
    playlist_link = spotify_obj.playlist(playlist_id, fields = "external_urls")
    return playlist_link["external_urls"]["spotify"]

"""
@app.route("/")
def login_redirect():
    db = Database()
    with session_scope(db) as session:
        update_user_data(db, session)
    namez = [tt["name"] + ' - ' + tt['artists'][0]["name"] for term in top_tracks_all_terms for tt in term]
    artz = [ta["name"] for term in top_artists_all_terms for ta in term]
    return flask.render_template("index.html", trax=namez, art=artz)

@app.route("/party/<party_id>") # we provide invite link, which is unique to every party
def party_invite(party_id):
    db = Database()
    with session_scope(db) as session:
        update_user_data(db, session)
        if not db.user_exists_in_party(user_id, party_id, session):
            db.add_to_party(user_id, party_id, session)
    
    # on click
    results = preview_party_playlist()
    namez = [track["name"] + ' - ' + track['artists'][0]["name"] for track in results['tracks']]
    return flask.render_template("index.html", trax=namez)
    
    # save_party_playlist()
    # return 'issa party' # party page

def fetch_party_id_from_url():
    url = request.path
    tag = '/party/'
    party_id = url[url.index(tag) + len(tag) : len(url)]
    return party_id

def leave_party(): # on click
    party_id = fetch_party_id_from_url()
    db = Database()
    with session_scope(db) as session:
        if db.is_host(user_id, party_id, session):
            # if no one else is in party, delete party (db.delete_party_data())
            if len(db.get_party_users(party_id, session)) == 1:
                print('yeehaw')
                db.delete_party_data(party_id, session)
            else:
                db.delete_user_from_party(user_id, party_id, session)
                new_host = db.get_party_users(party_id, session)[0]
                db.grant_host(new_host, party_id, session)
        else:
            db.delete_user_from_party(user_id, party_id, session)
    # redirect to homepage or party directory
"""
"""
if __name__ == "__main__":    
    app.run(debug=True)
"""


if __name__ == '__main__':
    app.run(host='0.0.0.0')

"""
    https://accounts.spotify.com/authorize?client_id=%222330b5ffbc5e4ff8906796e4a3fcb8c3%22&response_type=code&redirect_uri=https%3A%2F%2Ftune-in-pp-llc.herokuapp.com%2Fapi_callback%2F&scope=playlist-modify-public+user-read-email+user-top-read
    https://accounts.spotify.com/en/authorize?client_id=0e61efc53ed04155888413944e4982fa&redirect_uri=https:%2F%2Fsalty-beach-42139.herokuapp.com%2Fapi%2Fcallback&scope=user-read-email%20user-top-read&response_type=code
    """