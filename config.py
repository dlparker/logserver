import os
# SQLAlchemy database configuration. Here we are using a local sqlite3
# database
if os.environ.get('LOG_NO_HEROKU', None):
   SQLALCHEMY_DATABASE_URI = 'sqlite://'
else:
   SQLALCHEMY_DATABASE_URI = 'sqlite:///%s/log_data.sqlite3' % (os.path.dirname(__file__))
SQLALCHEMY_ECHO = False
# Generate a random secret key
SECRET_KEY = os.urandom(24)
# Disable debugging
DEBUG = False
