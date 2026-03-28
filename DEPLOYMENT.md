# DJ Crew App Deployment on Mac Mini

## Service Information

The DJ Crew mentorship application is deployed on your Mac Mini (edumini.local) as a LaunchAgent service that runs 24/7.

**Access URL:** `http://edumini.local:8081`

---

## Service Management Commands

### Check Status
```bash
ssh dwardo@edumini.local "launchctl list | grep deejay"
```

### Stop Service
```bash
ssh dwardo@edumini.local "launchctl stop com.deejay.app"
```

### Start Service
```bash
ssh dwardo@edumini.local "launchctl start com.deejay.app"
```

### Restart Service
```bash
ssh dwardo@edumini.local "launchctl stop com.deejay.app && launchctl start com.deejay.app"
```

---

## View Logs

### Error Logs
```bash
ssh dwardo@edumini.local "tail -f ~/deejay-app/error.log"
```

### Access Logs
```bash
ssh dwardo@edumini.local "tail -f ~/deejay-app/access.log"
```

### Standard Output
```bash
ssh dwardo@edumini.local "tail -f ~/deejay-app/stdout.log"
```

### Standard Error
```bash
ssh dwardo@edumini.local "tail -f ~/deejay-app/stderr.log"
```

---

## Update Application Code

To deploy code changes:

```bash
# Sync files from local machine
rsync -avz --exclude 'venv' --exclude '__pycache__' --exclude '*.pyc' --exclude '.git' --exclude '.DS_Store' /Users/dwardo/Claude/deejay.com.br/ dwardo@edumini.local:~/deejay-app/

# Restart service
ssh dwardo@edumini.local "launchctl stop com.deejay.app && launchctl start com.deejay.app"
```

---

## Update Python Dependencies

If you update requirements.txt:

```bash
ssh dwardo@edumini.local "cd ~/deejay-app && source venv/bin/activate && pip install -r requirements.txt"
ssh dwardo@edumini.local "launchctl stop com.deejay.app && launchctl start com.deejay.app"
```

---

## File Locations on Mac Mini

- **Application Directory:** `/Users/dwardo/deejay-app/`
- **LaunchAgent Config:** `/Users/dwardo/Library/LaunchAgents/com.deejay.app.plist`
- **Start Script:** `/Users/dwardo/deejay-app/start_deejay.sh`
- **Environment Variables:** `/Users/dwardo/deejay-app/.env`
- **Virtual Environment:** `/Users/dwardo/deejay-app/venv/`

---

## Access Endpoints

- **Main Application:** `http://edumini.local:8081`
- **Health Check:** `http://edumini.local:8081/api/health`
- **Agents List:** `http://edumini.local:8081/api/agents`
- **Summary API:** `http://edumini.local:8081/api/summarize`

---

## Features

### Summary Feature
After each agent consultation, a visually distinct purple summary box appears showing 3-5 key takeaways from the conversation. The summary updates after follow-up questions to reflect all advice received.

### Multi-Language Support
- Default language: Portuguese
- Language preference saved in cookies
- Toggle between PT/EN with switcher in top-right

### Agent Selection
Choose up to 3 specialized DJ/Producer mentors:
- A&R (Artistic Mentor)
- DJ Coach
- Music Producer Mentor
- Curator / Music Critic
- Digital Strategist
- Booker / Show Agent
- Career Manager
- Entertainment Lawyer

---

## Both Applications Running

Two separate applications are running on the Mac Mini:

1. **eduardopontes.com** (Executive Council)
   - Port: 8080
   - URL: `http://edumini.local:8080`
   - Service: `com.council.app`
   - Directory: `~/council-app/`

2. **deejay.com.br** (DJ Crew)
   - Port: 8081
   - URL: `http://edumini.local:8081`
   - Service: `com.deejay.app`
   - Directory: `~/deejay-app/`
