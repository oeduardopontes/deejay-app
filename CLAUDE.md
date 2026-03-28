# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **DJ/Producer Mentor Council** - an AI-powered mentorship system with 8 specialized agents providing comprehensive guidance for DJs and music producers. The system is built using Flask for the web UI and Anthropic Claude for the AI agents.

**Primary Domain:** Music production, DJ performance, music industry career management
**Languages Supported:** Portuguese (default) and English

## High-Level Architecture

### Multi-Agent System
The core architecture is a **council-based deliberation system** where 8 specialized AI agents provide domain-specific advice:

1. **Agent Layer** (`agents/`) - Individual agent definitions with specific expertise
2. **Orchestration Layer** (`council/orchestrator.py`) - Coordinates agent communication and response synthesis
3. **Web Layer** (`app.py`) - Flask application with API endpoints and UI
4. **Translation Layer** (`i18n.py`, `translations/`) - Multilingual support

### Key Architectural Decisions

**No CrewAI Framework**: Despite the requirements.txt mentioning CrewAI, this codebase uses a **custom orchestration system** via direct Anthropic API calls. The `council/orchestrator.py` directly manages agent interactions using the `anthropic` Python SDK.

**Independent Agent Responses**: Each agent responds independently to the question with shared context - there's no inter-agent communication or iteration. The orchestrator formats all responses together.

**Stateless Sessions**: The web application doesn't maintain conversation history server-side. Each question is treated independently unless context is explicitly provided.

## Development Commands

### Environment Setup
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Mac/Linux
# venv\Scripts\activate   # On Windows

# Install dependencies
pip install -r requirements.txt
```

### Running the Application

**Local Development:**
```bash
# Activate virtual environment
source venv/bin/activate

# Run Flask development server
python app.py
# Access at http://localhost:8080
```

**Production Deployment (Mac Mini):**
```bash
# SSH to Mac Mini and restart service
ssh dwardo@edumini.local "launchctl stop com.deejay.app && launchctl start com.deejay.app"

# View logs
ssh dwardo@edumini.local "tail -f ~/deejay-app/error.log"

