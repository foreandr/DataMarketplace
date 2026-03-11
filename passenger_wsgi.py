import os
import sys

# Add current directory to path so it can find app.py
sys.path.insert(0, os.path.dirname(__file__))

# Switch to the virtual environment interpreter
INTERP = os.path.join(os.getcwd(), "venv", "bin", "python")
if sys.executable != INTERP:
    os.execl(INTERP, INTERP, *sys.argv)

# Import the Flask instance 'app' as 'application' for Passenger
from app import app as application
