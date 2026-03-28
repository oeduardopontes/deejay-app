// Global state
let agents = [];
let contextCounter = 0;
let lastQuestion = '';
let lastAnswer = '';
let lastSelectedAgents = [];
let allResponses = [];  // Store all responses for summary generation

// Load agents on page load
document.addEventListener('DOMContentLoaded', () => {
    loadAgents();
    initializeUI();
});

// Initialize UI enhancements
function initializeUI() {
    const textarea = document.getElementById('question');
    if (textarea) {
        // Add character counter
        textarea.addEventListener('input', updateCharCount);

        // Add auto-resize
        textarea.addEventListener('input', autoResize);

        // Keyboard shortcuts
        textarea.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                e.preventDefault();
                submitDeliberation();
            }
        });
    }
}

// Auto-resize textarea
function autoResize() {
    const textarea = document.getElementById('question');
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 300) + 'px';
}

// Update character count
function updateCharCount() {
    const textarea = document.getElementById('question');
    const length = textarea.value.length;

    // Show character count if text exists
    let counter = document.querySelector('.char-count');
    if (!counter && length > 0) {
        counter = document.createElement('div');
        counter.className = 'char-count';
        textarea.parentElement.appendChild(counter);
    }

    if (counter) {
        counter.textContent = `${length} `+t("form.character_count")+``;
        counter.style.display = length > 0 ? 'block' : 'none';
    }
}

// Load available agents from API
async function loadAgents() {
    try {
        const response = await fetch('/api/agents');
        const data = await response.json();
        agents = data.agents;
        renderAgents();
    } catch (error) {
        console.error('Erro ao carregar agentes:', error);
        showError('Falha ao carregar agentes. Por favor, atualize a página.');
    }
}

// Render agent checkboxes
function renderAgents() {
    const agentsList = document.getElementById('agents-list');
    agentsList.innerHTML = '';

    agents.forEach(agent => {
        const label = document.createElement('label');
        label.className = 'agent-option';
        label.innerHTML = `
            <input type="checkbox" value="${agent.id}" class="agent-checkbox" onchange="limitAgentSelection()">
            <img src="/static/images/agents/${agent.id}.png" alt="${agent.role}" class="agent-profile-pic" onerror="this.src='/static/images/agents/placeholder.png'">
            <div class="agent-info">
                <strong>${agent.role}</strong>
                <small>${agent.expertise.join(', ')}</small>
            </div>
        `;
        agentsList.appendChild(label);
    });

    // Set initial button state (disabled since no agents selected)
    limitAgentSelection();
}

// Limit agent selection to maximum 3
function limitAgentSelection() {
    const checkboxes = document.querySelectorAll('.agent-checkbox');
    const checked = document.querySelectorAll('.agent-checkbox:checked');
    const submitBtn = document.getElementById('submit-btn');

    // Disable unchecked boxes if 3 are selected
    if (checked.length >= 3) {
        checkboxes.forEach(cb => {
            if (!cb.checked) {
                cb.disabled = true;
            }
        });
    } else {
        checkboxes.forEach(cb => {
            cb.disabled = false;
        });
    }

    // Enable/disable submit button based on selection
    if (checked.length === 0) {
        submitBtn.disabled = true;
        submitBtn.style.opacity = '0.5';
        submitBtn.style.cursor = 'not-allowed';
    } else {
        submitBtn.disabled = false;
        submitBtn.style.opacity = '1';
        submitBtn.style.cursor = 'pointer';
    }
}

// Add context item
function addContextItem() {
    const container = document.getElementById('context-items');
    const item = document.createElement('div');
    item.className = 'context-item';
    item.id = `context-${contextCounter}`;
    item.innerHTML = `
        <input type="text" placeholder="Chave (ex: Orçamento)" class="context-key">
        <input type="text" placeholder="Valor (ex: R$ 500 mil)" class="context-value">
        <button class="btn-remove" onclick="removeContextItem(${contextCounter})">Remover</button>
    `;
    container.appendChild(item);
    contextCounter++;
}

// Remove context item
function removeContextItem(id) {
    const item = document.getElementById(`context-${id}`);
    item.remove();
}