# Access at http://edumini.local:8081
```

### Testing

**Quick Test:**
```bash
# Test a single agent consultation
python ask_council.py
```

**Interactive CLI:**
```bash
# Terminal-based UI for testing
python council_ui.py
```

**API Test:**
```bash
# Test the API endpoints
python test_api.py
```

## Agent System

### The 8 Agents

Each agent has:
- **ID** (e.g., `ar`, `coach`, `produtor`)
- **Name** (display name)
- **Role** (one-line description)
- **System Prompt** (defines behavior and expertise boundaries)
- **Expertise Areas** (list of specializations)

**Critical Agent Design Principle:** Each agent's system prompt explicitly tells them to STAY IN THEIR LANE. They are instructed NOT to give advice outside their expertise (e.g., Producer should not give career advice).

### Agent Definitions

Agents are defined in two places:
1. **Individual files** in `agents/` (e.g., `agents/ar.py`) - Contains `AGENT_CONFIG` dict
2. **Orchestrator** (`council/orchestrator.py`) - Contains the full agent definitions used at runtime

**Important:** The `agents/*.py` files appear to be config templates. The actual agent definitions used by the system are in `council/orchestrator.py` lines 36-85.

### Adding or Modifying Agents

**To modify an agent:**
1. Edit the agent definition in `council/orchestrator.py` (in the `self.agents` dict)
2. Update the corresponding file in `agents/` if you want to keep them in sync
3. Update translations in `translations/en.json` and `translations/pt.json` if changing names/roles
4. No restart needed for local dev; restart service for production

**System Prompt Best Practices:**
- Be explicit about what the agent should NOT do
- Include specific technical terminology for the domain
- Request actionable, specific advice (not generic praise)
- Specify response format if needed

## Web Application

### Routes

**Pages:**
- `/` - Main council consultation page (renders `templates/council.html`)

**API Endpoints:**
- `POST /api/set-locale` - Set language preference (pt/en)
- `GET /api/agents` - Get list of agents with localized info
- `POST /api/deliberate` - Run full council deliberation (rate-limited)
- `GET /api/progress/<session_id>` - Server-Sent Events (SSE) stream for deliberation progress
- `POST /api/quick-poll` - Consult single agent (rate-limited)
- `POST /api/summarize` - Generate conversation summary
- `GET /api/health` - Health check endpoint

**Rate Limiting:** Both `/api/deliberate` and `/api/quick-poll` have 30-second rate limits per IP address.

### Internationalization (i18n)

The system uses a custom i18n module (`i18n.py`) that:
- Loads translations from JSON files in `translations/`
- Stores locale preference in cookies (1 year expiration)
- Provides `t()` function for template translations
- Defaults to Portuguese (`pt`)

**To add/edit translations:**
1. Edit `translations/pt.json` (Portuguese)
2. Edit `translations/en.json` (English)
3. Use the `t('key.path')` function in templates

**Translation Structure:**
```json
{
  "app": { "title": "..." },
  "agents": {
    "ar": { "name": "...", "role": "..." }
  }
}
```

### Static Assets

- `static/css/` - Stylesheets
- `static/js/` - JavaScript
- `static/images/agents/` - Agent profile pictures

**Note:** Profile pictures should be named `{agent_id}.png` (e.g., `ar.png`, `coach.png`). SVG versions are also supported. Falls back to `placeholder.png` if not found.

## Environment Variables

Required in `.env` file:

```bash
ANTHROPIC_API_KEY=sk-ant-...  # Required - Anthropic API key
DEFAULT_MODEL=claude-3-haiku-20240307  # Optional - defaults to haiku
TEMPERATURE=0.7  # Optional
MAX_ITERATIONS=5  # Optional
POSTHOG_API_KEY=phc_...  # Optional - LLM usage analytics (token counts, cost, latency)
POSTHOG_HOST=https://us.i.posthog.com  # Optional
```

**Security Note:** The `.env` file is gitignored. Use `.env.example` as a template.

## Deployment Architecture

**Production Environment:**
- **Server:** Mac Mini (edumini.local)
- **Service Manager:** macOS LaunchAgent (`com.deejay.app`)
- **Process Manager:** gunicorn with 4 workers (`start_deejay.sh`)
- **Port:** 8081
- **Working Directory:** `/Users/dwardo/deejay-app/`
- **Start Script:** `start_deejay.sh`

**Deployment Process:**
```bash
# Sync code from local to server
rsync -avz --exclude 'venv' --exclude '__pycache__' \
  /Users/dwardo/Claude/deejay.com.br/ \
  dwardo@edumini.local:~/deejay-app/

# Restart service
ssh dwardo@edumini.local "launchctl stop com.deejay.app && launchctl start com.deejay.app"
```

**Log Files:**
- `error.log` - Application errors
- `access.log` - HTTP access logs
- `stdout.log` - Standard output
- `stderr.log` - Standard error

## Important Implementation Details

### Council Deliberation Flow

When `council.deliberate()` is called:
1. Determines which agents to consult (default: all 8)
2. For each agent:
   - Calls Anthropic API with agent's system prompt
   - Passes question + optional context
   - Adds language instruction to system prompt
   - Waits 2 seconds between agents (configurable delay)
3. Formats all responses into a single markdown document
4. Returns formatted response with each agent's section

**No Synthesis Agent:** The final response is just a formatted concatenation of individual agent responses. There's no "meta-agent" that synthesizes the council's advice.

**Max 3 Agents (UI):** The web UI enforces a maximum of 3 agents per consultation (client-side limit in `static/js/app.js`). The backend `deliberate()` has no such limit.

### Progress Tracking

The web UI supports real-time progress updates during deliberation:
- Uses Server-Sent Events (SSE) for streaming updates
- Progress queue per session ID
- Updates show which agent is currently being consulted

### API Model Used

**Default Model:** `claude-3-haiku-20240307` (fast and cost-effective)
**Max Tokens:** 2000 per agent response
**Temperature:** Controlled by system prompt (not explicitly set in API calls)

**Cost Consideration:** With 8 agents and 2000 max tokens each, a full deliberation can use ~16k tokens output. Haiku is used for cost efficiency.

## Working with This Codebase

### Common Tasks

**Add a new agent:**
1. Add agent definition to `council/orchestrator.py` in `self.agents` dict (line ~36)
2. Create `agents/{agent_id}.py` with `AGENT_CONFIG` (optional, for documentation)
3. Add translations to `translations/pt.json` and `translations/en.json`
4. Add profile picture to `static/images/agents/{agent_id}.png`

**Modify agent behavior:**
- Edit the `system_prompt` in `council/orchestrator.py`
- Test with `python ask_council.py` or `python council_ui.py`
- Deploy changes to production

**Update UI copy:**
- Edit translations in `translations/pt.json` and `translations/en.json`
- Changes take effect immediately (no restart needed in dev mode)

**Adjust rate limiting:**
- Modify `RATE_LIMIT_SECONDS` in `app.py` (line 44)

### Testing Strategy

1. **Unit Testing:** Test individual agent responses with `quick_poll()`
2. **Integration Testing:** Test full council with `deliberate()`
3. **UI Testing:** Use web interface or `test_api.py`
4. **Language Testing:** Test both PT and EN responses

**Example Test:**
```python
from council.orchestrator import AgentCouncil

council = AgentCouncil()

# Test single agent
response = council.quick_poll(
    question="Como melhorar meu beatmatching?",
    agent_type="coach",
    language="pt"
)
print(response)

# Test full council
response = council.deliberate(
    question="Preciso de feedback sobre minha track",
    selected_agents=["curador", "produtor", "ar"],
    language="pt"
)
print(response)
```

## Documentation Files

The repository includes extensive documentation:
- `AGENTS_README.md` - Agent system overview
- `CREATING_COUNCILS.md` - How to create new councils/agents
- `AGENT_TEMPLATES.md` - Agent templates and examples
- `DEPLOYMENT.md` - Production deployment guide
- `QUICK_START.md` - Quick start guide (in Portuguese)
- `SERVICE_MANAGEMENT.md` - Service management commands
- `TROUBLESHOOTING.md` - Common issues and solutions

## Sister Application

This codebase has a sister application called **Executive Council** (eduardopontes.com):
- Same architecture (agent council system)
- Different domain (business/executive decisions)
- Different agents (CEO, CFO, CTO, CMO)
- Deployed on same Mac Mini at port 8080

The two applications share architectural patterns but are separate codebases.
