from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import psycopg
import os
from app.routes import main_blueprint


db = SQLAlchemy()

# Load environment variables from .env
load_dotenv()

def create_app():
    app = Flask(__name__)

    load_dotenv()
    # Database configuration
    db_user = os.getenv('db_user')
    db_password = os.getenv('db_password')
    db_host = os.getenv('db_host')
    db_port = os.getenv('db_port', 5432)  # Default to 5432 if not set
    db_name = os.getenv('db_name')
    app.config["SQLALCHEMY_DATABASE_URI"] = f'postgresql+psycopg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Initialize the database
    db.init_app(app)

    # Register blueprints

    app.register_blueprint(main_blueprint)

    return app