// Collect context from form
function getContext() {
    const context = {};
    const items = document.querySelectorAll('.context-item');

    items.forEach(item => {
        const key = item.querySelector('.context-key').value.trim();
        const value = item.querySelector('.context-value').value.trim();
        if (key && value) {
            context[key] = value;
        }
    });

    return Object.keys(context).length > 0 ? context : null;
}

// Get selected agents
function getSelectedAgents() {
    const checkboxes = document.querySelectorAll('.agent-checkbox:checked');
    const selected = Array.from(checkboxes).map(cb => cb.value);
    return selected.length > 0 ? selected : null;
}

// Show simple loading spinner
function showLoadingSpinner() {
    const loadingEl = document.getElementById('loading');
    const spinner = loadingEl.querySelector('.spinner');
    const loadingText = loadingEl.querySelector('p');

    if (spinner) spinner.style.display = 'block';
    if (loadingText) {
        loadingText.style.display = 'block';
        loadingText.textContent = t('form.progress_consulting');
    }
}

// Submit deliberation with progress tracking
async function submitDeliberation() {
    const question = document.getElementById('question').value.trim();

    if (!question) {
        const textarea = document.getElementById('question');
        textarea.style.borderColor = '#ef4444';
        textarea.focus();
        showError('Por favor, insira uma pergunta para o conselho deliberar.');

        setTimeout(() => {
            textarea.style.borderColor = '';
        }, 3000);
        return;
    }

    const context = getContext();
    const selectedAgents = getSelectedAgents();
    const sessionId = 'session_' + Date.now();

    // Store for follow-up
    lastQuestion = question;
    lastSelectedAgents = selectedAgents || [];

    const loadingEl = document.getElementById('loading');
    const submitBtn = document.getElementById('submit-btn');
    const resultsSection = document.getElementById('results-section');

    loadingEl.style.display = 'flex';
    submitBtn.disabled = true;
    submitBtn.textContent = '⏳ ' + t('form.submit_button_loading');
    resultsSection.style.display = 'none';

    // Show simple loading spinner
    showLoadingSpinner();

    try {
        const response = await fetch('/api/deliberate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                question: question,
                context: context,
                agents: selectedAgents,
                session_id: sessionId
            })
        });

        const data = await response.json();

        if (response.ok) {
            showResults(data.recommendation);
            submitBtn.textContent = '✓ ' + t('form.submit_button_success');
            setTimeout(() => {
                submitBtn.textContent = '🚀 ' + t('form.submit_button');
            }, 3000);
        } else {
            if (response.status === 503) {
                showError(data.error + ' ⏳');
            } else {
                showError(data.error || t('errors.deliberation_error'));
            }
            submitBtn.textContent = '🚀 ' + t('form.submit_button');
        }
    } catch (error) {
        console.error('Erro:', error);
        showError(t('errors.connection_error'));
        submitBtn.textContent = '🚀 ' + t('form.submit_button');
    } finally {
        loadingEl.style.display = 'none';
        submitBtn.disabled = false;
    }
}

// Show results
function showResults(recommendation) {
    const resultsSection = document.getElementById('results-section');
    const resultsContent = document.getElementById('results');

    // Store original markdown for copying
    resultsContent.dataset.originalText = recommendation;

    // Store for follow-up context and summary
    lastAnswer = recommendation;
    allResponses.push({
        question: lastQuestion,
        answer: recommendation
    });

    // Parse markdown and render as HTML
    resultsContent.innerHTML = marked.parse(recommendation);
    resultsSection.style.display = 'block';

    // Add fade-in animation
    resultsSection.style.opacity = '0';
    resultsSection.style.transform = 'translateY(20px)';

    setTimeout(() => {
        resultsSection.style.transition = 'all 0.4s ease';
        resultsSection.style.opacity = '1';
        resultsSection.style.transform = 'translateY(0)';
    }, 10);

    // Scroll to results
    setTimeout(() => {
        resultsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }, 100);

    // Add copy button
    addCopyButton(resultsContent);

    // Generate summary
    generateSummary(resultsSection);

    // Display follow-up section with selected agents
    displayFollowupSection();
}

