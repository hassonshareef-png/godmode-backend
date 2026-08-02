"""
UNUSED LEGACY MODULE.
Firebase was removed from this project. This file is kept only as a placeholder.
Do NOT import or use this module.
If you previously had a Firebase service-account JSON committed to this repo,
revoke and rotate those credentials immediately — deleting from Git does not
invalidate leaked keys.
"""

import os

firebaseConfig = {
    "apiKey": os.getenv("FIREBASE_API_KEY"),
    "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
    "projectId": os.getenv("FIREBASE_PROJECT_ID"),
    "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
    "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID"),
    "appId": os.getenv("FIREBASE_APP_ID"),
    "measurementId": os.getenv("FIREBASE_MEASUREMENT_ID"),
}
