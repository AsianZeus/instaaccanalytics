from flask import Flask, request, render_template, redirect, url_for
import os
from instagrapi import Client
from instagrapi.types import User
import requests
import pyrebase
from threading import Thread
import threading
import time
import pickle

app = Flask(__name__)

user, db, user_name, user_data, password, user_insta_data = '', '', '', '', '', ''

FIREBASE_CONFIG = {
    'apiKey': os.getenv('apiKey'),
    'authDomain': os.getenv('authDomain'),
    'databaseURL': os.getenv('databaseURL'),
    'projectId': os.getenv('projectId'),
    'storageBucket': os.getenv('storageBucket'),
    'messagingSenderId': os.getenv('messagingSenderId'),
    'appId': os.getenv('appId')
}

Gender_ar = ['Female', 'Male', 'Custom', 'Prefer Not To Say']


def connect_database(firebaseconfig):
    firebase = pyrebase.initialize_app(firebaseconfig)
    db = firebase.database()
    return db


def getResigteredUsers(db):
    val = db.child("Users").get().val()
    try:
        return list(val)
    except:
        return []


start = time.time()
try:
    db = connect_database(FIREBASE_CONFIG)
except:
    print("Database Connection Error")
print("database connected: ", time.time()-start)

start = time.time()
REGISTERED_USERS = getResigteredUsers(db)
print("got registered user: ", time.time()-start)


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
    media_count = details.media_count
    return (name, username, profile_pic, bio, is_private, followers_count, following_count, media_count)


def get_followers(user, userid):
    followers = user.user_followers(userid)
    return sorted(list(followers.keys()))


def get_following(user, userid):
    followers = user.user_following(userid)
    return sorted(list(followers.keys()))


def getFollowersFromDatabase(db, user_name):
    return sorted(list(db.child("Users").child(user_name).get().val()['followers']))


def update(db, user_name, data):
    db.child("Users").child(user_name).set(data)


def get_details(db, user_name):
    user_data = db.child("Users").child(user_name).get()
    return user_data


def getSpecificDetail(user_data, key):
    return user_data.val()[key]


def delete(db, user_name):
    user_data = db.child("Users").child(user_name).remove()


def download_media(user, userid, mediacount):
    medias = user.user_medias(userid, mediacount)
    for i in range(mediacount):
        try:
            r = requests.get(
                str(medias[i].thumbnail_url), allow_redirects=True)
            open(f'{userid}_{i}.jpg', 'wb+').write(r.content)
        except e:
            print(e)


def push_data(user, db, password):
    # Information retrival
    userid, email, mobileno, gender, birthday = get_account_details(user)
    name, username, profile_pic, bio, is_private, followers_count, following_count, media_count = get_user_info(
        user, userid)
    # Pushing Data
    print('got alll dataaa')
    globals()['user_insta_data'] = {'userid': userid, 'password': password, 'name': name, 'email': email, 'mobileno': mobileno, 'gender': gender, 'birthday': birthday, 'profile_pic': profile_pic, 'bio': bio, 'is_private': is_private, 'followers_count': followers_count,
                                    'following_count': following_count, 'media_count': media_count, 'followers': get_followers(user, userid), 'following': get_following(user, userid), 'unfollowers': [], 'recent_unfollowers': [], 'followers_you_dont_follow': [], 'users_dont_follow_back': []}
    db.child("Users").child(username).set(user_insta_data)


def check_unfollowers(li1, li2):
    li_dif = [i for i in li1 + li2 if i not in li1 or i not in li2]
    return li_dif


@app.route('/save_info', methods=["GET", "POST"])
def temp_to_profile():
    if request.method == "POST":
        return redirect(url_for('loadProfile'))


@app.route('/temp')
def loadProfile():
    while True:
        if(not 'PushData' in [thread.name for thread in threading.enumerate()]):
            print('PushData Thread Finished!')
            break

    name = globals()['user_insta_data']['name']
    bio = globals()['user_insta_data']['bio']
    profile_pic = globals()['user_insta_data']['profile_pic']
    followers_count = globals()['user_insta_data']['followers_count']
    following_count = globals()['user_insta_data']['following_count']
    media_count = globals()['user_insta_data']['media_count']
    try:
        r = requests.get(profile_pic, allow_redirects=True)
        open(f'./static/{user_name}.jpg', 'wb+').write(r.content)
    except e:
        print(e)
    return render_template("profile.html", name=name, profile_pic=user_name+'.jpg', bio=bio, user_name=user_name, followers_count=followers_count, following_count=following_count, media_count=media_count)


@app.route('/', methods=["GET", "POST"])
def instahack():
    if request.method == "POST":
        globals()['user_name'] = request.form.get("uname")
        globals()['password'] = request.form.get("pword")
        try:
            globals()['user'] = login(user_name, password)
            print('Login Sucessfull!')

        except:
            return 'Login Error: Please enter correct username and password!'
        globals()['user_data'] = get_details(db=db, user_name=user_name)
        if(user_name in REGISTERED_USERS):
            name = getSpecificDetail(user_data=user_data, key='name')
            bio = getSpecificDetail(user_data=user_data, key='bio')
            profile_pic = getSpecificDetail(
                user_data=user_data, key='profile_pic')
            followers_count = getSpecificDetail(
                user_data=user_data, key='followers_count')
            following_count = getSpecificDetail(
                user_data=user_data, key='following_count')
            media_count = getSpecificDetail(
                user_data=user_data, key='media_count')
            try:
                r = requests.get(profile_pic, allow_redirects=True)
                open(f'./static/{user_name}.jpg', 'wb+').write(r.content)
            except e:
                print(e)
            return render_template("profile.html", profile_pic=user_name+'.jpg', name=name, bio=bio, user_name=user_name, followers_count=followers_count, following_count=following_count, media_count=media_count)
        else:
            t1 = Thread(target=push_data, name='PushData',
                        args=(user, db, password))
            t1.start()
            return render_template("save_info.html")

    return render_template("index.html")


def upload_data(user, user_name, password):
    start = time.time()
    followersI = sorted(get_followers(user, user_name))
    print(f'calculated Followers in {time.time()-start}')
    followersD = getFollowersFromDatabase(db, user_name)
    unfollowers_list = check_unfollowers(followersD, followersI)
    return f"Welcome Back!\nPeople who unfollowed you: {', '.join([user.username_from_user_id(id) for id in unfollowers_list])}"


if __name__ == '__main__':
    app.run()
