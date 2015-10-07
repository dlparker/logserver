import os
# SQLAlchemy database configuration. Here we are using a local sqlite3
# database
if os.environ.get('LOG_NO_HEROKU', None):
   SQLALCHEMY_DATABASE_URI = 'sqlite:///%s/log_data.sqlite3' % (os.path.dirname(__file__))
   IN_HEROKU = False
   DEBUG = True
else:
   SQLALCHEMY_DATABASE_URI = 'sqlite://'
   IN_HEROKU = True
   DEBUG = False

SQLALCHEMY_ECHO = False
# Generate a random secret key
SECRET_KEY = os.urandom(24)
# Disable debugging
LOGGING_URL = "http://localhost:5000/"
if os.environ.get('LOG_NO_HEROKU', None):
    in_heroku = False
#logging_url = "http://192.168.100.108:5001/"
