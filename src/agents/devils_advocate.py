"""Devil's Advocate agent implementation."""
import instructor
from langfuse.openai import OpenAI  # Langfuse wrapper for automatic tracking
import os
from dotenv import load_dotenv

from src.models.schemas import DevilsAdvocateOutput, ContextAnalysis, ProposerOutput

load_dotenv()


class DevilsAdvocateAgent:
    """Agent that systematically challenges recommendations across four attack dimensions."""

    def __init__(self):
        """Initialize the Devil's Advocate with OpenAI client."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        self.client = instructor.from_openai(OpenAI(api_key=api_key))
        self.model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

    def critique(
        self,
        decision: str,
        context: str,
        context_analysis: ContextAnalysis,
        proposer_output: ProposerOutput
    ) -> DevilsAdvocateOutput:
        """
        Generate systematic critique of the Proposer's recommendation.

        Args:
            decision: The decision statement
            context: User-provided context (may be empty)
            context_analysis: Output from Context Analyzer
            proposer_output: Output from Proposer Agent

        Returns:
            DevilsAdvocateOutput with counterarguments, failure scenarios, and risk breakdown
        """
        prompt = self._build_prompt(decision, context, context_analysis, proposer_output)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": """You are a Devil's Advocate agent that systematically challenges recommendations.

CRITICAL RULES:
- Attack the recommendation across ALL FOUR dimensions: Execution Risk, Market & Customer Impact, Reputational Downside, Opportunity Cost
- Generate SPECIFIC counterarguments, not generic concerns
- Create CONCRETE failure scenarios with clear triggers
- Flag UNVERIFIED assumptions as high-risk
- Assign risk scores (0-10) based on context completeness and assumption quality
- DO NOT soften critique with phrases like "however", "on the other hand", or "to be fair"
- Be ruthlessly critical - your job is to expose weaknesses, not balance perspectives
- Lower context completeness = higher execution risk scores"""
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_model=DevilsAdvocateOutput,
            temperature=0
        )

        return response

    def _build_prompt(
        self,
        decision: str,
        context: str,
        context_analysis: ContextAnalysis,
        proposer_output: ProposerOutput
    ) -> str:
        """Build the prompt for the Devil's Advocate."""
        # Format Proposer's assumptions
        assumptions_text = "\n".join(
            f"  - {a.statement} (basis: {a.basis}, risk: {a.risk_level})"
            for a in proposer_output.assumptions
        )

        # Format missing context
        missing_ctx = "\n".join(f"  - {ctx}" for ctx in context_analysis.missing_context) if context_analysis.missing_context else "  None"

        prompt = f"""Systematically challenge this recommendation across ALL FOUR attack dimensions.

DECISION:
{decision}

PROVIDED CONTEXT:
{context if context else "No context provided"}

CONTEXT COMPLETENESS: {context_analysis.completeness_score}/100

MISSING CONTEXT:
{missing_ctx}

PROPOSER'S RECOMMENDATION:
{proposer_output.recommendation}

PROPOSER'S CONFIDENCE: {proposer_output.confidence}/100

PROPOSER'S ASSUMPTIONS:
{assumptions_text}

PROPOSER'S JUSTIFICATION:
{proposer_output.justification}

YOUR TASK:
Attack this recommendation across ALL FOUR dimensions:

1. EXECUTION RISK (0-10): What could fail technically?
   - Challenge assumptions about implementation
   - Identify technical failure modes
   - Consider dependency failures, integration issues, timing problems
   - Higher score if context completeness is low (<50%)

2. MARKET & CUSTOMER IMPACT (0-10): Who gets hurt if this goes wrong?
   - Identify customer segments at risk
   - Consider competitive dynamics
   - Assess market reaction scenarios
   - Think about customer trust erosion

3. REPUTATIONAL DOWNSIDE (0-10): What's the narrative if this fails publicly?
   - How would media/social media frame this failure?
   - What's the worst-case PR scenario?
   - Consider stakeholder perception shifts
   - Think about long-term brand damage

4. OPPORTUNITY COST (0-10): What else could be done with this time/effort?
   - What alternatives are being ignored?
   - What's the cost of delay on other priorities?
   - Consider resource allocation trade-offs
   - Assess relative value vs. other options

REQUIRED OUTPUT:
- counterarguments: At least 1 per attack dimension (minimum 4 total), directly challenging the Proposer
- failure_scenarios: At least 3 specific scenarios with clear triggers and severity
- high_risk_assumptions: Flag any Proposer assumptions that are UNVERIFIED or HIGH-RISK
- risk_breakdown: Score all four dimensions 0-10

REMEMBER:
- Be ruthlessly critical, not balanced
- No softening language
- Specific scenarios, not generic concerns
- Tag unverified assumptions clearly"""

        return prompt
