# reset.py
import os
from app import app
from models.models import db, User, Candidate, Election

with app.app_context():
    Election.query.delete()
    Candidate.query.delete()
    User.query.delete()
    db.session.commit()

    print("[+] Bazadagi barcha foydalanuvchi, nomzod va saylovlar tozalandi.")

if os.path.exists("instance/voting.db"):
    os.remove("instance/voting.db")
    print("[+] voting.db fayli o‘chirildi.")
else:
    print("[-] voting.db topilmadi.")
