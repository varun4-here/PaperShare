from flask import Flask, request, render_template_string
import requests
from bs4 import BeautifulSoup
import sqlite3
import os
import json
from datetime import datetime
import re

app = Flask(__name__)

# Configuration
DB_NAME = "research_papers.db"
HF_API_KEY = "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"  # Your Hugging Face token

# Database Setup with better error handling
def init_db():
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        # Enable foreign key support
        c.execute("PRAGMA foreign_keys = ON")
        
        c.execute('''CREATE TABLE IF NOT EXISTS papers
                     (id INTEGER PRIMARY KEY,
                     title TEXT NOT NULL,
                     authors TEXT,
                     abstract TEXT,
                     url TEXT UNIQUE NOT NULL,
                     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS analyses
                     (paper_id INTEGER PRIMARY KEY,
                     headline TEXT NOT NULL,
                     hook TEXT NOT NULL,
                     key_finding TEXT NOT NULL,
                     method TEXT NOT NULL,
                     technical_detail TEXT NOT NULL,
                     application TEXT NOT NULL,
                     prior_work TEXT,
                     limitation TEXT,
                     advantage TEXT NOT NULL,
                     stats TEXT,
                     personal_take TEXT NOT NULL,
                     open_question TEXT,
                     novice_summary TEXT,
                     FOREIGN KEY(paper_id) REFERENCES papers(id) ON DELETE CASCADE)''')
        
        conn.commit()
        return conn
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        raise

# Improved Data Extraction with better error handling
def crawl_arxiv_paper(url):
    try:
        if not re.match(r'^https?://arxiv\.org/abs/\d+\.\d+', url):
            raise ValueError("Invalid arXiv URL format")
            
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        title = soup.find('h1', class_='title mathjax')
        if not title:
            raise ValueError("Title not found in paper")
        title = title.get_text(strip=True).replace('Title:', '')
        
        authors = ', '.join([a.get_text(strip=True) for a in soup.select('.authors a')][:3])
        
        abstract = soup.find('blockquote', class_='abstract mathjax')
        if not abstract:
            raise ValueError("Abstract not found in paper")
        abstract = abstract.get_text(strip=True).replace('Abstract:', '')
        
        return {
            'title': title,
            'authors': authors,
            'abstract': abstract,
            'url': url
        }
    except Exception as e:
        print(f"Crawling error for {url}: {e}")
        return None

# Analysis using Hugging Face API
def analyze_with_ai(paper):
    if not HF_API_KEY:
        print("Hugging Face API key not configured")
        return generate_basic_analysis(paper)
    
    try:
        # Hugging Face Inference API endpoint for a suitable model
        API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2"
        headers = {
            "Authorization": f"Bearer {HF_API_KEY}",
            "Content-Type": "application/json"
        }
        
        prompt = f"""<s>[INST] As a passionate physics student, create a detailed LinkedIn post analysis of this paper:

Title: {paper['title']}
Abstract: {paper['abstract']}

Provide analysis in this exact JSON format:
{{
    "headline": "🚀 [Eye-catching claim]",
    "hook": "[Why this matters]",
    "key_finding": "[Main conclusion]",
    "method": "[Research approach]",
    "technical_detail": "[Key innovation]",
    "application": "[Practical use]",
    "prior_work": "[Previous research]",
    "limitation": "[What prior work couldn't do]",
    "advantage": "[This paper's improvement]",
    "stats": "[Statistical significance]",
    "personal_take": "[Your perspective]",
    "open_question": "[Remaining challenges]",
    "novice_summary": "[A 3-4 sentence explanation for someone with no background in the field]"
}}
Format your response as valid JSON only without any additional text or explanation. [/INST]</s>
"""

        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 1024,
                "temperature": 0.7,
                "return_full_text": False
            }
        }
        
        response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        
        response_data = response.json()
        
        # HF API returns a list of generated outputs
        if isinstance(response_data, list) and len(response_data) > 0:
            text_response = response_data[0].get('generated_text', '')
        else:
            # Handle other response formats
            text_response = response_data.get('generated_text', '')
        
        # Extract JSON from the response text
        try:
            # Try to find JSON object in the text
            json_match = re.search(r'(\{.*\})', text_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)
            else:
                # If no JSON object is found, try parsing the whole response
                return json.loads(text_response)
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON response from Hugging Face: {e}")
            print(f"Response text: {text_response}")
            return generate_basic_analysis(paper)
            
    except Exception as e:
        print(f"AI analysis failed: {e}")
        return generate_basic_analysis(paper)

