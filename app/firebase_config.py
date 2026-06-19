import firebase_admin
from firebase_admin import credentials, auth

firebaseConfig = {
    "apiKey": "AIzaSyCjDmBqoUBAhhqAQ3Y46KzQET2AUU0TtrA",
    "authDomain": "godmode-app.firebaseapp.com",
    "projectId": "godmode-app",
    "storageBucket": "godmode-app.firebasestorage.app",
    "messagingSenderId": "832029650032",
    "appId": "1:832029650032:web:caef5a08835a2c0b1558b5",
    "measurementId": "G-P9RQLPRZ5Q"
}

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)

