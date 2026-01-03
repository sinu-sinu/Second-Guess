"""Context Analyzer agent implementation."""
from typing import List
import instructor
from openai import OpenAI
from pydantic import Field
import os
from dotenv import load_dotenv

from src.models.schemas import ContextAnalysis

load_dotenv()


class ContextAnalyzerAgent:
    """Agent that analyzes decision context completeness."""

    # Decision type context requirements mapping
    DECISION_TYPE_CONTEXTS = {
        "launch": [
            "deployment readiness",
            "rollback plan",
            "system stability verification",
            "customer impact analysis",
            "team capacity and availability",
            "monitoring and alerting setup"
        ],
        "pricing": [
            "competitive analysis",
            "cost structure",
            "target customer segment",
            "revenue impact model",
            "customer churn risk assessment",
            "market positioning strategy"
        ],
        "hiring": [
            "current team capacity",
            "budget and runway",
            "role requirements and urgency",
            "onboarding capacity",
            "hiring timeline",
            "team growth impact"
        ],
        "technical": [
            "technical requirements",
            "implementation complexity",
            "technical debt implications",
            "resource requirements",
            "testing strategy",
            "rollback and failure recovery"
        ],
        "market_entry": [
            "market size and opportunity",
            "competitive landscape",
            "customer acquisition strategy",
            "resource requirements",
            "timeline and milestones",
            "risk assessment"
        ]
    }

    def __init__(self):
        """Initialize the Context Analyzer with OpenAI client."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        self.client = instructor.from_openai(OpenAI(api_key=api_key))
        self.model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

    def _classify_decision_type(self, decision: str, context: str = "") -> str:
        """Classify the decision type based on decision statement and context."""
        prompt = f"""Classify the following business decision into ONE of these types:
- launch: Decisions about launching, releasing, or deploying products/features
- pricing: Decisions about pricing strategy, monetization, or cost changes
- hiring: Decisions about hiring, team expansion, or headcount
- technical: Decisions about technical implementation, architecture, or infrastructure
- market_entry: Decisions about entering new markets or segments

Decision: {decision}
Context: {context if context else 'None provided'}

Return ONLY the decision type (one word: launch, pricing, hiring, technical, or market_entry)."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_model=None,
            temperature=0
        )

        decision_type = response.choices[0].message.content.strip().lower()

        # Validate and default to technical if unclear
        if decision_type not in self.DECISION_TYPE_CONTEXTS:
            decision_type = "technical"

        return decision_type

    def _extract_provided_context(self, decision: str, context: str, required_context: List[str]) -> List[str]:
        """Extract which required context dimensions are present in user input."""
        if not context:
            return []

        prompt = f"""Given a decision and user-provided context, identify which required context dimensions are addressed.

Decision: {decision}
User Context: {context}

Required Context Dimensions:
{chr(10).join(f'- {rc}' for rc in required_context)}

For each required dimension, determine if the user's context addresses it (even partially).
Return ONLY a JSON array of the dimension names that are addressed.

Example: ["system stability verification", "rollback plan"]"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_model=None,
            temperature=0
        )

        # Parse response - expecting JSON array
        try:
            import json
            provided = json.loads(response.choices[0].message.content.strip())
            # Validate that items are in required_context
            return [p for p in provided if p in required_context]
        except:
            # Fallback: simple keyword matching
            provided = []
            context_lower = context.lower()
            for req in required_context:
                # Check if key terms from requirement appear in context
                req_terms = req.lower().split()
                if any(term in context_lower for term in req_terms if len(term) > 3):
                    provided.append(req)
            return provided

    def _calculate_completeness_score(self, provided: List[str], required: List[str]) -> int:
        """Calculate context completeness score (0-100)."""
        if not required:
            return 100

        score = int((len(provided) / len(required)) * 100)
        return max(0, min(100, score))  # Clamp to 0-100

    def analyze(self, decision: str, context: str = "") -> ContextAnalysis:
        """
        Analyze decision context completeness.

        Args:
            decision: The decision statement
            context: Optional user-provided context

        Returns:
            ContextAnalysis with completeness scoring
        """
        # Step 1: Classify decision type
        decision_type = self._classify_decision_type(decision, context or "")

        # Step 2: Get required context for this decision type
        required_context = self.DECISION_TYPE_CONTEXTS[decision_type]

        # Step 3: Extract which required contexts are provided
        provided_context = self._extract_provided_context(decision, context or "", required_context)

        # Step 4: Determine missing context
        missing_context = [rc for rc in required_context if rc not in provided_context]

        # Step 5: Calculate completeness score
        completeness_score = self._calculate_completeness_score(provided_context, required_context)

        return ContextAnalysis(
            decision_type=decision_type,
            required_context=required_context,
            provided_context=provided_context,
            missing_context=missing_context,
            completeness_score=completeness_score
        )
