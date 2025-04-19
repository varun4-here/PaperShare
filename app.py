# --- START OF FILE papershare/app.py ---

from flask import Flask, request, render_template, jsonify
import requests
from bs4 import BeautifulSoup
import sqlite3
import os
import json
import random # For template variation
from datetime import datetime
import re
import logging
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# --- Configuration ---
# Consider using environment variables for production: os.getenv("GEMINI_API_KEY")
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY" # Set your Gemini API key here
# --------------------

DB_NAME = "research_papers.db"

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# --- Gemini Model Configuration ---
try:
    if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY":
        logger.warning("Gemini API Key not configured. AI analysis will be limited.")
        gemini_model = None
    else:
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel('gemini-1.5-flash-latest')
        logger.info("Gemini AI model configured successfully.")
except Exception as e:
    logger.error(f"Failed to configure Gemini AI: {e}", exc_info=True)
    gemini_model = None
# ---------------------------------


# --- Database Functions (Unchanged) ---
def init_db():
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
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
                     linkedin_draft TEXT,  -- Added field for LLM draft
                     keywords TEXT,      -- Added field for keywords/hashtags
                     FOREIGN KEY(paper_id) REFERENCES papers(id) ON DELETE CASCADE)''') # Added new columns
        conn.commit()
        logger.info(f"Database '{DB_NAME}' initialized successfully.")
        return conn
    except sqlite3.Error as e:
        logger.error(f"Database initialization error: {e}")
        raise

# --- Web Scraping Function (Unchanged) ---
def crawl_arxiv_paper(url):
    try:
        if not re.match(r'^https?://arxiv\.org/abs/\d+\.\d+(v\d+)?$', url):
             raise ValueError("Invalid arXiv URL format passed to crawler")
        logger.info(f"Crawling arXiv paper: {url}")
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        title_tag = soup.find('h1', class_='title mathjax')
        meta_title = soup.find('meta', attrs={'name': 'citation_title'})
        if title_tag: title = title_tag.get_text(strip=True).replace('Title:', '').strip()
        elif meta_title and meta_title['content']: title = meta_title['content'].strip()
        else: raise ValueError("Title tag or meta tag not found.")
        if not title: raise ValueError("Extracted title is empty.")

        authors_tags = soup.select('.authors a')
        meta_authors = soup.find_all('meta', attrs={'name': 'citation_author'})
        if authors_tags: authors = ', '.join([a.get_text(strip=True) for a in authors_tags][:5])
        elif meta_authors: authors = ', '.join([meta['content'].strip() for meta in meta_authors][:5])
        else: authors = "Authors not found"

        abstract_tag = soup.find('blockquote', class_='abstract mathjax')
        meta_abstract = soup.find('meta', attrs={'name': 'citation_abstract'})
        if abstract_tag: abstract = abstract_tag.get_text(strip=True).replace('Abstract:', '').strip()
        elif meta_abstract and meta_abstract['content']: abstract = meta_abstract['content'].strip()
        else: raise ValueError("Abstract tag or meta tag not found.")
        if not abstract: raise ValueError("Extracted abstract is empty.")

        logger.info(f"Successfully extracted paper: {title[:50]}...")
        return {'title': title, 'authors': authors, 'abstract': abstract, 'url': url}
    except requests.exceptions.RequestException as e: logger.error(f"Network error crawling {url}: {e}"); return None
    except ValueError as e: logger.error(f"Content extraction error for {url}: {e}"); return None
    except Exception as e: logger.error(f"Unexpected crawling error for {url}: {e}", exc_info=True); return None


# --- *** UPDATED Gemini-Powered Analysis Function *** ---
def analyze_with_ai(paper):
    """
    Analyzes the paper using Gemini, focusing on generating a good LinkedIn draft.
    Returns a dictionary with the analysis or None if it fails.
    """
    if not gemini_model:
        logger.warning("Gemini model not available. Cannot perform AI analysis.")
        return None

    logger.info(f"Analyzing paper with Gemini: {paper['title'][:50]}...")

    # --- UPDATED Gemini Prompt ---
    # Now explicitly asks for a LinkedIn draft and keywords, alongside structured data.
    prompt = f"""Act as an expert academic researcher and skilled science communicator creating content about a research paper for LinkedIn.
Analyze the provided paper title and abstract.

**Paper Title:** {paper['title']}
**Paper Abstract:** {paper['abstract']}

**Your Task:**
Generate a JSON object containing the following keys. Base your answers *only* on the provided title and abstract. Do not add external information.

1.  `headline`: A very short, engaging headline suitable for social media, starting with an emoji.
2.  `key_finding`: The single most important conclusion or result. Be specific and concise.
3.  `method_summary`: A brief description of the core method or approach used.
4.  `advantage_summary`: A brief summary of the key advantage or improvement claimed, if stated.
5.  `application_summary`: A brief mention of potential applications.
6.  `keywords`: A list of 3-5 relevant technical keywords or concepts from the text, suitable for hashtags (e.g., ["Machine Learning", "Computer Vision", "NLP"]).
7.  `linkedin_draft`: **Write an engaging LinkedIn post draft (around 3-5 paragraphs).**
    *   Start with the `headline`.
    *   Include a strong hook explaining the paper's importance.
    *   Clearly state the `key_finding`.
    *   Briefly mention the `method_summary`.
    *   Highlight the `advantage_summary` and `application_summary`.
    *   Add a short concluding thought or insightful question.
    *   **Crucially, make it sound natural and engaging, not just a list of facts.**
    *   Use paragraphs (separated by double newlines `\\n\\n`).
    *   You can use bullet points (e.g., ▪️) for clarity if appropriate within the draft.
    *   **Do not include hashtags or the paper URL within this draft itself.**

**Output Format:**
Return **ONLY** the valid JSON object, starting with `{{` and ending with `}}`. Ensure all string values are properly escaped. Do not include ```json markdown.

Example JSON Structure:
{{
  "headline": "...",
  "key_finding": "...",
  "method_summary": "...",
  "advantage_summary": "...",
  "application_summary": "...",
  "keywords": ["Keyword1", "Keyword2", "Keyword3"],
  "linkedin_draft": "POST_HEADLINE\\n\\nHOOK_SENTENCE...\\n\\nKEY_FINDING_DETAILS...\\n\\nMETHOD_MENTION...\\n\\nIMPLICATIONS...\\n\\nCONCLUDING_THOUGHT/QUESTION..."
}}
"""

    try:
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        }
        generation_config = genai.types.GenerationConfig(temperature=0.6) # Slightly more creative temp

        logger.debug("Sending request to Gemini API...")
        response = gemini_model.generate_content(
            prompt,
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        logger.debug(f"Gemini API response received. Finish reason: {response.candidates[0].finish_reason if response.candidates else 'N/A'}")

        if not response.candidates or response.candidates[0].finish_reason != genai.types.FinishReason.STOP:
             block_reason = response.prompt_feedback.block_reason if response.prompt_feedback else 'Unknown'
             safety_ratings = response.prompt_feedback.safety_ratings if response.prompt_feedback else []
             logger.error(f"Gemini response finished unexpectedly or blocked. Reason: {block_reason}. Ratings: {safety_ratings}")
             return None

        generated_text = response.text.strip()
        logger.debug(f"Raw Gemini text response: {generated_text[:200]}...")

        try:
            json_match = re.search(r'\{[\s\S]*\}', generated_text)
            if json_match:
                json_str = json_match.group(0)
                analysis = json.loads(json_str)
                logger.info("Successfully parsed JSON from Gemini response.")
                # Validate essential keys from the new structure
                if isinstance(analysis, dict) and all(k in analysis for k in ['headline', 'key_finding', 'linkedin_draft', 'keywords']):
                    # --- Supplement with template fallback for non-core fields ---
                    # This ensures we still have *some* content for other post types even if Gemini focused on LinkedIn
                    template_analysis = analyze_with_template(paper) # Get defaults
                    full_analysis = {}
                    # Prioritize Gemini output for shared keys
                    full_analysis['headline'] = analysis.get('headline') or template_analysis.get('headline')
                    full_analysis['hook'] = analysis.get('hook') or template_analysis.get('hook') # Hook might not be a direct key anymore
                    full_analysis['key_finding'] = analysis.get('key_finding') or template_analysis.get('key_finding')
                    full_analysis['method'] = analysis.get('method_summary') or template_analysis.get('method')
                    full_analysis['technical_detail'] = analysis.get('technical_detail') or template_analysis.get('technical_detail') # Maybe Gemini provides this?
                    full_analysis['application'] = analysis.get('application_summary') or template_analysis.get('application')
                    full_analysis['advantage'] = analysis.get('advantage_summary') or template_analysis.get('advantage')
                    full_analysis['novice_summary'] = analysis.get('novice_summary') or template_analysis.get('novice_summary') # Maybe add this to prompt?

                    # Add fields Gemini might not generate but template has
                    full_analysis['prior_work'] = template_analysis.get('prior_work')
                    full_analysis['limitation'] = template_analysis.get('limitation')
                    full_analysis['stats'] = template_analysis.get('stats')
                    full_analysis['personal_take'] = template_analysis.get('personal_take')
                    full_analysis['open_question'] = template_analysis.get('open_question')

                    # Add the specific Gemini fields
                    full_analysis['linkedin_draft'] = analysis.get('linkedin_draft', '') # The main generated draft
                    full_analysis['keywords'] = analysis.get('keywords', []) # Keywords for hashtags

                    return full_analysis
                else:
                    logger.error("Parsed JSON from Gemini missing essential keys (headline, key_finding, linkedin_draft, keywords).")
                    return None
            else: logger.error("No JSON object found in Gemini response."); return None
        except json.JSONDecodeError as json_e:
            logger.error(f"Failed to decode JSON from Gemini response: {json_e}")
            logger.error(f"Problematic text (snippet): {generated_text[:500]}"); return None
    except Exception as e: logger.error(f"Error during Gemini API call/processing: {e}", exc_info=True); return None

# --- Template-Based Fallback Analysis (Simplified) ---
def analyze_with_template(paper):
    """Generate a minimal fallback structured analysis."""
    logger.warning(f"Generating minimal template-based analysis for: {paper.get('title', 'N/A')[:50]}...")
    title = paper.get('title', '')
    abstract = paper.get('abstract', '')
    title_words = title.split()
    topic = ' '.join(title_words[:min(5, len(title_words))]) if title_words else "this research"
    sentences = re.split(r'(?<=[.!?])\s+', abstract)
    first_sentence = sentences[0] if sentences else abstract[:150]
    key_finding = (first_sentence[:147] + '...') if len(first_sentence) > 150 else first_sentence

    # Extract simple keywords from title
    keywords_raw = [w for w in title_words if len(w) > 3 and w.lower() not in ['the', 'and', 'for', 'with', 'from', 'paper', 'study']]
    keywords = list(set(keywords_raw[:5])) # Unique, first 5 relevant words

    return {
        'headline': f"🔬 Research Snapshot: {topic}",
        'hook': f"This paper investigates key aspects of {topic}.",
        'key_finding': key_finding or "Main results presented.",
        'method': "Methodology detailed within.",
        'technical_detail': "Specific techniques used.",
        'application': f"Potential applications in {topic}.",
        'prior_work': "Builds on prior work.",
        'limitation': "Scope and limitations discussed.",
        'advantage': "Offers potential improvements.",
        'stats': "Results presented in paper.",
        'personal_take': "An interesting contribution.",
        'open_question': "Further research suggested.",
        'novice_summary': f"Research on {topic}, using specific methods to find answers.",
        'linkedin_draft': "", # No draft generated by template
        'keywords': keywords      # Basic keywords from title
    }


# --- *** UPDATED LinkedIn Post Generation *** ---
def generate_linkedin_post(paper, analysis):
    """
    Generates a LinkedIn post, prioritizing LLM draft if available and good.
    Otherwise, assembles a post using structured data and improved templates.
    """
    logger.debug(f"Generating LinkedIn post for: {paper.get('title', 'N/A')[:50]}...")
    paper_url = paper.get('url', '')
    llm_draft = analysis.get('linkedin_draft', '').strip()

    # --- Hashtag Generation ---
    hashtags = ["#Research", "#Science", "#Innovation"] # Base hashtags
    ai_keywords = analysis.get('keywords', [])
    # Clean keywords and format as hashtags
    if isinstance(ai_keywords, list):
        for kw in ai_keywords:
            if isinstance(kw, str) and kw.strip():
                 # Basic cleaning: remove punctuation, ensure CamelCase or single word
                 tag = re.sub(r'[^\w\s-]', '', kw).strip()
                 if ' ' in tag: # CamelCase for multi-word
                      tag = ''.join(word.capitalize() for word in tag.split())
                 if len(tag) > 2: # Avoid very short tags
                     hashtags.append(f"#{tag}")
    # Ensure uniqueness and limit count
    hashtags = list(dict.fromkeys(hashtags))[:7] # Keep up to 7 unique hashtags
    hashtag_string = " ".join(hashtags)
    # ------------------------

    # --- Strategy 1: Use LLM Draft if good ---
    # Check if draft exists and has reasonable length (e.g., > 100 chars) and structure (e.g., newlines)
    if llm_draft and len(llm_draft) > 100 and '\n\n' in llm_draft:
        logger.info("Using LLM-generated LinkedIn draft.")
        # Append URL and hashtags to the LLM draft
        full_post = f"{llm_draft}\n\n🔗 Read the full paper: {paper_url}\n\n{hashtag_string}"
        return full_post.strip()

    # --- Strategy 2: Fallback to assembling from parts using templates ---
    logger.warning("LLM draft not usable, assembling LinkedIn post from structured data.")
    # Ensure we have values, falling back to generic placeholders if needed
    defaults = {
        'headline': f"🔬 Research Insights: {paper.get('title','')[0:30]}...",
        'hook': "An interesting new study.",
        'key_finding': "Presents significant findings.",
        'method': "Utilizes a specific methodology.",
        'advantage': "Offers potential benefits.",
        'application': "Could have practical applications.",
        'personal_take': "Worth looking into for those in the field.",
        'open_question': "What are your thoughts on this approach?",
         # Add keys that might be missing from a failed/partial AI analysis
        'technical_detail': analysis.get('technical_detail', 'Specific techniques detailed within.'),
        'prior_work': analysis.get('prior_work', 'Builds on prior work.'),
        'limitation': analysis.get('limitation', 'Limitations may apply.')
    }
    analysis_final = {k: analysis.get(k) or defaults.get(k) for k in defaults.keys()}

    # More varied and engaging templates
    templates = [
        f"""{analysis_final['headline']}

Just came across this paper and found the findings quite interesting: "{paper.get('title', 'Paper Title')}"

📌 **What's the core idea?** {analysis_final['hook']}

🔑 **Key Takeaway:** {analysis_final['key_finding']}

🔬 **How they did it:** The research employed {analysis_final['method']}. A notable aspect is {analysis_final.get('technical_detail','the specific technique used')}.

✨ **Why it matters:** This work suggests {analysis_final['advantage']} and could be applied to {analysis_final['application']}.

🤔 **My perspective:** {analysis_final['personal_take']} {analysis_final['open_question']}

🔗 Dive deeper: {paper_url}

{hashtag_string}""",

        f"""{analysis_final['headline']} | Exploring advances in {analysis.get('field_simple', 'research')}

This paper caught my eye: "{paper.get('title', 'Paper Title')}"

🔹 **The Gist:** {analysis_final['hook']}
🔹 **Main Result:** {analysis_final['key_finding']}
🔹 **Approach:** Leverages {analysis_final['method']}.

🚀 **Potential Impact:** This could lead to improvements in {analysis_final['application']}, potentially offering {analysis_final['advantage']}. It builds upon {analysis_final.get('prior_work', 'existing studies')}.

Always interesting to see how the field evolves! What limitations or extensions come to mind for you? ({analysis_final.get('limitation','Limitations discussed in paper')})

Full text: {paper_url}

{hashtag_string}""",

        f"""{analysis_final['headline']}

Sharing thoughts on a recent read: "{paper.get('title', 'Paper Title')}"

Essentially, the paper {analysis_final['hook']} The authors found that {analysis_final['key_finding']} by using {analysis_final['method']}.

What stands out is {analysis_final['advantage']}, which might be useful for {analysis_final['application']}.

{analysis_final['personal_take']}

Check out the details: {paper_url}

{hashtag_string}"""
    ]

    # Choose a random template for variety
    chosen_template = random.choice(templates)
    return chosen_template.strip()


# --- Other Post Generation Functions (Mostly Unchanged, Use final analysis dict) ---
def generate_twitter_post(paper, analysis):
    logger.debug(f"Generating Twitter post for: {paper.get('title', 'N/A')[:50]}...")
    defaults = analyze_with_template(paper)
    analysis_final = {k: analysis.get(k) or defaults.get(k, '') for k in defaults.keys()}
    keywords = analysis.get('keywords', [])
    hashtags = ["#Research"]
    if isinstance(keywords, list):
         for kw in keywords[:3]: # Take first 3 keywords for Twitter
              if isinstance(kw, str) and kw.strip():
                   tag = re.sub(r'[^\w\s-]', '', kw).strip()
                   if ' ' in tag: tag = ''.join(word.capitalize() for word in tag.split())
                   if len(tag) > 2: hashtags.append(f"#{tag}")
    hashtag_string = " ".join(list(dict.fromkeys(hashtags))[:4]) # Max 4 unique tags

    def truncate(text, length):
        text = str(text)
        if len(text) <= length: return text
        return text[:length-3] + "..."

    tweet1 = f"""{analysis_final['headline']} (1/3)
📜: "{truncate(paper.get('title', 'Paper Title'), 60)}"
🔑: {truncate(analysis_final['key_finding'], 120)}
{hashtag_string}"""
    tweet2 = f"""(2/3) How:
🔧 Method: {truncate(analysis_final['method'], 90)}
💡 Advantage: {truncate(analysis_final['advantage'], 90)}"""
    tweet3 = f"""(3/3) Impact:
🎯 Apps: {truncate(analysis_final['application'], 80)}
🤔 My Take: {truncate(analysis_final['personal_take'], 70)}
🔗: {paper.get('url', '')}"""
    return f"{tweet1.strip()}\n\n{tweet2.strip()}\n\n{tweet3.strip()}"

def generate_novice_summary(paper, analysis):
    logger.debug(f"Generating Novice summary for: {paper.get('title', 'N/A')[:50]}...")
    defaults = analyze_with_template(paper)
    analysis_final = {k: analysis.get(k) or defaults.get(k, '') for k in defaults.keys()}

    return f"""**Easy Explanation: "{paper.get('title', 'Paper Title')}"** 🧠➡️💡

**What's it about?** 🤔
{analysis_final.get('novice_summary', 'This research explores an interesting topic.')}
Basically: {analysis_final.get('hook','The goal was to understand something better.')}

**What did they find?** 🎯
The main discovery: {analysis_final.get('key_finding','They found some key results.')}

**How did they do it?** 🛠️
They used a method involving {analysis_final.get('method','specific techniques')}. The special part was {analysis_final.get('technical_detail','how they approached the problem')}.

**Why should I care?** ✨
This research is cool because {analysis_final.get('advantage','it might improve things')}. It could one day help with {analysis_final.get('application','real-world uses')}.

**What's next / Limits?** ❓
{analysis_final.get('open_question') or analysis_final.get('limitation','There are still things to explore.')}

**Want the details?** 🤓
Read the full paper here: {paper.get('url', '')}""".strip()


# --- Flask Route (Updated DB Interaction) ---
@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'GET':
        return render_template('index.html')

    if request.method == 'POST':
        conn = None
        try:
            conn = init_db()
            data = request.get_json()
            if not data or 'url' not in data: return jsonify({'success': False, 'error': "Invalid request data."}), 400
            url = data.get('url', '').strip()

            # --- Input Validation ---
            if not url: return jsonify({'success': False, 'error': "Please enter a URL"}), 400
            valid_arxiv_pattern = r'^https?://arxiv\.org/abs/\d+\.\d+(v\d+)?$'
            if not re.match(valid_arxiv_pattern, url):
                if '/pdf/' in url and url.endswith('.pdf'):
                     url = url.replace('/pdf/', '/abs/').replace('.pdf', '')
                     logger.info(f"Corrected URL from PDF to ABS: {url}")
                     if not re.match(valid_arxiv_pattern, url): return jsonify({'success': False, 'error': "Invalid arXiv URL (tried PDF fix). Use abstract URL."}), 400
                else: return jsonify({'success': False, 'error': "Invalid arXiv URL format. Use abstract URL."}), 400

            # --- Crawl Paper ---
            paper = crawl_arxiv_paper(url)
            if not paper: return jsonify({'success': False, 'error': "Failed to fetch or parse paper details. Check URL/arXiv status."}), 404

            c = conn.cursor()

            # --- DB Interaction: Get Paper ID ---
            paper_id = None
            try:
                c.execute('SELECT id FROM papers WHERE url = ?', (paper['url'],))
                paper_id_tuple = c.fetchone()
                if paper_id_tuple: paper_id = paper_id_tuple[0]; logger.info(f"Paper found in DB with ID: {paper_id}")
                else:
                    c.execute('INSERT INTO papers (title, authors, abstract, url) VALUES (?, ?, ?, ?)',
                             (paper['title'], paper['authors'], paper['abstract'], paper['url']))
                    paper_id = c.lastrowid
                    conn.commit(); logger.info(f"New paper inserted with ID: {paper_id}")
                if not paper_id: raise sqlite3.Error("Failed to get or create paper ID.")
            except sqlite3.Error as db_e:
                 conn.rollback(); logger.error(f"DB error handling paper entry: {db_e}"); return jsonify({'success': False, 'error': f"DB error: {str(db_e)}"}), 500

            # --- DB Interaction: Get or Create Analysis (Updated Keys) ---
            analysis = None
            # Updated list of keys to SELECT and INSERT
            analysis_keys = ['headline', 'hook', 'key_finding', 'method', 'technical_detail', 'application',
                             'prior_work', 'limitation', 'advantage', 'stats', 'personal_take', 'open_question',
                             'novice_summary', 'linkedin_draft', 'keywords']
            select_keys_str = ", ".join(analysis_keys)
            c.execute(f'SELECT {select_keys_str} FROM analyses WHERE paper_id = ?', (paper_id,))
            analysis_row = c.fetchone()

            if analysis_row:
                 analysis = dict(zip(analysis_keys, analysis_row))
                 # Ensure keywords are loaded as list if stored as JSON string
                 if isinstance(analysis.get('keywords'), str):
                     try: analysis['keywords'] = json.loads(analysis['keywords'])
                     except json.JSONDecodeError: analysis['keywords'] = []
                 logger.info(f"Analysis found in DB for paper ID {paper_id}")
            else:
                 logger.info(f"No analysis found for paper ID {paper_id}, generating...")
                 analysis = analyze_with_ai(paper) # Attempt AI analysis

                 if analysis is None: # If AI failed (returned None)
                      logger.warning("AI analysis failed, falling back to template.")
                      analysis = analyze_with_template(paper) # Use template as fallback

                 try:
                      # Prepare values for insertion, converting list (keywords) to JSON string for DB
                      insert_values = [paper_id]
                      for key in analysis_keys:
                          value = analysis.get(key, '')
                          if key == 'keywords' and isinstance(value, list):
                              insert_values.append(json.dumps(value)) # Store keywords as JSON string
                          else:
                              insert_values.append(str(value)) # Ensure other values are strings

                      placeholders = ",".join(["?"] * (len(analysis_keys) + 1))
                      c.execute(f'''INSERT INTO analyses
                                   (paper_id, {select_keys_str})
                                   VALUES ({placeholders})''', insert_values)
                      conn.commit()
                      logger.info(f"Successfully inserted new analysis for paper ID {paper_id}")
                 except sqlite3.Error as db_insert_e:
                      conn.rollback()
                      logger.error(f"DB error inserting analysis for {paper_id}: {db_insert_e}")

            # --- Generate Posts ---
            # Pass the potentially richer analysis dict to generation functions
            linkedin_post = generate_linkedin_post(paper, analysis)
            twitter_post = generate_twitter_post(paper, analysis)
            novice_summary = generate_novice_summary(paper, analysis)

            # --- Return Success Response ---
            return jsonify({
                'success': True,
                'data': { 'linkedin': linkedin_post, 'twitter': twitter_post, 'novice': novice_summary, 'paper_title': paper.get('title', 'N/A') }
            })

        # --- Error Handling (Unchanged) ---
        except requests.exceptions.RequestException as e: logger.error(f"Network error: {e}"); return jsonify({'success': False, 'error': f"Network error: {e}"}), 503
        except ValueError as e: logger.error(f"Data validation error: {e}"); return jsonify({'success': False, 'error': f"Invalid input or data: {e}"}), 400
        except sqlite3.Error as e:
            if conn: conn.rollback(); logger.error(f"DB error: {str(e)}"); return jsonify({'success': False, 'error': f"Database error: {str(e)}"}), 500
        except Exception as e:
            if conn: conn.rollback(); logger.error(f"Unexpected error: {str(e)}", exc_info=True); return jsonify({'success': False, 'error': "An unexpected server error occurred."}), 500
        finally:
            if conn: conn.close(); logger.debug("DB connection closed.")


if __name__ == '__main__':
    try:
        init_db() # Initialize DB on startup
    except Exception as e:
        print(f"CRITICAL: Failed to initialize database on startup: {e}")
    app.run(host='0.0.0.0', port=5001, debug=False) # Use debug=False for production
# --- END OF FILE papershare/app.py ---