# app/__init__.py
import os
from flask import Flask
from .config import Config

def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(Config)
    # ensure data dir exists
    os.makedirs(app.config.get("DATA_DIR", "./data"), exist_ok=True)

    # register routes blueprint (import here to avoid circular imports)
    from .routes import bp as main_bp
    app.register_blueprint(main_bp)

    return app