// Add copy and download buttons to results
function addCopyButton(resultsContent) {
    // Remove existing buttons if any
    const existingBtns = resultsContent.parentElement.querySelectorAll('.copy-btn, .download-btn');
    existingBtns.forEach(btn => btn.remove());

    // Store the original markdown text
    const markdownText = resultsContent.dataset.originalText || resultsContent.textContent;

    // Create button container
    const buttonContainer = document.createElement('div');
    buttonContainer.style.marginTop = '1rem';
    buttonContainer.style.display = 'flex';
    buttonContainer.style.gap = '10px';

    // Copy button
    const copyBtn = document.createElement('button');
    copyBtn.className = 'btn-secondary copy-btn';
    copyBtn.textContent = '📋 ' + t('form.copy_button');
    copyBtn.onclick = () => {
        navigator.clipboard.writeText(markdownText).then(() => {
            copyBtn.textContent = '✓ ' + t('form.copy_success');
            setTimeout(() => {
                copyBtn.textContent = '📋 ' + t('form.copy_button');
            }, 2000);
        });
    };

    // Download button
    const downloadBtn = document.createElement('button');
    downloadBtn.className = 'btn-secondary download-btn';
    downloadBtn.textContent = '💾 Download MD';
    downloadBtn.onclick = () => {
        // Create blob with markdown content
        const blob = new Blob([markdownText], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);

        // Create temporary link and trigger download
        const a = document.createElement('a');
        a.href = url;
        a.download = 'deejay-crew-response-' + new Date().toISOString().slice(0, 10) + '.md';
        document.body.appendChild(a);
        a.click();

        // Cleanup
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        // Visual feedback
        downloadBtn.textContent = '✓ Downloaded';
        setTimeout(() => {
            downloadBtn.textContent = '💾 Download MD';
        }, 2000);
    };

    buttonContainer.appendChild(copyBtn);
    buttonContainer.appendChild(downloadBtn);
    resultsContent.parentElement.appendChild(buttonContainer);
}

// Show error
function showError(message) {
    const resultsSection = document.getElementById('results-section');
    const resultsContent = document.getElementById('results');

    resultsContent.innerHTML = `<div class="error">❌ ${message}</div>`;
    resultsSection.style.display = 'block';

    // Scroll to error
    setTimeout(() => {
        resultsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }, 100);
}

// Generate summary of all responses
async function generateSummary(container) {
    const summaryBox = document.createElement('div');
    summaryBox.className = 'summary-box';

    const title = document.createElement('h3');
    title.innerHTML = '⚡ ' + t('form.summary_title');
    summaryBox.appendChild(title);

    const content = document.createElement('div');
    content.className = 'summary-box-content';
    content.innerHTML = '<em>' + t('form.summary_generating') + '</em>';
    summaryBox.appendChild(content);

    container.appendChild(summaryBox);

    // Prepare all responses for summarization
    const responsesText = allResponses.map((r, i) =>
        `### ${i === 0 ? 'Original Question' : 'Follow-up ' + i}:\n${r.question}\n\n**Response:**\n${r.answer}`
    ).join('\n\n---\n\n');

    try {
        const response = await fetch('/api/summarize', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                conversation: responsesText
            })
        });

        const data = await response.json();

        if (response.ok) {
            content.innerHTML = marked.parse(data.summary);
        } else {
            content.innerHTML = '<em>Unable to generate summary</em>';
        }
    } catch (error) {
        console.error('Error generating summary:', error);
        content.innerHTML = '<em>Unable to generate summary</em>';
    }
}

// Display follow-up section
function displayFollowupSection() {
    const followupSection = document.getElementById('followup-section');
    followupSection.style.display = 'block';

    displayFollowupAgents();
}

