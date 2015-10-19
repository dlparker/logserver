import sqlite3
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_model_tables():
    db.create_all()
