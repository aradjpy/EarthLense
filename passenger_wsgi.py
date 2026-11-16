"""cPanel/Passenger WSGI bridge for the EarthLense FastAPI app.

Requires: pip install -r requirements-cpanel.txt
In cPanel use startup file passenger_wsgi.py and entrypoint application.
"""
from a2wsgi import ASGIMiddleware
from app.main import app

application = ASGIMiddleware(app)
