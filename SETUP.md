# PaperShare Setup Guide

Complete step-by-step guide to set up and run the PaperShare application.

## 📋 Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Internet connection (for accessing arXiv and Google AI API)

## 🚀 Quick Start

### 1. Install Dependencies

Navigate to the project directory and install required packages:

```bash
cd "c:\Users\ASUS\Desktop\Projects (Active)\PaperShare"
pip install -r requirements.txt
```

This will install:
- Flask (Web framework)
- requests & beautifulsoup4 (Web scraping)
- google-generativeai (AI analysis)
- PyPDF2 (PDF text extraction)
- python-dotenv (Environment variable management)

### 2. API Key Configuration

Your Google Gemini API key is already configured in the `.env` file. If you need to update it:

1. Open `.env` file
2. Update the line: `GEMINI_API_KEY=your_new_key_here`

**Need a new API key?** Get it from [Google AI Studio](https://makersuite.google.com/app/apikey)

### 3. Run the Application

Start the Flask server:

```bash
python app.py
```

You should see output like:
```
INFO - Database 'research_papers.db' initialized successfully.
INFO - Gemini AI model configured successfully.
 * Running on http://0.0.0.0:5001
```

### 4. Access the Application

Open your web browser and navigate to:
```
http://localhost:5001
```

## 📖 How to Use

1. **Find an arXiv paper**: Go to [arxiv.org](https://arxiv.org) and find a paper
2. **Copy the abstract URL**: Example: `https://arxiv.org/abs/2403.10235`
3. **Paste into PaperShare**: Enter the URL in the input field
4. **Generate Content**: Click "Generate Content" button
5. **View Results**: Browse the three tabs:
   - **LinkedIn**: Professional post with hashtags
   - **Twitter**: Multi-tweet thread
   - **Novice**: Easy-to-understand explanation

## 🔧 Troubleshooting

### "Failed to fetch or parse paper details"
- Verify the arXiv URL is correct (format: `https://arxiv.org/abs/XXXX.XXXXX`)
- Check your internet connection
- Ensure arXiv.org is accessible

### "AI analysis was not successful"
- Verify your API key in `.env` file
- Check API key validity at [Google AI Studio](https://makersuite.google.com/app/apikey)
- Review `app.log` file for detailed error messages

### PyPDF2 warnings
- If you see PyPDF2 warnings, the app will still work but won't extract PDF content
- Reinstall: `pip install --upgrade PyPDF2`

### Port already in use
- If port 5001 is busy, edit `app.py` (last line) to use a different port:
  ```python
  app.run(host='0.0.0.0', port=5002, debug=False)
  ```

## 📁 Project Structure

```
PaperShare/
├── app.py                  # Main Flask application
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (API key)
├── .env.example           # Template for .env file
├── .gitignore             # Git ignore rules
├── templates/
│   └── index.html         # Frontend HTML
├── Static/
│   ├── css/
│   │   └── style.css      # Styling
│   └── js/
│       └── script.js      # Frontend logic
├── research_papers.db     # SQLite database (auto-created)
└── app.log               # Application logs
```

## 🎯 Testing the Application

Test with this sample arXiv paper:
```
https://arxiv.org/abs/2403.10235
```

Expected behavior:
1. Loading indicator appears
2. Paper is fetched and analyzed (10-30 seconds)
3. Three content tabs populate with generated summaries
4. Results cached in database for faster future access

## 🔒 Security Notes

- **Never commit `.env` file** to version control (already in `.gitignore`)
- If sharing code, use `.env.example` as template
- Keep your API key confidential

## 💡 Tips

- **Database caching**: Previously analyzed papers load instantly from the database
- **PDF extraction**: First 4 and last 3 pages are extracted for deeper analysis
- **Offline mode**: App works without API key but won't generate AI content
- **Logs**: Check `app.log` for debugging information

## 🆘 Need Help?

1. Check the `app.log` file for detailed error messages
2. Ensure all dependencies are installed: `pip list`
3. Verify Python version: `python --version` (should be 3.8+)
4. Test API key separately at Google AI Studio

## 📝 Example URLs to Try

- Attention Is All You Need: `https://arxiv.org/abs/1706.03762`
- GPT-3: `https://arxiv.org/abs/2005.14165`
- ResNet: `https://arxiv.org/abs/1512.03385`
- BERT: `https://arxiv.org/abs/1810.04805`

---

**Ready to go!** Start the app with `python app.py` and begin generating research summaries! 🚀
