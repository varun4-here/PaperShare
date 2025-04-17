// START OF FILE papershare/static/js/script.js
document.addEventListener('DOMContentLoaded', () => {
    // --- Global Elements ---
    const body = document.body;
    const themeToggle = document.getElementById('theme-toggle');
    const themeIcon = document.getElementById('theme-icon');
    const themeNotification = document.getElementById('theme-notification');
    const dateElement = document.getElementById('current-date');
    const footerYear = document.getElementById('footer-year');
    const paperForm = document.getElementById('paper-form');
    const paperUrlInput = document.getElementById('paper-url');
    const loadingIndicator = document.getElementById('loading-indicator');
    const errorMessage = document.getElementById('error-message');
    const errorText = document.getElementById('error-text');
    const outputContainer = document.getElementById('output-container');
    const historyList = document.getElementById('history-list');
    const historyPlaceholder = document.getElementById('history-placeholder');
    const contentMap = {
        linkedin: document.getElementById('linkedin-content'),
        twitter: document.getElementById('twitter-content'),
        novice: document.getElementById('novice-content'),
    };
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    const copyButtons = document.querySelectorAll('.copy-to-clipboard-btn');

    // --- Initial Setup ---
    function init() {
        // Set Theme
        const savedTheme = localStorage.getItem('theme') || 'light';
        setTheme(savedTheme, false); // No notification on load

        // Set Date
        const now = new Date();
        const dateOptions = { year: 'numeric', month: 'long', day: 'numeric' };
        if(dateElement) dateElement.textContent = now.toLocaleDateString('en-US', dateOptions);
        if(footerYear) footerYear.textContent = now.getFullYear();

        // Load History (Optional - implement localStorage if needed)
        updateHistoryDisplay();

        // Auto-focus input field
        if (paperUrlInput) { // Check if element exists before focusing
             paperUrlInput.focus();
        }

        attachEventListeners();
    }

    // --- Theme Handling ---
    function setTheme(theme, notify = true) {
        body.classList.remove('light-theme', 'dark-theme');
        body.classList.add(`${theme}-theme`);
        localStorage.setItem('theme', theme);
        const isDark = theme === 'dark';
        if(themeIcon) { // Check if element exists
            themeIcon.classList.replace(isDark ? 'ph-moon' : 'ph-sun', isDark ? 'ph-sun' : 'ph-moon');
        }
        if(themeToggle) { // Check if element exists
            themeToggle.setAttribute('aria-label', `Switch to ${isDark ? 'light' : 'dark'} theme`);
        }


        if (notify && themeNotification) { // Check if element exists
            themeNotification.textContent = `Switched to ${isDark ? 'Dark' : 'Light'} Theme`;
            themeNotification.classList.add('show');
            setTimeout(() => themeNotification.classList.remove('show'), 2000);
        }
    }

    // --- Event Listeners ---
    function attachEventListeners() {
        if (themeToggle) {
             themeToggle.addEventListener('click', () => {
                const newTheme = body.classList.contains('dark-theme') ? 'light' : 'dark';
                setTheme(newTheme);
            });
        }

        if (paperForm) {
            paperForm.addEventListener('submit', handleFormSubmit);
        }


        tabButtons.forEach(button => {
            button.addEventListener('click', handleTabSwitch);
        });

        copyButtons.forEach(button => {
            button.addEventListener('click', handleCopy);
        });
    }

    // --- Form Submission ---
    async function handleFormSubmit(event) {
        event.preventDefault();
        // Ensure elements exist before accessing value
        if (!paperUrlInput) return;
        const url = paperUrlInput.value.trim();

        if (!isValidArxivUrl(url)) { // Use corrected validation
            showError("Please enter a valid arXiv Abstract URL (e.g., https://arxiv.org/abs/1234.5678).");
            return;
        }

        setLoadingState(true);
        hideError();
        hideOutput();

        try {
            const response = await fetch('/', { // Fetch from root path
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: url }),
            });

            const result = await response.json();

            if (!response.ok || !result.success) {
                throw new Error(result.error || `Server error: ${response.status}`);
            }

            displayResults(result.data);
            addToHistory(result.data.paper_title || 'Untitled Paper', url); // Add to history on success

        } catch (error) {
            console.error("Submission error:", error);
            showError(error.message || "An error occurred. Please try again.");
        } finally {
            setLoadingState(false);
        }
    }

    // --- UI Update Functions ---
    function setLoadingState(isLoading) {
         const submitButton = paperForm ? paperForm.querySelector('button[type="submit"]') : null;
        if (isLoading) {
            if(loadingIndicator) loadingIndicator.classList.add('active');
            if(paperUrlInput) paperUrlInput.disabled = true;
            if(submitButton) submitButton.disabled = true;

        } else {
            if(loadingIndicator) loadingIndicator.classList.remove('active');
            if(paperUrlInput) paperUrlInput.disabled = false;
            if(submitButton) submitButton.disabled = false;
        }
    }

    function showError(message) {
        if (errorText) errorText.textContent = message;
        if (errorMessage) errorMessage.style.display = 'flex';
        hideOutput(); // Hide results when error occurs
    }

    function hideError() {
        if (errorMessage) errorMessage.style.display = 'none';
    }

     function hideOutput() {
        if (outputContainer) {
            outputContainer.style.display = 'none';
            outputContainer.classList.remove('active');
        }
    }

    function displayResults(data) {
        if (contentMap.linkedin) contentMap.linkedin.textContent = data.linkedin || "Could not generate LinkedIn content.";
        if (contentMap.twitter) contentMap.twitter.textContent = data.twitter || "Could not generate Twitter content.";
        if (contentMap.novice) contentMap.novice.textContent = data.novice || "Could not generate Novice summary.";

        if (outputContainer) {
            outputContainer.style.display = 'block';
            outputContainer.classList.add('active');
        }

         // Ensure the first tab is active by default after generation if elements exist
         if(tabButtons.length > 0 && tabContents.length > 0) {
             activateTab(tabButtons[0], tabContents[0]);
         }
    }

     // CORRECTED validation function
     function isValidArxivUrl(url) {
        // Checks for https://arxiv.org/abs/ followed by number.number and optional version vX
        const commonArxivRegex = /^https?:\/\/arxiv\.org\/abs\/\d+\.\d+(v\d+)?$/;
        return commonArxivRegex.test(url);
     }

    // --- Tab Management ---
    function handleTabSwitch(event) {
        const clickedButton = event.currentTarget;
        const tabName = clickedButton.getAttribute('data-tab');
        const targetContent = document.getElementById(`${tabName}-tab`);

        if (targetContent) { // Ensure target exists
             activateTab(clickedButton, targetContent);
        }
    }

    function activateTab(activeButton, activeContent) {
         // Deactivate all
        tabButtons.forEach(btn => {
            btn.classList.remove('active');
            btn.setAttribute('aria-selected', 'false');
             btn.tabIndex = -1;
        });
        tabContents.forEach(content => {
            if(content){ // Check if content element exists
                content.classList.remove('active');
                content.hidden = true;
            }
        });

        // Activate clicked/specified
        activeButton.classList.add('active');
        activeButton.setAttribute('aria-selected', 'true');
        activeButton.tabIndex = 0;
        activeContent.classList.add('active');
        activeContent.hidden = false;
        // Don't focus button on tab switch, allow content focus
        // activeButton.focus();
    }


    // --- Clipboard Handling ---
    function handleCopy(event) {
        const button = event.currentTarget;
        const contentId = button.getAttribute('data-content');
        const textElement = contentMap[contentId];
        const statusElement = document.getElementById(`${contentId}-copy-status-inline`);

        if (textElement && textElement.textContent && navigator.clipboard) { // Check for clipboard API support
            navigator.clipboard.writeText(textElement.textContent)
                .then(() => showCopyStatus(statusElement, 'Copied!', true))
                .catch(err => {
                    console.error(`Failed to copy ${contentId}:`, err);
                    showCopyStatus(statusElement, 'Failed!', false);
                    // Fallback for older browsers or issues
                    alert("Could not copy automatically. Please select and copy manually.");
                });
        } else {
             console.error(`Content element not found, empty, or clipboard API unavailable for ${contentId}`);
             showCopyStatus(statusElement, 'Error', false);
        }
    }

    function showCopyStatus(element, message, success) {
         if (!element) return;
         element.textContent = message;
         element.style.color = success ? 'var(--success)' : 'var(--danger)';
         element.classList.add('visible');
         setTimeout(() => {
            element.classList.remove('visible');
            // Reset text after fade out (optional)
            // setTimeout(() => { element.textContent = ''; }, 300);
         }, 1500);
    }

    // --- History Management (Simple In-Memory) ---
     let paperHistory = []; // Keep history in memory for the session

    function addToHistory(title, url) {
        // Avoid duplicates based on URL
        if (!paperHistory.some(item => item.url === url)) {
             const timestamp = new Date();
             paperHistory.unshift({ title, url, timestamp }); // Add to the beginning
             // Limit history size
             if (paperHistory.length > 5) {
                 paperHistory.pop(); // Remove the oldest
             }
             updateHistoryDisplay();
        }
    }

    function updateHistoryDisplay() {
        if (!historyList) return;
        historyList.innerHTML = ''; // Clear current list

        if (paperHistory.length === 0) {
            if(historyPlaceholder) historyPlaceholder.style.display = 'block';
             historyList.style.display = 'none';
        } else {
             if(historyPlaceholder) historyPlaceholder.style.display = 'none';
             historyList.style.display = 'block';
             paperHistory.forEach(item => {
                 const li = document.createElement('li');
                 li.classList.add('history-item');

                 const titleDiv = document.createElement('div');
                 titleDiv.classList.add('history-title');
                 titleDiv.textContent = item.title;
                 titleDiv.title = item.title; // Tooltip for long titles

                 const dateDiv = document.createElement('div');
                 dateDiv.classList.add('history-date');
                 dateDiv.textContent = item.timestamp.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

                 const linkA = document.createElement('a');
                 linkA.classList.add('history-link');
                 linkA.href = item.url;
                 linkA.target = '_blank';
                 linkA.rel = 'noopener noreferrer';
                 linkA.innerHTML = `<i class="ph ph-arrow-square-out"></i> View Paper`;

                 li.appendChild(titleDiv);
                 li.appendChild(dateDiv);
                 li.appendChild(linkA);
                 historyList.appendChild(li);
             });
        }
    }

    // --- Run Initialization ---
    init();

}); // End DOMContentLoaded
// END OF FILE papershare/static/js/script.js