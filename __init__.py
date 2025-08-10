from flask import Flask

app = Flask(__name__)

# Import routes after creating the app object to avoid circular imports
from app import routes