# Fallback analysis generator
def generate_basic_analysis(paper):
    keywords = paper['title'].split()[:3]
    return {
        'headline': f"🚀 New Research on {' '.join(keywords)}",
        'hook': f"This paper explores important aspects of {' '.join(keywords)}",
        'key_finding': paper['abstract'][:100] + "...",
        'method': "Combines experimental and theoretical approaches",
        'technical_detail': "Introduces new methodology for " + keywords[0],
        'application': "Potential applications in " + keywords[-1] + " field",
        'prior_work': "Builds on previous research in this area",
        'limitation': "Had limited scope in certain conditions",
        'advantage': "Improves upon existing methods",
        'stats': "Shows statistically significant results",
        'personal_take': "This could influence future work in the field",
        'open_question': "How these findings generalize remains to be seen",
        'novice_summary': f"This research investigates {keywords[0]} in a new way. The findings could help us understand {keywords[-1]} better. This matters because it might lead to practical applications in everyday life."
    }

# LinkedIn post generator
def generate_linkedin_post(paper, analysis):
    defaults = {
        'headline': "🚀 Interesting Physics Research",
        'hook': "This paper presents fascinating findings",
        'key_finding': "significant results in the field",
        'method': "innovative methodology",
        'technical_detail': "novel approach",
        'application': "potential real-world applications",
        'prior_work': "previous research",
        'limitation': "certain limitations",
        'advantage': "important improvements",
        'stats': "statistically significant results",
        'personal_take': "exciting potential",
        'open_question': "important unanswered questions"
    }
    
    # Use analysis values or defaults
    analysis = {**defaults, **analysis}
    
    return f"""{analysis['headline']}

When I first read about this, I was intrigued because {analysis['hook']}.

The paper demonstrates {analysis['key_finding']} using {analysis['method']}. 
Key innovation: {analysis['technical_detail']}
Potential applications: {analysis['application']}

Compared to {analysis['prior_work']} which had {analysis['limitation']}, this work shows {analysis['advantage']}. 
{analysis['stats']}.

As a physics enthusiast, I find {analysis['personal_take']} particularly exciting.
Remaining questions: {analysis['open_question']}

Read the paper: {paper['url']}
What are your thoughts? Let's discuss! 👇"""

# Twitter post generator
def generate_twitter_post(paper, analysis):
    defaults = {
        'headline': "🚀 Physics Research Alert",
        'hook': "fascinating findings",
        'key_finding': "significant results",
        'application': "promising applications"
    }
    
    # Use analysis values or defaults
    analysis = {**defaults, **analysis}
    
    # Create a shorter version for Twitter
    headline = analysis['headline']
    if len(headline) > 50:
        headline = headline[:47] + "..."
    
    return f"""{headline}

{analysis['key_finding'][:80]}... 

Why it matters: {analysis['hook'][:80]}...

Potential impact: {analysis['application'][:80]}...

Paper: {paper['url']}
#Research #Physics #Science"""

