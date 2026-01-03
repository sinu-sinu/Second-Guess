"""Judge agent implementation."""
import instructor
from openai import OpenAI
import os
from dotenv import load_dotenv

from src.models.schemas import JudgeOutput, ContextAnalysis, ProposerOutput, DevilsAdvocateOutput

load_dotenv()


class JudgeAgent:
    """Agent that evaluates reasoning quality of both Proposer and Devil's Advocate."""

    def __init__(self):
        """Initialize the Judge with OpenAI client."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        self.client = instructor.from_openai(OpenAI(api_key=api_key))
        self.model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

    def evaluate(
        self,
        decision: str,
        context: str,
        context_analysis: ContextAnalysis,
        proposer_output: ProposerOutput,
        devils_advocate_output: DevilsAdvocateOutput
    ) -> JudgeOutput:
        """
        Evaluate reasoning quality of both Proposer and Devil's Advocate.

        Args:
            decision: The decision statement
            context: User-provided context (may be empty)
            context_analysis: Output from Context Analyzer
            proposer_output: Output from Proposer Agent
            devils_advocate_output: Output from Devil's Advocate Agent

        Returns:
            JudgeOutput with strength scores, weak claims, unsupported claims, and reasoning assessment
        """
        prompt = self._build_prompt(decision, context, context_analysis, proposer_output, devils_advocate_output)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": """You are a Judge agent that evaluates reasoning quality neutrally and objectively.

CRITICAL RULES:
- Evaluate BOTH Proposer and Devil's Advocate for reasoning quality
- DO NOT favor either side based on their conclusion—evaluate logic, specificity, and evidence
- Assign strength scores (0-10) based on:
  * Logical consistency: are arguments internally coherent?
  * Specificity vs vagueness: are claims concrete or generic?
  * Evidence support: are claims backed by provided context?
  * Overconfidence detection: are claims made beyond available evidence?
- Identify WEAK claims (vague like "things could go wrong" vs specific like "auth service could fail under load")
- Identify UNSUPPORTED claims (not backed by provided context)
- Be neutral—your job is to assess reasoning quality, not pick a winner
- High-quality arguments with specific, evidence-backed claims get higher scores
- Vague, generic, or unsupported arguments get lower scores"""
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_model=JudgeOutput,
            temperature=0
        )

        return response

    def _build_prompt(
        self,
        decision: str,
        context: str,
        context_analysis: ContextAnalysis,
        proposer_output: ProposerOutput,
        devils_advocate_output: DevilsAdvocateOutput
    ) -> str:
        """Build the prompt for the Judge."""
        # Format Proposer's assumptions
        proposer_assumptions = "\n".join(
            f"  - {a.statement} (basis: {a.basis}, risk: {a.risk_level})"
            for a in proposer_output.assumptions
        )

        # Format Devil's Advocate counterarguments
        advocate_counterargs = "\n".join(
            f"  - {arg}"
            for arg in devils_advocate_output.counterarguments
        )

        # Format failure scenarios
        failure_scenarios_text = "\n".join(
            f"  - {fs.description} (trigger: {fs.trigger}, severity: {fs.impact_severity})"
            for fs in devils_advocate_output.failure_scenarios
        )

        # Format high-risk assumptions
        high_risk_text = "\n".join(
            f"  - {hra}"
            for hra in devils_advocate_output.high_risk_assumptions
        ) if devils_advocate_output.high_risk_assumptions else "  None"

        # Format provided context
        provided_ctx = "\n".join(
            f"  - {ctx}"
            for ctx in context_analysis.provided_context
        ) if context_analysis.provided_context else "  None"

        prompt = f"""Evaluate the reasoning quality of BOTH the Proposer and Devil's Advocate.

DECISION:
{decision}

PROVIDED CONTEXT:
{context if context else "No context provided"}

CONTEXT AVAILABLE (from Context Analyzer):
{provided_ctx}

CONTEXT COMPLETENESS: {context_analysis.completeness_score}/100

---

PROPOSER'S CASE:
Recommendation: {proposer_output.recommendation}
Confidence: {proposer_output.confidence}/100

Assumptions:
{proposer_assumptions}

Justification:
{proposer_output.justification}

---

DEVIL'S ADVOCATE'S CASE:
Counterarguments:
{advocate_counterargs}

Failure Scenarios:
{failure_scenarios_text}

High-Risk Assumptions Flagged:
{high_risk_text}

Risk Breakdown:
- Execution: {devils_advocate_output.risk_breakdown.execution}/10
- Market & Customer: {devils_advocate_output.risk_breakdown.market_customer}/10
- Reputational: {devils_advocate_output.risk_breakdown.reputational}/10
- Opportunity Cost: {devils_advocate_output.risk_breakdown.opportunity_cost}/10

---

YOUR TASK:
Evaluate BOTH sides for reasoning quality:

1. LOGICAL CONSISTENCY
   - Are arguments internally coherent?
   - Do they contradict themselves?
   - Do conclusions follow from premises?

2. SPECIFICITY vs VAGUENESS
   - Specific: "Auth service could fail under 10k concurrent users based on load test results"
   - Vague: "Things could go wrong" or "There might be issues"
   - Penalize vague claims, reward specific ones

3. EVIDENCE SUPPORT
   - Are claims backed by the provided context?
   - Are assumptions clearly stated vs hidden?
   - Are claims made beyond available evidence (overconfidence)?

4. OVERCONFIDENCE DETECTION
   - Given completeness score of {context_analysis.completeness_score}%, are confidence levels appropriate?
   - Low context (<50%) with high confidence (>70%) is a red flag
   - Are strong claims made without supporting evidence?

OUTPUT REQUIREMENTS:
- proposer_strength: 0-10 score for Proposer's reasoning quality
- advocate_strength: 0-10 score for Devil's Advocate's reasoning quality
- weak_claims: Identify vague, generic, or poorly reasoned claims from EITHER side
  * Each weak claim must specify source ("proposer" or "advocate")
  * Minimum 1 weak claim if context completeness < 50%
- unsupported_claims: Identify claims not backed by provided context
  * Each unsupported claim must specify source ("proposer" or "advocate")
  * Check if assumptions/arguments reference context that wasn't actually provided
- reasoning_assessment: 2-3 sentence overall assessment of reasoning quality from both sides

REMEMBER:
- You are NEUTRAL—evaluate reasoning quality, not which side you agree with
- A well-reasoned argument you disagree with should score high
- A poorly-reasoned argument you agree with should score low
- Specific > Vague, Evidence-backed > Unsupported"""

        return prompt
