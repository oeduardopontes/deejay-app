#!/usr/bin/env python3
"""
Flask Web Application for AI Agent Council
Access your council through a web browser
"""

from flask import Flask, render_template, request, jsonify, session, Response, make_response
from council.orchestrator import AgentCouncil
import os
import secrets
import time
import json
from functools import wraps
from queue import Queue
from threading import Thread
import i18n
import posthog
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Initialize PostHog
posthog_api_key = os.getenv('POSTHOG_API_KEY')
posthog_host = os.getenv('POSTHOG_HOST', 'https://app.posthog.com')

if posthog_api_key:
    posthog.api_key = posthog_api_key
    posthog.host = posthog_host
    print(f"✅ PostHog initialized: {posthog_host}")
else:
    print("⚠️  PostHog API key not found - analytics disabled")

# Add i18n to Jinja2 context
@app.context_processor
def inject_i18n():
    return {
        't': i18n.t,
        'locale': i18n.get_locale(),
        'get_translations': i18n.get_all_translations
    }

# Set locale before each request
@app.before_request
def set_locale_from_cookie():
    locale = request.cookies.get('locale', 'pt')  # Default to Portuguese
    i18n.set_locale(locale)

# Initialize council once at startup
council = None

# Progress tracking
progress_queues = {}

# Simple rate limiting
last_request_time = {}
RATE_LIMIT_SECONDS = 30  # Minimum 30 seconds between requests


