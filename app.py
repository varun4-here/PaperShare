import os
import re
import io
import json
import logging
import requests
from flask import Flask, request, render_template, jsonify
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader
from google import genai
from google.genai import types

app = Flask(__name__)

# --- Configuration ---
GEMINI_API_KEY = "ENTER YOUR OWN KEY< NOT MINE MATE"
MODEL_ID = "gemini-3-flash-preview"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Initialize the New Client ---
client = genai.Client(api_key=GEMINI_API_KEY)

# --- PDF & ArXiv Crawler ---
def extract_pdf_text(pdf_url):
    try:
        response = requests.get(pdf_url, timeout=15)
        reader = PdfReader(io.BytesIO(response.content))
        text = ""
        for i in range(min(3, len(reader.pages))):
            text += reader.pages[i].extract_text()
        return text[:10000]
    except Exception as e:
        logger.warning(f"PDF Error: {e}")
        return ""

def crawl_arxiv(url):
    try:
        response = requests.get(url, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.find('h1', class_='title').text.replace('Title:', '').strip()
        abstract = soup.find('blockquote', class_='abstract').text.replace('Abstract:', '').strip()
        
        # --- NEW: Extract Authors ---
        authors = soup.find('div', class_='authors').text.replace('Authors:', '').strip()
        
        pdf_url = url.replace('/abs/', '/pdf/') + ".pdf"
        pdf_text = extract_pdf_text(pdf_url)
        
        return {
            'title': title, 
            'authors': authors, 
            'abstract': abstract, 
            'url': url, 
            'pdf_text': pdf_text
        }
    except Exception as e:
        logger.error(f"Crawl Error: {e}")
        return None

# --- AI Analysis ---
def analyze_paper(paper):
    # Modified prompt with student-creator persona and researcher attribution
    prompt = f"""
    CONTEXT: You are a tech-savvy student and digital content creator. You love translating complex research into engaging content for your peers and followers.
    
    TASK: Analyze this research paper and create social media content. You MUST mention the researchers/authors ({paper['authors']}) in the posts to give them proper credit.

    PAPER_TITLE: {paper['title']}
    AUTHORS: {paper['authors']}
    ABSTRACT: {paper['abstract']}
    TECHNICAL_CONTEXT: {paper['pdf_text'][:5000]}

    Return ONLY a JSON object with these exact keys:
    "headline": (Catchy with emoji, student-style),
    "linkedin_post": (4 paragraphs from a student's perspective: Why I'm reading this, the breakthrough by {paper['authors']}, how it works, and a question for the community),
    "twitter_thread": (A punchy 3-tweet summary. Tweet 1 must credit the researchers),
    "novice_analogy": (Explain the tech like an analogy to a household object),
    "key_takeaway": (The most important result in 1 sentence),
    "hashtags": (list of 5)
    """

    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type='application/json',
                safety_settings=[types.SafetySetting(category='HARM_CATEGORY_DANGEROUS_CONTENT', threshold='BLOCK_NONE')]
            )
        )
        return json.loads(response.text)
    except Exception as e:
        logger.error(f"AI Call Failed: {e}")
        return None

# --- Routes ---

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        return process_logic()
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    return process_logic()

def process_logic():
    data = request.get_json()
    url = data.get('url', '').strip()
    
    if not url or 'arxiv.org' not in url:
        return jsonify({'success': False, 'error': 'Please provide a valid arXiv URL'})

    paper_data = crawl_arxiv(url)
    if not paper_data:
        return jsonify({'success': False, 'error': 'Could not fetch paper details'})

    analysis = analyze_paper(paper_data)
    if not analysis:
        return jsonify({'success': False, 'error': 'AI Analysis failed.'})

    tags = " ".join([f"#{t.replace(' ', '')}" for t in analysis.get('hashtags', [])])
    
    return jsonify({
        'success': True,
        'data': {
            'paper_title': paper_data['title'],
            'authors': paper_data['authors'], # Included in raw data
            'linkedin': f"{analysis['linkedin_post']}\n\n{tags}",
            'twitter': f"{analysis['twitter_thread']}\n\nRead more: {url}",
            'novice': f"⭐ THE BIG IDEA:\n{analysis['key_takeaway']}\n\n🏠 ANALOGY:\n{analysis['novice_analogy']}"
        }
    })

if __name__ == '__main__':
    app.run(debug=True, port=5001)
