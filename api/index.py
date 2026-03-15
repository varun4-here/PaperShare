from flask import Flask
from vercel_wsgi import handle_request

app = Flask(__name__)

@app.route("/")
def home():
    return "PaperShare running on Vercel"

def handler(request):
    return handle_request(app, request)