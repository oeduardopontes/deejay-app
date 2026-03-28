"""
DJ/Producer Mentor Council Orchestrator
Coordinates 8 specialized agents for comprehensive DJ/Producer mentorship
"""

import anthropic
import os
from typing import Dict, List, Optional, Callable, Any
import time
from datetime import datetime
import posthog


class AgentCouncil:
    """
    Orchestrates a council of 8 specialized mentoring agents for DJ/Producers:
    - A&R (Artistic Mentor)
    - DJ Coach
    - Music Producer Mentor
    - Music Curator/Critic
    - Digital Strategist
    - Booker/Show Agent
    - Career Manager
    - Entertainment Lawyer
    """

    def __init__(self):
        """Initialize the council with API clients"""
        self.anthropic_key = os.getenv('ANTHROPIC_API_KEY')

        if not self.anthropic_key:
            raise ValueError("ANTHROPIC_API_KEY não encontrada nas variáveis de ambiente")

        self.client = anthropic.Anthropic(api_key=self.anthropic_key)
        self.model = "claude-3-haiku-20240307"

        # Initialize PostHog for LLM tracking if not already initialized
        posthog_api_key = os.getenv('POSTHOG_API_KEY')
        posthog_host = os.getenv('POSTHOG_HOST', 'https://app.posthog.com')

        if posthog_api_key and not posthog.api_key:
            posthog.api_key = posthog_api_key
            posthog.host = posthog_host

        self.posthog_enabled = bool(posthog.api_key)
        if self.posthog_enabled:
            print("✅ PostHog LLM tracking enabled")

        # Agent definitions
        self.agents = {
            'ar': {
                'name': 'Mentor Artístico (A&R)',
                'role': 'Definir identidade sonora e estratégia criativa',
                'system_prompt': 'Você é um A&R experiente com 15 anos de experiência. Sua especialidade é IDENTIDADE SONORA e posicionamento de artista. Foque em: 1) Análise de referências e influências, 2) Direcionamento de estilo único, 3) Estratégia de marca artística. Seja ESPECÍFICO sobre gêneros, subgêneros e artistas comparáveis. Evite conselhos genéricos sobre produção ou carreira - isso não é sua área.',
                'expertise': ['identidade_sonora', 'análise_referências', 'roadmap_artístico']
            },
            'coach': {
                'name': 'Coach de DJ',
                'role': 'Corrigir técnica, leitura de pista e construção de set',
                'system_prompt': 'Você é um Coach de DJ profissional. Sua especialidade é TÉCNICA DE PERFORMANCE e leitura de público. Foque EXCLUSIVAMENTE em: 1) Técnicas de mixagem (beatmatching, EQ, FX), 2) Estrutura e energia do set, 3) Leitura de pista. Dê instruções PRÁTICAS e passo-a-passo. NÃO dê conselhos sobre produção, marketing ou negócios - não é sua área.',
                'expertise': ['analisar_set', 'plano_treino', 'equipamento_recomendado']
            },
            'produtor': {
                'name': 'Produtor Musical Mentor',
                'role': 'Ensinar produção, arranjo, mix e master',
                'system_prompt': 'Você é um Produtor Musical com estúdio próprio. Sua especialidade é PRODUÇÃO TÉCNICA: arranjo, sound design, mixagem e masterização. Forneça: 1) Feedback técnico específico sobre frequências, compressão, espacialização, 2) Sugestões de plugins e técnicas, 3) Checklist de finalização. Seja TÉCNICO e detalhado. NÃO opine sobre carreira, shows ou contratos.',
                'expertise': ['feedback_mix', 'arranjo', 'sound_design']
            },
            'curador': {
                'name': 'Curador / Crítico Musical',
                'role': 'Avaliar faixas e sets com feedback técnico',
                'system_prompt': 'Você é um Curador Musical crítico que trabalha para selos e plataformas. Sua especialidade é AVALIAÇÃO CRÍTICA e potencial comercial. Analise: 1) Qualidade técnica vs mercado, 2) Apelo comercial e originalidade, 3) Pontos de melhoria específicos. Seja HONESTO e crítico - não elogie apenas para agradar. NÃO dê conselhos de carreira ou negociação.',
                'expertise': ['analise_tecnica', 'avaliacao_comercial', 'acoes_melhoria']
            },
            'estratega': {
                'name': 'Estrategista Digital',
                'role': 'Planejar campanhas de lançamento e crescimento',
                'system_prompt': 'Você é um Estrategista Digital especializado em música eletrônica. Sua área é MARKETING DIGITAL e crescimento online. Forneça: 1) Planos de lançamento com cronograma, 2) Estratégias de conteúdo para redes sociais, 3) Táticas de ads e métricas. Use NÚMEROS e seja específico sobre plataformas. NÃO opine sobre produção musical ou técnica de DJ.',
                'expertise': ['plano_lancamento', 'conteudo_social', 'ads_strategy']
            },
            'booker': {
                'name': 'Booker / Agente de Shows',
                'role': 'Negociar gigs e criar agenda de shows',
                'system_prompt': 'Você é um Booker de artistas eletrônicos. Sua especialidade é NEGOCIAÇÃO DE SHOWS e networking com venues. Foque em: 1) Estratégias de pitching e precificação, 2) Press kit e materiais de divulgação, 3) Rider técnico e requisitos. Forneça SCRIPTS práticos e faixas de cachê realistas. NÃO opine sobre produção ou conteúdo criativo.',
                'expertise': ['negociacao_gigs', 'press_kit', 'rider']
            },
            'manager': {
                'name': 'Manager / Consultor de Carreira',
                'role': 'Planejar carreira, metas e finanças',
                'system_prompt': 'Você é um Manager de artistas com visão 360°. Sua especialidade é PLANEJAMENTO ESTRATÉGICO de carreira e gestão financeira. Forneça: 1) Planos trimestrais com metas mensuráveis, 2) Alocação de tempo e recursos, 3) Priorização de ações. Seja PRAGMÁTICO sobre orçamento e ROI. NÃO opine sobre técnicas de produção ou performance.',
                'expertise': ['planejamento_carreira', 'orcamento', 'cronograma']
            },
            'advogado': {
                'name': 'Advogado de Entretenimento',
                'role': 'Revisar contratos e explicar direitos autorais',
                'system_prompt': 'Você é um Advogado especializado em Entretenimento e Direito Autoral. Sua área é PROTEÇÃO LEGAL e contratos. Foque EXCLUSIVAMENTE em: 1) Revisão de cláusulas contratuais, 2) Direitos autorais e splits, 3) Registro de obras. Cite termos legais e práticas de mercado. NÃO opine sobre criatividade, marketing ou carreira artística.',
                'expertise': ['revisao_contrato', 'direitos_autorais', 'registro_obras']
            }
        }

    def get_agent_info(self) -> Dict[str, Dict]:
        """Return information about all available agents"""
        return {
            agent_id: {
                'name': info['name'],
                'role': info['role'],
                'expertise': info['expertise']
            }
            for agent_id, info in self.agents.items()
        }

    def _call_agent(self, agent_id: str, question: str, context: Optional[str] = None, language: str = 'pt') -> str:
        """
        Call a specific agent with a question

        Args:
            agent_id: ID of the agent to call
            question: The question to ask
            context: Optional context from previous responses
            language: Language for the response (pt or en)

        Returns:
            Agent's response as a string
        """
        if agent_id not in self.agents:
            raise ValueError(f"Agente desconhecido: {agent_id}")

        agent = self.agents[agent_id]

        # Build the message with context if provided
        user_message = question
        if context:
            user_message = f"Contexto:\n{context}\n\nPergunta:\n{question}"

        # Add language instruction to system prompt
        system_prompt = agent['system_prompt']
        if language == 'pt':
            system_prompt += "\n\nIMPORTANTE: Responda SEMPRE em português brasileiro."
        else:
            system_prompt += "\n\nIMPORTANT: Always respond in English."

        # Track LLM call start time
        start_time = time.time()

        try:
            # Call Anthropic API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                system=system_prompt,
                messages=[{
                    "role": "user",
                    "content": user_message
                }]
            )

            # Calculate metrics
            latency_ms = (time.time() - start_time) * 1000
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            total_tokens = input_tokens + output_tokens

            # Calculate cost (Claude 3 Haiku pricing)
            input_cost = (input_tokens / 1_000_000) * 0.25
            output_cost = (output_tokens / 1_000_000) * 1.25
            total_cost = input_cost + output_cost

            # Track LLM generation in PostHog
            if self.posthog_enabled:
                try:
                    posthog.capture(
                        distinct_id=f"agent_{agent_id}",
                        event="$ai_generation",
                        properties={
                            "$ai_model": self.model,
                            "$ai_provider": "anthropic",
                            "$ai_input_tokens": input_tokens,
                            "$ai_output_tokens": output_tokens,
                            "$ai_total_tokens": total_tokens,
                            "$ai_input_cost_usd": input_cost,
                            "$ai_output_cost_usd": output_cost,
                            "$ai_total_cost_usd": total_cost,
                            "$ai_latency_ms": latency_ms,
                            "$ai_stop_reason": response.stop_reason,
                            "agent_id": agent_id,
                            "agent_name": agent['name'],
                            "agent_role": agent['role'],
                            "language": language,
                            "has_context": bool(context),
                            "question_length": len(question),
                            "response_length": len(response.content[0].text)
                        }
                    )
                except Exception as e:
                    print(f"⚠️  PostHog LLM tracking error: {e}")

            return response.content[0].text

        except Exception as e:
            # Track error in PostHog
            if self.posthog_enabled:
                try:
                    posthog.capture(
                        distinct_id=f"agent_{agent_id}",
                        event="$ai_generation_error",
                        properties={
                            "$ai_model": self.model,
                            "$ai_provider": "anthropic",
                            "$ai_latency_ms": (time.time() - start_time) * 1000,
                            "agent_id": agent_id,
                            "agent_name": agent['name'],
                            "error": str(e),
                            "language": language
                        }
                    )
                except:
                    pass
            raise Exception(f"Erro ao chamar agente {agent_id}: {str(e)}")

    def quick_poll(self, question: str, agent_type: str, language: str = 'pt') -> str:
        """
        Quick consultation with a single agent

        Args:
            question: The question to ask
            agent_type: Which agent to consult
            language: Language for response

        Returns:
            Agent's response
        """
        return self._call_agent(agent_type, question, language=language)

    def deliberate(
        self,
        question: str,
        context: Optional[Dict] = None,
        selected_agents: Optional[List[str]] = None,
        progress_callback: Optional[Callable] = None,
        delay_between_agents: int = 2,
        language: str = 'pt'
    ) -> str:
        """
        Run a full council deliberation

        Args:
            question: The question or scenario to deliberate on
            context: Optional context dictionary
            selected_agents: List of agent IDs to consult (None = all agents)
            progress_callback: Optional callback for progress updates
            delay_between_agents: Delay in seconds between agent calls
            language: Language for responses

        Returns:
            Final synthesized recommendation
        """
        # Determine which agents to use
        agents_to_use = selected_agents if selected_agents else list(self.agents.keys())

        # Collect responses from each agent
        responses = {}

        for i, agent_id in enumerate(agents_to_use):
            if progress_callback:
                progress_callback({
                    'status': 'consulting',
                    'agent': self.agents[agent_id]['name'],
                    'progress': int((i / len(agents_to_use)) * 100)
                })

            # Build context string from the provided context dict (not from other agents)
            context_str = None
            if context:
                context_str = "\n".join([f"{key}: {value}" for key, value in context.items()])

            # Get agent's response (each agent responds independently)
            try:
                response = self._call_agent(agent_id, question, context_str, language)
                responses[agent_id] = response

                # Delay before next agent (except for last one)
                if i < len(agents_to_use) - 1:
                    time.sleep(delay_between_agents)

            except Exception as e:
                responses[agent_id] = f"[Erro ao consultar {self.agents[agent_id]['name']}: {str(e)}]"

        # Synthesize final recommendation
        if progress_callback:
            progress_callback({
                'status': 'synthesizing',
                'agent': 'Conselho Completo',
                'progress': 95
            })

        # Format the final response
        final_response = self._format_council_response(responses, language)

        if progress_callback:
            progress_callback({
                'status': 'complete',
                'progress': 100
            })

        return final_response

    def _format_council_response(self, responses: Dict[str, str], language: str = 'pt') -> str:
        """Format all agent responses into a cohesive council recommendation"""

        header = "# Conselho de Mentoria DJ/Produtor\n\n" if language == 'pt' else "# DJ/Producer Mentor Council\n\n"

        formatted = header

        for agent_id, response in responses.items():
            agent = self.agents[agent_id]
            formatted += f"## {agent['name']}\n"
            formatted += f"*{agent['role']}*\n\n"
            formatted += f"{response}\n\n"
            formatted += "---\n\n"

        return formatted

    def generate_summary(self, prompt: str) -> str:
        """
        Generate a concise summary using Claude API

        Args:
            prompt: The prompt with conversation to summarize

        Returns:
            Summary text
        """
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=500,  # Keep summaries short
                system="Você é um assistente especializado em criar resumos concisos e acionáveis de conversas de mentoria. Foque nos pontos principais e conselhos práticos.",
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            return response.content[0].text

        except Exception as e:
            raise Exception(f"Erro ao gerar resumo: {str(e)}")
