"""LangGraph workflow orchestration for decision evaluation."""
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END

from src.models.schemas import ContextAnalysis, ProposerOutput
from src.agents.context_analyzer import ContextAnalyzerAgent
from src.agents.proposer import ProposerAgent


class DecisionState(TypedDict):
    """State schema for decision evaluation workflow."""
    decision: str
    context: Optional[str]
    context_analysis: Optional[ContextAnalysis]
    proposer_output: Optional[ProposerOutput]


class DecisionWorkflow:
    """LangGraph-based workflow for decision evaluation."""

    def __init__(self):
        """Initialize workflow with agents."""
        self.context_analyzer = ContextAnalyzerAgent()
        self.proposer = ProposerAgent()
        self.graph = self._build_graph()

    def _analyze_context(self, state: DecisionState) -> DecisionState:
        """Node: Run Context Analyzer."""
        context_analysis = self.context_analyzer.analyze(
            decision=state["decision"],
            context=state.get("context", "") or ""
        )
        state["context_analysis"] = context_analysis
        return state

    def _propose_recommendation(self, state: DecisionState) -> DecisionState:
        """Node: Run Proposer Agent."""
        proposer_output = self.proposer.propose(
            decision=state["decision"],
            context=state.get("context", "") or "",
            context_analysis=state["context_analysis"]
        )
        state["proposer_output"] = proposer_output
        return state

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        # Create graph
        workflow = StateGraph(DecisionState)

        # Add nodes
        workflow.add_node("context_analyzer", self._analyze_context)
        workflow.add_node("proposer", self._propose_recommendation)

        # Define edges
        workflow.set_entry_point("context_analyzer")
        workflow.add_edge("context_analyzer", "proposer")
        workflow.add_edge("proposer", END)

        # Compile graph
        return workflow.compile()

    def run(self, decision: str, context: Optional[str] = None) -> DecisionState:
        """
        Execute the full decision evaluation workflow.

        Args:
            decision: The decision statement
            context: Optional user-provided context

        Returns:
            Final state with all agent outputs
        """
        initial_state: DecisionState = {
            "decision": decision,
            "context": context,
            "context_analysis": None,
            "proposer_output": None
        }

        final_state = self.graph.invoke(initial_state)
        return final_state