// Display selected agents for follow-up (read-only)
function displayFollowupAgents() {
    const displayContainer = document.getElementById('followup-agents-display');
    displayContainer.innerHTML = '';

    if (lastSelectedAgents.length === 0) {
        return;
    }

    const title = document.createElement('p');
    title.className = 'hint';
    title.style.marginTop = '0';
    title.style.marginBottom = '10px';
    title.textContent = t('form.followup_continuing');
    displayContainer.appendChild(title);

    const agentsGrid = document.createElement('div');
    agentsGrid.style.display = 'flex';
    agentsGrid.style.gap = '8px';
    agentsGrid.style.flexWrap = 'wrap';

    lastSelectedAgents.forEach(agentId => {
        const agent = agents.find(a => a.id === agentId);
        if (!agent) return;

        const agentChip = document.createElement('div');
        agentChip.style.display = 'flex';
        agentChip.style.alignItems = 'center';
        agentChip.style.gap = '8px';
        agentChip.style.padding = '6px 12px';
        agentChip.style.background = 'rgba(30, 30, 45, 0.6)';
        agentChip.style.borderRadius = '20px';
        agentChip.style.border = '1px solid rgba(138, 43, 226, 0.4)';

        const img = document.createElement('img');
        img.src = `/static/images/agents/${agent.id}.png`;
        img.alt = agent.role;
        img.style.width = '24px';
        img.style.height = '24px';
        img.style.borderRadius = '50%';
        img.style.border = '1px solid rgba(138, 43, 226, 0.5)';

        const name = document.createElement('span');
        name.style.fontSize = '0.85rem';
        name.style.color = '#c084fc';
        name.textContent = agent.role;

        agentChip.appendChild(img);
        agentChip.appendChild(name);
        agentsGrid.appendChild(agentChip);
    });

    displayContainer.appendChild(agentsGrid);
}

// Submit follow-up question
async function submitFollowup() {
    const followupQuestion = document.getElementById('followup-question').value.trim();

    if (!followupQuestion) {
        const textarea = document.getElementById('followup-question');
        textarea.style.borderColor = '#ef4444';
        textarea.focus();
        setTimeout(() => {
            textarea.style.borderColor = '';
        }, 3000);
        return;
    }

    const loadingEl = document.getElementById('loading');
    const followupBtn = document.getElementById('followup-btn');
    const sessionId = 'session_' + Date.now();

    loadingEl.style.display = 'flex';
    followupBtn.disabled = true;
    followupBtn.textContent = '⏳ ' + t('form.submit_button_loading');

    showLoadingSpinner();

    // Prepare context with previous Q&A
    const contextWithHistory = {
        'Previous Question': lastQuestion,
        'Previous Answer': lastAnswer,
        'Follow-up Question': followupQuestion
    };

    try {
        const response = await fetch('/api/deliberate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                question: followupQuestion,
                context: contextWithHistory,
                agents: lastSelectedAgents,
                session_id: sessionId
            })
        });

        const data = await response.json();

        if (response.ok) {
            // Store response for summary
            allResponses.push({
                question: followupQuestion,
                answer: data.recommendation
            });

            // Create a new response card
            const container = document.getElementById('followup-responses-container');

            const responseCard = document.createElement('section');
            responseCard.className = 'card';
            responseCard.style.marginTop = '20px';

            const title = document.createElement('h2');
            title.textContent = '💡 ' + t('form.results_title');
            responseCard.appendChild(title);

            const content = document.createElement('div');
            content.className = 'results-content';
            content.dataset.originalText = data.recommendation;
            content.innerHTML = marked.parse(data.recommendation);
            responseCard.appendChild(content);

            container.appendChild(responseCard);

            // Add fade-in animation
            responseCard.style.opacity = '0';
            responseCard.style.transform = 'translateY(20px)';
            setTimeout(() => {
                responseCard.style.transition = 'all 0.4s ease';
                responseCard.style.opacity = '1';
                responseCard.style.transform = 'translateY(0)';
            }, 10);

            // Add copy and download buttons
            addCopyButton(content);

            // Generate updated summary
            generateSummary(responseCard);

            // Update last answer for next follow-up
            lastAnswer = data.recommendation;

            // Clear follow-up input
            document.getElementById('followup-question').value = '';

            // Visual feedback
            followupBtn.textContent = '✓ ' + t('form.submit_button_success');
            setTimeout(() => {
                followupBtn.textContent = '🚀 ' + t('form.followup_button');
            }, 3000);

            // Scroll to new response
            setTimeout(() => {
                responseCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }, 100);
        } else {
            if (response.status === 503) {
                showError(data.error + ' ⏳');
            } else {
                showError(data.error || t('errors.deliberation_error'));
            }
            followupBtn.textContent = '🚀 ' + t('form.followup_button');
        }
    } catch (error) {
        console.error('Erro:', error);
        showError(t('errors.connection_error'));
        followupBtn.textContent = '🚀 ' + t('form.followup_button');
    } finally {
        loadingEl.style.display = 'none';
        followupBtn.disabled = false;
    }
}
