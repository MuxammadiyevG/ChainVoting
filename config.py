import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'very-hard-to-guess-key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI') or 'sqlite:///voting.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Blockchain konfiguratsiyasi
    BLOCKCHAIN_PROVIDER = os.environ.get('BLOCKCHAIN_PROVIDER') or 'http://127.0.0.1:7545'  # Ganache uchun lokal provider
    CONTRACT_ADDRESS = os.environ.get('CONTRACT_ADDRESS')
    ADMIN_ADDRESS = os.environ.get('ADMIN_ADDRESS')
    ADMIN_PRIVATE_KEY = os.environ.get('ADMIN_PRIVATE_KEY')