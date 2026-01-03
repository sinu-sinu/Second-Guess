"""Proposer agent implementation."""
import instructor
from openai import OpenAI
import os
from dotenv import load_dotenv

from src.models.schemas import ProposerOutput, ContextAnalysis

load_dotenv()


class ProposerAgent:
    """Agent that generates initial recommendations based on context analysis."""

    def __init__(self):
        """Initialize the Proposer with OpenAI client."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        self.client = instructor.from_openai(OpenAI(api_key=api_key))
        self.model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

    def propose(self, decision: str, context: str, context_analysis: ContextAnalysis) -> ProposerOutput:
        """
        Generate recommendation based on provided context.

        Args:
            decision: The decision statement
            context: User-provided context (may be empty)
            context_analysis: Output from Context Analyzer

        Returns:
            ProposerOutput with recommendation, assumptions, and confidence
        """
        prompt = self._build_prompt(decision, context, context_analysis)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": """You are an evaluation agent that generates recommendations based ONLY on provided context.

CRITICAL RULES:
- Use ONLY the provided context to make your recommendation
- Make ALL assumptions explicit - list what you're assuming is true
- DO NOT ask clarifying questions
- DO NOT use conversational phrases like "It seems like..." or "I think..."
- Use evaluative language: "Given provided context..." or "Based on available information..."
- Be directive: recommend "proceed", "delay", or "conditional" (with conditions)
- Assign confidence based on context completeness
- For each assumption, explain what it's based on and the risk if wrong"""
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_model=ProposerOutput,
            temperature=0
        )

        return response

    def _build_prompt(self, decision: str, context: str, context_analysis: ContextAnalysis) -> str:
        """Build the prompt for the Proposer."""
        # Format provided context
        provided_ctx = "\n".join(f"  - {ctx}" for ctx in context_analysis.provided_context) if context_analysis.provided_context else "  None"

        # Format missing context
        missing_ctx = "\n".join(f"  - {ctx}" for ctx in context_analysis.missing_context) if context_analysis.missing_context else "  None"

        prompt = f"""Evaluate this decision and provide a recommendation based ONLY on the provided context.

DECISION:
{decision}

PROVIDED CONTEXT:
{context if context else "No context provided"}

CONTEXT ANALYSIS:
- Decision Type: {context_analysis.decision_type}
- Completeness Score: {context_analysis.completeness_score}/100

CONTEXT AVAILABLE:
{provided_ctx}

CONTEXT MISSING:
{missing_ctx}

INSTRUCTIONS:
1. Generate a recommendation: "proceed", "delay", or "conditional: [specific conditions]"
2. List ALL assumptions you are making (minimum 2 if any context is missing)
   - For each assumption: state it clearly, explain its basis, assess risk level (low/medium/high)
3. Assign confidence (0-100) based on context completeness and assumption risk
4. Provide justification based ONLY on available context

Remember:
- Be evaluative, not conversational
- Make assumptions explicit
- Base confidence on completeness score and assumption risk
- Low completeness (<50) should have multiple assumptions and lower confidence
- High completeness (>80) may have few/no assumptions and higher confidence"""

        return prompt
