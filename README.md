# PaperShare: Let thy Paper Be Summarized 📄➡️💬

**AI-powered tool (Flask, Python, Gemini) that analyzes arXiv abstracts via URL to instantly generate shareable summaries for LinkedIn, Twitter, and novice audiences. Simplifies research dissemination.**

<!-- Add a GIF/Screenshot here showing the app in action! -->
<!-- Example: ![PaperShare Demo](./docs/demo.gif) -->

## The Problem

Sharing academic research effectively across different platforms is crucial but time-consuming. Manually summarizing papers and tailoring content for platforms like LinkedIn, Twitter, or for a general audience requires significant effort.

## The Solution

PaperShare automates this process! By simply providing the URL to an arXiv abstract page, this tool leverages Google's Gemini Pro large language model to analyze the content and generate ready-to-use summaries and social media posts.

## ✨ Key Features

*   🔗 **Simple Input:** Accepts standard arXiv abstract URLs (e.g., `https://arxiv.org/abs/YYMM.NNNNN`).
*   🧠 **AI Analysis:** Uses Google Gemini Pro to understand the abstract's key findings, methodology, advantages, and potential applications.
*   📝 **Multi-Platform Outputs:** Generates tailored content for:
    *   **LinkedIn:** Engaging, professional posts highlighting key takeaways (priority given to LLM-generated draft).
    *   **Twitter:** Concise, multi-tweet threads summarizing the paper's essence.
    *   **Novice Summary:** Easy-to-understand explanations for a non-expert audience.
*   🌐 **Web Interface:** Clean and simple user interface built with Flask, HTML, CSS, and vanilla JavaScript.
*   🛡️ **Robust Fallback:** Includes intelligent template-based analysis and content generation if the AI model fails, is unavailable, or the API key isn't configured.
*   💾 **Database Caching:** Utilizes SQLite to store paper details and generated analyses, significantly speeding up requests for previously processed papers.

## 🛠️ Technology Stack

*   **Backend:** Python 3.x, Flask
*   **AI Model:** Google Gemini Pro (`google-generativeai` SDK)
*   **Web Scraping:** `requests`, `BeautifulSoup4`
*   **Database:** SQLite 3
*   **Frontend:** HTML5, CSS3, Vanilla JavaScript

## 🚀 Setup and Installation

Follow these steps to run PaperShare locally:

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/YOUR_USERNAME/papershare.git # Replace with your repo URL
    cd papershare
    ```

2.  **Create and Activate a Virtual Environment:**
    *(Recommended to avoid dependency conflicts)*
    ```bash
    # Windows
    python -m venv venv
    .\venv\Scripts\activate

    # macOS / Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *(If `requirements.txt` doesn't exist, create it with the content below or run `pip install Flask requests beautifulsoup4 google-generativeai`)*

4.  **Configure API Key:**
    *   Open the `app.py` file.
    *   Find the line `GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"`
    *   Replace `"YOUR_GEMINI_API_KEY"` with your actual Google AI Studio API key.
    *   **Security Note:** For production or shared repositories, it's highly recommended to use environment variables instead of hardcoding the key:
        ```python
        # Replace the line in app.py with:
        import os
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        # Then set the environment variable in your terminal before running:
        # Windows (cmd): set GEMINI_API_KEY=YOUR_ACTUAL_KEY
        # Windows (PowerShell): $env:GEMINI_API_KEY="YOUR_ACTUAL_KEY"
        # macOS / Linux: export GEMINI_API_KEY=YOUR_ACTUAL_KEY
        ```

5.  **Database Setup:**
    *   The application will automatically create the `research_papers.db` SQLite file on the first run using the schema defined in `app.py`.
    *   **Important:** If you pull changes to `app.py` that modify the database schema (like adding/removing columns in `init_db`), you **must delete the existing `research_papers.db` file** before running the app again to allow the new schema to be created.

6.  **Run the Flask Application:**
    ```bash
    python app.py
    ```


## 📝 Usage

1.  Navigate to the application URL in your browser.
2.  Find the abstract page URL for the arXiv paper you want to analyze (e.g., `https://arxiv.org/abs/2403.10235`).
3.  Paste the URL into the input field.
4.  Click the "Generate Content" button.
5.  Wait for the analysis (this involves web scraping and potentially an AI API call, so it might take a few seconds).
6.  The generated content for LinkedIn, Twitter, and Novice audiences will appear in separate tabs.
7.  Use the copy buttons to copy the generated text.

## `requirements.txt`

If the file doesn't exist, create `requirements.txt` in the root directory with this content:

```text
Flask>=2.0
requests>=2.25
beautifulsoup4>=4.9
google-generativeai>=0.4