# Novice summary generator
def generate_novice_summary(paper, analysis):
    defaults = {
        'novice_summary': f"This research looks at interesting aspects of {paper['title'].split()[0]}. While it's complex, the findings could eventually lead to practical uses in our daily lives. The researchers used new methods to solve problems that previous approaches couldn't handle."
    }
    
    # Use analysis values or defaults
    analysis = {**defaults, **analysis}
    
    return f"""# Simple Explanation of "{paper['title']}"

{analysis['novice_summary']}

## Why This Matters
In everyday terms, this research could one day help with {analysis['application'].lower() if analysis['application'].lower().startswith('potential') else 'potential ' + analysis['application'].lower()}.

## The Big Picture
{analysis['hook']}

## Main Takeaway
{analysis['key_finding']}

## How They Did It
The researchers approached this problem by using {analysis['method']}. 
What makes this special is that they {analysis['technical_detail'].lower() if analysis['technical_detail'][0].isupper() else analysis['technical_detail']}.

## What's Next?
There are still open questions like: {analysis['open_question']}

## For More Information
For more details: {paper['url']}

*This summary was created to help non-experts understand the significance of this research paper.*"""

# Web Interface with better error handling
@app.route('/', methods=['GET', 'POST'])
def home():
    try:
        conn = init_db()
        linkedin_post = None
        twitter_post = None
        novice_summary = None
        error = None
        
        if request.method == 'POST':
            url = request.form.get('url', '').strip()
            if not url:
                error = "Please enter a URL"
            elif not re.match(r'^https?://arxiv\.org/abs/\d+\.\d+', url):
                error = "Please enter a valid arXiv URL (e.g., https://arxiv.org/abs/1234.5678)"
            else:
                paper = crawl_arxiv_paper(url)
                if not paper:
                    error = "Failed to fetch paper details. Please check the URL."
                else:
                    try:
                        c = conn.cursor()
                        
                        # Store paper
                        c.execute('''INSERT OR IGNORE INTO papers 
                                    (title, authors, abstract, url) 
                                    VALUES (?, ?, ?, ?)''',
                                 (paper['title'], paper['authors'], paper['abstract'], paper['url']))
                        paper_id = c.lastrowid or c.execute('SELECT id FROM papers WHERE url = ?', (paper['url'],)).fetchone()[0]
                        conn.commit()
                        
                        # Get or create analysis
                        c.execute('''SELECT * FROM analyses WHERE paper_id = ?''', (paper_id,))
                        analysis_row = c.fetchone()
                        
                        if analysis_row:
                            analysis = dict(zip([
                                'paper_id', 'headline', 'hook', 'key_finding', 
                                'method', 'technical_detail', 'application',
                                'prior_work', 'limitation', 'advantage', 'stats',
                                'personal_take', 'open_question', 'novice_summary'
                            ], analysis_row))
                        else:
                            analysis = analyze_with_ai(paper)
                            c.execute('''INSERT INTO analyses VALUES 
                                        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                                     (paper_id, 
                                      analysis.get('headline', ''),
                                      analysis.get('hook', ''),
                                      analysis.get('key_finding', ''),
                                      analysis.get('method', ''),
                                      analysis.get('technical_detail', ''),
                                      analysis.get('application', ''),
                                      analysis.get('prior_work', ''),
                                      analysis.get('limitation', ''),
                                      analysis.get('advantage', ''),
                                      analysis.get('stats', ''),
                                      analysis.get('personal_take', ''),
                                      analysis.get('open_question', ''),
                                      analysis.get('novice_summary', '')))
                            conn.commit()
                        
                        linkedin_post = generate_linkedin_post(paper, analysis)
                        twitter_post = generate_twitter_post(paper, analysis)
                        novice_summary = generate_novice_summary(paper, analysis)
                        
                    except Exception as e:
                        conn.rollback()
                        error = f"Database error: {str(e)}"
        
        return render_template_string('''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Research Paper Sharing Tool</title>
                <style>
                    body { font-family: Arial, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; }
                    input[type="text"] { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 4px; }
                    button { background: #0077b5; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; margin-right: 10px; }
                    button:hover { background: #005582; }
                    pre { background: #f5f5f5; padding: 15px; border-radius: 4px; white-space: pre-wrap; }
                    .error { color: #d9534f; margin: 10px 0; }
                    .success { color: #5cb85c; margin-left: 10px; display: inline-block; }
                    .info { margin: 20px 0; padding: 10px; border-radius: 4px; }
                    .linkedin { background: #e7f3fe; }
                    .twitter { background: #e8f5fd; }
                    .novice { background: #f0f7ee; }
                    .tab { cursor: pointer; padding: 10px 20px; display: inline-block; border: 1px solid #ddd; border-radius: 4px 4px 0 0; }
                    .active-tab { background-color: #f5f5f5; border-bottom: none; }
                    h2 { margin-top: 10px; }
                    .tab-content { display: none; }
                    .active-content { display: block; }
                    .copy-container { margin-top: 10px; }
                </style>
            </head>
            <body>
                <h1>Research Paper Sharing Tool</h1>
                <form method="post">
                    <input type="text" name="url" placeholder="Enter arXiv paper URL (e.g., https://arxiv.org/abs/2403.10235)" 
                           value="{{ request.form.url if request.method == 'POST' else '' }}" required>
                    <button type="submit">Generate Content</button>
                </form>
                
                {% if error %}
                <div class="error">{{ error }}</div>
                {% endif %}
                
                {% if linkedin_post %}
                <div class="tabs">
                    <div class="tab active-tab" onclick="openTab(event, 'linkedin')">LinkedIn Post</div>
                    <div class="tab" onclick="openTab(event, 'twitter')">Twitter Post</div>
                    <div class="tab" onclick="openTab(event, 'novice')">Novice Summary</div>
                </div>
                
                <div id="linkedin" class="tab-content active-content info linkedin">
                    <h2>LinkedIn Post</h2>
                    <pre id="linkedinContent">{{ linkedin_post }}</pre>
                    <div class="copy-container">
                        <button onclick="copyToClipboard('linkedinContent', 'linkedinStatus')">Copy to Clipboard</button>
                        <span id="linkedinStatus" class="success"></span>
                    </div>
                </div>
                
                <div id="twitter" class="tab-content info twitter">
                    <h2>Twitter Post</h2>
                    <pre id="twitterContent">{{ twitter_post }}</pre>
                    <div class="copy-container">
                        <button onclick="copyToClipboard('twitterContent', 'twitterStatus')">Copy to Clipboard</button>
                        <span id="twitterStatus" class="success"></span>
                    </div>
                </div>
                
                <div id="novice" class="tab-content info novice">
                    <h2>Novice-Friendly Summary</h2>
                    <pre id="noviceContent">{{ novice_summary }}</pre>
                    <div class="copy-container">
                        <button onclick="copyToClipboard('noviceContent', 'noviceStatus')">Copy to Clipboard</button>
                        <span id="noviceStatus" class="success"></span>
                    </div>
                </div>
                {% endif %}
                
                <script>
                function copyToClipboard(elementId, statusId) {
                    const content = document.getElementById(elementId).textContent;
                    navigator.clipboard.writeText(content).then(() => {
                        document.getElementById(statusId).textContent = "Copied!";
                        setTimeout(() => {
                            document.getElementById(statusId).textContent = "";
                        }, 2000);
                    });
                }
                
                function openTab(evt, tabName) {
                    // Hide all tab content
                    var tabcontent = document.getElementsByClassName("tab-content");
                    for (var i = 0; i < tabcontent.length; i++) {
                        tabcontent[i].classList.remove("active-content");
                    }
                    
                    // Remove active class from all tabs
                    var tabs = document.getElementsByClassName("tab");
                    for (var i = 0; i < tabs.length; i++) {
                        tabs[i].classList.remove("active-tab");
                    }
                    
                    // Show the specific tab content
                    document.getElementById(tabName).classList.add("active-content");
                    
                    // Add active class to the button that opened the tab
                    evt.currentTarget.classList.add("active-tab");
                }
                </script>
            </body>
            </html>
        ''', linkedin_post=linkedin_post, twitter_post=twitter_post, novice_summary=novice_summary, error=error)
    
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}", 500
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    app.run(debug=True, port=5001)