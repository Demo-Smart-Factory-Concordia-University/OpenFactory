import os


class Config:
    INSTANCE_PATH = os.environ.get('INSTANCE_PATH') or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///openfact.db'
    FLASK_ADMIN_SWATCH = 'cerulean'
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://'