def rate_limit(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client_ip = request.remote_addr
        current_time = time.time()

        if client_ip in last_request_time:
            time_since_last = current_time - last_request_time[client_ip]
            if time_since_last < RATE_LIMIT_SECONDS:
                wait_time = int(RATE_LIMIT_SECONDS - time_since_last)
                return jsonify({
                    'error': f'Por favor, aguarde {wait_time} segundos antes de fazer outra requisição.'
                }), 429

        last_request_time[client_ip] = current_time
        return f(*args, **kwargs)
    return decorated_function


def get_council():
    """Lazy initialization of council"""
    global council
    if council is None:
        council = AgentCouncil()
    return council


def get_user_id():
    """Get or create a unique user ID for tracking"""
    if 'user_id' not in session:
        session['user_id'] = secrets.token_hex(16)
    return session['user_id']


def track_event(event_name, properties=None):
    """Track an event in PostHog if enabled"""
    if posthog_api_key:
        try:
            user_id = get_user_id()
            event_properties = {
                'ip': request.remote_addr,
                'locale': i18n.get_locale(),
                'user_agent': request.headers.get('User-Agent', 'Unknown')
            }
            if properties:
                event_properties.update(properties)

            posthog.capture(
                distinct_id=user_id,
                event=event_name,
                properties=event_properties
            )
        except Exception as e:
            # Silently fail if analytics tracking fails
            print(f"⚠️  PostHog tracking error: {e}")


@app.route('/')
def council_page():
    """Council deliberation page"""
    track_event('page_view', {'page': 'council'})
    return render_template('council.html')


@app.route('/api/set-locale', methods=['POST'])
def set_locale():
    """Set the user's preferred locale"""
    data = request.json
    locale = data.get('locale', 'en')

    # Validate locale
    if locale not in ['en', 'pt']:
        return jsonify({'error': 'Invalid locale'}), 400

    # Track locale change
    track_event('locale_changed', {'locale': locale})

    # Create response with cookie
    response = make_response(jsonify({'success': True, 'locale': locale}))
    response.set_cookie('locale', locale, max_age=365*24*60*60)  # 1 year
    return response


@app.route('/api/agents', methods=['GET'])
def get_agents():
    """Get list of available agents with localized info"""
    try:
        council_instance = get_council()
        agents_info = council_instance.get_agent_info()

        agents = []
        for agent_type, info in agents_info.items():
            # Get localized agent info from translations
            localized_role = i18n.t(f'agents.{agent_type}.role')
            localized_expertise = []

            # Try to get localized expertise list
            expertise_key = f'agents.{agent_type}.expertise'
            expertise_data = i18n.get_nested_value(
                i18n.load_translations(i18n.get_locale()),
                expertise_key
            )

            if expertise_data and isinstance(expertise_data, list):
                localized_expertise = expertise_data
            else:
                # Fallback to original if translation not found
                localized_expertise = info['expertise']

            agents.append({
                'id': agent_type,
                'name': agent_type.upper(),
                'role': localized_role if localized_role != expertise_key else info['role'],
                'expertise': localized_expertise
            })

        return jsonify({'agents': agents})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/deliberate', methods=['POST'])
@rate_limit
def deliberate():
    """Run a council deliberation with progress tracking"""
    try:
        data = request.json
        question = data.get('question', '').strip()
        context = data.get('context', {})
        selected_agents = data.get('agents', None)
        session_id = data.get('session_id', secrets.token_hex(8))

        # Get the user's language preference from cookie
        language = request.cookies.get('locale', 'en')

        if not question:
            return jsonify({'error': 'Pergunta é obrigatória'}), 400

        council_instance = get_council()

        # Create progress queue for this session
        progress_queues[session_id] = Queue()

        def progress_callback(progress_data):
            """Callback to track progress"""
            if session_id in progress_queues:
                progress_queues[session_id].put(progress_data)

        # Run deliberation in background thread
        result_container = {'result': None, 'error': None}

        def run_deliberation():
            try:
                # If only one agent selected, use quick_poll
                if selected_agents and len(selected_agents) == 1:
                    result = council_instance.quick_poll(
                        question=question,
                        agent_type=selected_agents[0],
                        language=language
                    )
                else:
                    # Full deliberation with progress tracking
                    result = council_instance.deliberate(
                        question=question,
                        context=context if context else None,
                        selected_agents=selected_agents if selected_agents else None,
                        progress_callback=progress_callback,
                        delay_between_agents=3,
                        language=language
                    )
                result_container['result'] = str(result)
            except Exception as e:
                result_container['error'] = str(e)
            finally:
                # Signal completion
                if session_id in progress_queues:
                    progress_queues[session_id].put({'status': 'done'})

        thread = Thread(target=run_deliberation)
        thread.start()
        thread.join(timeout=120)  # 2 minute timeout

        # Clean up queue
        if session_id in progress_queues:
            del progress_queues[session_id]

        if result_container['error']:
            raise Exception(result_container['error'])

        if result_container['result']:
            # Track successful deliberation
            track_event('council_deliberation', {
                'agents_count': len(selected_agents) if selected_agents else 8,
                'selected_agents': selected_agents if selected_agents else 'all',
                'question_length': len(question),
                'language': language
            })

            return jsonify({
                'success': True,
                'recommendation': result_container['result'],
                'session_id': session_id
            })
        else:
            return jsonify({'error': 'Timeout - deliberação demorou muito tempo'}), 504

    except TimeoutError:
        return jsonify({'error': 'A deliberação demorou muito tempo. Por favor, tente novamente.'}), 504
    except Exception as e:
        error_msg = str(e)

        # Handle specific API errors with user-friendly messages
        if 'overloaded_error' in error_msg.lower() or 'overloaded' in error_msg.lower():
            return jsonify({
                'error': 'A API do Claude está temporariamente sobrecarregada. Por favor, aguarde alguns segundos e tente novamente.'
            }), 503
        elif 'rate_limit' in error_msg.lower():
            return jsonify({
                'error': 'Limite de taxa atingido. Por favor, aguarde um momento antes de tentar novamente.'
            }), 429
        elif 'not_found_error' in error_msg or 'model' in error_msg.lower():
            return jsonify({
                'error': 'Erro de configuração da API. Por favor, verifique as chaves de API e configurações.'
            }), 500
        elif 'authentication' in error_msg.lower() or 'api_key' in error_msg.lower():
            return jsonify({
                'error': 'Erro de autenticação. Por favor, verifique a chave API nas configurações.'
            }), 401
        else:
            return jsonify({
                'error': f'Erro ao processar deliberação. Por favor, tente novamente em alguns instantes.'
            }), 500


@app.route('/api/progress/<session_id>')
def progress_stream(session_id):
    """Stream progress updates via Server-Sent Events"""
    def generate():
        if session_id not in progress_queues:
            yield f"data: {json.dumps({'error': 'Session not found'})}\n\n"
            return

        queue = progress_queues[session_id]

        while True:
            try:
                # Get progress update with timeout
                progress = queue.get(timeout=1)

                # Check if done
                if progress.get('status') == 'done':
                    yield f"data: {json.dumps(progress)}\n\n"
                    break

                # Send progress update
                yield f"data: {json.dumps(progress)}\n\n"

            except:
                # Send heartbeat
                yield f": heartbeat\n\n"
                continue

    return Response(generate(), mimetype='text/event-stream')


@app.route('/api/summarize', methods=['POST'])
def summarize_conversation():
    """Generate a concise summary of the conversation"""
    try:
        data = request.json
        conversation = data.get('conversation', '')

        if not conversation:
            return jsonify({'error': 'No conversation provided'}), 400

        # Get the user's language preference from cookie
        language = request.cookies.get('locale', 'en')

        council_instance = get_council()

        # Language-specific prompts
        if language == 'pt':
            summary_prompt = f"""Crie um resumo muito conciso da seguinte conversa de mentoria para DJ/Produtor Musical.
Foque nos conselhos acionáveis principais e nos pontos mais importantes. Use marcadores. Seja breve (máximo 3-5 pontos).

{conversation}

Forneça um resumo sucinto em formato markdown:"""
        else:
            summary_prompt = f"""Create a very concise summary of the following DJ/Producer mentorship conversation.
Focus on the key actionable advice and main points. Use bullet points. Keep it brief (3-5 points maximum).

{conversation}

Provide a succinct summary in markdown format:"""

        # Use the council's client to generate summary
        summary = council_instance.generate_summary(summary_prompt)

        # Track summary generation
        track_event('summary_generated', {
            'conversation_length': len(conversation),
            'language': language
        })

        return jsonify({'summary': summary})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    try:
        council_instance = get_council()
        return jsonify({
            'status': 'healthy',
            'council': 'initialized'
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500


if __name__ == '__main__':
    print("\n" + "="*80)
    print("🏢  AI AGENT COUNCIL - Web Interface")
    print("="*80)
    print("\n🚀 Starting server...")
    print("📱 Open your browser to: http://localhost:8080")
    print("⌨️  Press Ctrl+C to stop the server\n")
    print("="*80 + "\n")

    app.run(debug=True, host='0.0.0.0', port=8080)
