"""LangGraph workflow orchestration for decision evaluation."""
from typing import TypedDict, Optional
import time
from langgraph.graph import StateGraph, END

from src.models.schemas import ContextAnalysis, ProposerOutput, DevilsAdvocateOutput, JudgeOutput, ConfidenceOutput
from src.agents.context_analyzer import ContextAnalyzerAgent
from src.agents.proposer import ProposerAgent
from src.agents.devils_advocate import DevilsAdvocateAgent
from src.agents.judge import JudgeAgent
from src.agents.confidence_estimator import ConfidenceEstimatorAgent
from src.observability.langfuse_client import get_langfuse


class DecisionState(TypedDict):
    """State schema for decision evaluation workflow."""
    decision: str
    context: Optional[str]
    context_analysis: Optional[ContextAnalysis]
    proposer_output: Optional[ProposerOutput]
    devils_advocate_output: Optional[DevilsAdvocateOutput]
    judge_output: Optional[JudgeOutput]
    confidence_output: Optional[ConfidenceOutput]
    final_recommendation: Optional[str]
    # Tracing metadata
    trace_id: Optional[str]
    decision_id: Optional[str]
    version: Optional[int]


class DecisionWorkflow:
    """LangGraph-based workflow for decision evaluation."""

    def __init__(self):
        """Initialize workflow with agents."""
        self.context_analyzer = ContextAnalyzerAgent()
        self.proposer = ProposerAgent()
        self.devils_advocate = DevilsAdvocateAgent()
        self.judge = JudgeAgent()
        self.confidence_estimator = ConfidenceEstimatorAgent()
        self.graph = self._build_graph()

    def _analyze_context(self, state: DecisionState) -> DecisionState:
        """Node: Run Context Analyzer."""
        start_time = time.time()
        langfuse = get_langfuse()

        # Create span if tracing is enabled
        span = None
        if langfuse and state.get("trace_id"):
            span = langfuse.span(
                trace_id=state["trace_id"],
                name="context_analyzer",
                input={
                    "decision": state["decision"],
                    "context": state.get("context", "")
                },
                metadata={"agent": "context_analyzer", "prompt_version": "v1.0"}
            )

        # Run agent
        context_analysis = self.context_analyzer.analyze(
            decision=state["decision"],
            context=state.get("context", "") or ""
        )
        state["context_analysis"] = context_analysis

        # Update span with output
        if span:
            latency_ms = (time.time() - start_time) * 1000
            span.end(
                output={
                    "decision_type": context_analysis.decision_type,
                    "completeness_score": context_analysis.completeness_score,
                    "missing_context": context_analysis.missing_context
                },
                metadata={"latency_ms": latency_ms}
            )

        return state

    def _propose_recommendation(self, state: DecisionState) -> DecisionState:
        """Node: Run Proposer Agent."""
        start_time = time.time()
        langfuse = get_langfuse()

        # Create span if tracing is enabled
        span = None
        if langfuse and state.get("trace_id"):
            span = langfuse.span(
                trace_id=state["trace_id"],
                name="proposer",
                input={
                    "decision": state["decision"],
                    "context": state.get("context", ""),
                    "completeness_score": state["context_analysis"].completeness_score
                },
                metadata={"agent": "proposer", "prompt_version": "v1.0"}
            )

        # Run agent
        proposer_output = self.proposer.propose(
            decision=state["decision"],
            context=state.get("context", "") or "",
            context_analysis=state["context_analysis"]
        )
        state["proposer_output"] = proposer_output

        # Update span with output
        if span:
            latency_ms = (time.time() - start_time) * 1000
            span.end(
                output={
                    "recommendation": proposer_output.recommendation,
                    "confidence": proposer_output.confidence,
                    "assumptions_count": len(proposer_output.assumptions)
                },
                metadata={"latency_ms": latency_ms}
            )

        return state

    def _critique_recommendation(self, state: DecisionState) -> DecisionState:
        """Node: Run Devil's Advocate Agent."""
        start_time = time.time()
        langfuse = get_langfuse()

        # Create span if tracing is enabled
        span = None
        if langfuse and state.get("trace_id"):
            span = langfuse.span(
                trace_id=state["trace_id"],
                name="devils_advocate",
                input={
                    "decision": state["decision"],
                    "proposer_recommendation": state["proposer_output"].recommendation,
                    "proposer_confidence": state["proposer_output"].confidence
                },
                metadata={"agent": "devils_advocate", "prompt_version": "v1.0"}
            )

        # Run agent
        devils_advocate_output = self.devils_advocate.critique(
            decision=state["decision"],
            context=state.get("context", "") or "",
            context_analysis=state["context_analysis"],
            proposer_output=state["proposer_output"]
        )
        state["devils_advocate_output"] = devils_advocate_output

        # Update span with output
        if span:
            latency_ms = (time.time() - start_time) * 1000
            span.end(
                output={
                    "counterarguments_count": len(devils_advocate_output.counterarguments),
                    "failure_scenarios_count": len(devils_advocate_output.failure_scenarios),
                    "execution_risk": devils_advocate_output.risk_breakdown.execution
                },
                metadata={"latency_ms": latency_ms}
            )

        return state

    def _evaluate_reasoning(self, state: DecisionState) -> DecisionState:
        """Node: Run Judge Agent."""
        start_time = time.time()
        langfuse = get_langfuse()

        # Create span if tracing is enabled
        span = None
        if langfuse and state.get("trace_id"):
            span = langfuse.span(
                trace_id=state["trace_id"],
                name="judge",
                input={
                    "decision": state["decision"],
                    "proposer_confidence": state["proposer_output"].confidence,
                    "completeness_score": state["context_analysis"].completeness_score
                },
                metadata={"agent": "judge", "prompt_version": "v1.0"}
            )

        # Run agent
        judge_output = self.judge.evaluate(
            decision=state["decision"],
            context=state.get("context", "") or "",
            context_analysis=state["context_analysis"],
            proposer_output=state["proposer_output"],
            devils_advocate_output=state["devils_advocate_output"]
        )
        state["judge_output"] = judge_output

        # Update span with output
        if span:
            latency_ms = (time.time() - start_time) * 1000
            span.end(
                output={
                    "proposer_strength": judge_output.proposer_strength,
                    "advocate_strength": judge_output.advocate_strength,
                    "weak_claims_count": len(judge_output.weak_claims),
                    "unsupported_claims_count": len(judge_output.unsupported_claims)
                },
                metadata={"latency_ms": latency_ms}
            )

        return state

    def _estimate_confidence(self, state: DecisionState) -> DecisionState:
        """Node: Run Confidence Estimator Agent."""
        start_time = time.time()
        langfuse = get_langfuse()

        # Create span if tracing is enabled
        span = None
        if langfuse and state.get("trace_id"):
            span = langfuse.span(
                trace_id=state["trace_id"],
                name="confidence_estimator",
                input={
                    "initial_confidence": state["proposer_output"].confidence,
                    "completeness_score": state["context_analysis"].completeness_score,
                    "execution_risk": state["devils_advocate_output"].risk_breakdown.execution
                },
                metadata={"agent": "confidence_estimator", "version": "v1.0"}
            )

        # Run agent
        confidence_output = self.confidence_estimator.estimate(
            context_analysis=state["context_analysis"],
            proposer_output=state["proposer_output"],
            devils_advocate_output=state["devils_advocate_output"],
            judge_output=state["judge_output"]
        )
        state["confidence_output"] = confidence_output

        # Generate final recommendation
        final_recommendation = self.confidence_estimator.generate_final_recommendation(
            confidence_output=confidence_output,
            proposer_output=state["proposer_output"],
            devils_advocate_output=state["devils_advocate_output"],
            context_analysis=state["context_analysis"]
        )
        state["final_recommendation"] = final_recommendation

        # Update span with output and log custom metrics
        if span:
            latency_ms = (time.time() - start_time) * 1000
            span.end(
                output={
                    "adjusted_confidence": confidence_output.adjusted_confidence,
                    "confidence_delta": confidence_output.delta,
                    "penalties_count": len(confidence_output.penalties),
                    "final_recommendation": final_recommendation.split("\n")[0]  # First line only
                },
                metadata={"latency_ms": latency_ms}
            )

            # Log custom metrics/scores
            if state.get("trace_id"):
                langfuse.score(
                    trace_id=state["trace_id"],
                    name="context_completeness",
                    value=state["context_analysis"].completeness_score / 100.0  # Normalize to 0-1
                )
                langfuse.score(
                    trace_id=state["trace_id"],
                    name="adjusted_confidence",
                    value=confidence_output.adjusted_confidence / 100.0  # Normalize to 0-1
                )
                langfuse.score(
                    trace_id=state["trace_id"],
                    name="confidence_delta",
                    value=confidence_output.delta / 100.0  # Can be negative
                )

        return state

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        # Create graph
        workflow = StateGraph(DecisionState)

        # Add nodes
        workflow.add_node("context_analyzer", self._analyze_context)
        workflow.add_node("proposer", self._propose_recommendation)
        workflow.add_node("devils_advocate", self._critique_recommendation)
        workflow.add_node("judge", self._evaluate_reasoning)
        workflow.add_node("confidence_estimator", self._estimate_confidence)

        # Define edges
        workflow.set_entry_point("context_analyzer")
        workflow.add_edge("context_analyzer", "proposer")
        workflow.add_edge("proposer", "devils_advocate")
        workflow.add_edge("devils_advocate", "judge")
        workflow.add_edge("judge", "confidence_estimator")
        workflow.add_edge("confidence_estimator", END)

        # Compile graph
        return workflow.compile()

    def run(
        self,
        decision: str,
        context: Optional[str] = None,
        decision_id: Optional[str] = None,
        version: Optional[int] = None
    ) -> DecisionState:
        """
        Execute the full decision evaluation workflow.

        Args:
            decision: The decision statement
            context: Optional user-provided context
            decision_id: Optional decision ID for tracing
            version: Optional version number for tracing

        Returns:
            Final state with all agent outputs
        """
        langfuse = get_langfuse()
        trace_id = None

        # Create parent trace if Langfuse is enabled
        if langfuse:
            metadata = {}
            if decision_id:
                metadata["decision_id"] = decision_id
            if version:
                metadata["version"] = version

            try:
                trace = langfuse.trace(
                    name="decision_evaluation",
                    input={"decision": decision, "context": context},
                    metadata=metadata
                )
                trace_id = trace.id
            except Exception as e:
                print(f"[WARNING] Failed to create Langfuse trace: {e}")

        initial_state: DecisionState = {
            "decision": decision,
            "context": context,
            "context_analysis": None,
            "proposer_output": None,
            "devils_advocate_output": None,
            "judge_output": None,
            "confidence_output": None,
            "final_recommendation": None,
            "trace_id": trace_id,
            "decision_id": decision_id,
            "version": version
        }

        final_state = self.graph.invoke(initial_state)

        # Update trace with final output
        if langfuse and trace_id:
            try:
                langfuse.trace(
                    id=trace_id,
                    output={
                        "final_recommendation": final_state.get("final_recommendation"),
                        "adjusted_confidence": final_state.get("confidence_output").adjusted_confidence if final_state.get("confidence_output") else None,
                        "context_completeness": final_state.get("context_analysis").completeness_score if final_state.get("context_analysis") else None
                    }
                )
                # Flush to ensure data is sent
                langfuse.flush()
            except Exception as e:
                print(f"[WARNING] Failed to update Langfuse trace: {e}")

        return final_state
