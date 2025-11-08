import pyrebase

firebase_config = {
    "apiKey": "AIzaSyB42dqeurcB8ts6uQj5HT78z4QBLR7NiZA",
    "authDomain": "minitravel-b11a7.firebaseapp.com",
    "databaseURL": "https://minitravel-b11a7-default-rtdb.firebaseio.com",
    "projectId": "minitravel-b11a7",
    "storageBucket": "minitravel-b11a7.firebasestorage.app",
    "messagingSenderId": "339117495091",
    "appId": "1:339117495091:web:629ab3ede80b9e84246446",
}

firebase = pyrebase.initialize_app(firebase_config)

auth = firebase.auth()
db = firebase.database()
storage = firebase.storage()