"""Multi-agent orchestration with LangGraph: router → retrieval → KB analyst → final prompt."""

from __future__ import annotations

import os
from typing import Literal, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

from .knowledge_store import get_knowledge_store

CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")

CHAT_SYSTEM_PROMPT = """
You are an enterprise customer support AI assistant for a B2B software or services vendor. You help
customers—often IT, security, finance, procurement, and operations—with account questions such as
billing and invoices, plans and usage limits, SSO/SCIM and access, API keys and rate limits,
onboarding, feature availability, documentation pointers, and how to escalate to support or a
customer success manager.

Tone: professional, concise, calm, and respectful of urgency (renewals, outages, compliance
deadlines). Use clear language. You do not have access to private contracts, ticket queues, or
internal systems: never invent specific SLA percentages, pricing, legal terms, case numbers, or
commitments. When an answer depends on account data or a signed agreement, say what is typically
needed and direct them to their account team, official support portal, or legal/finance contacts.

If the user describes an active security incident, suspected breach, or data exposure, advise them
to use the vendor's security or abuse channel and their own incident response process immediately;
keep guidance high-level and brief.

If a question is outside B2B customer support (e.g. personal medical or unrelated consumer topics),
politely note your scope and suggest appropriate resources.

When "Retrieved knowledge base notes" are provided, ground answers in them for facts and procedures
stated there. If the notes do not contain the answer, say so and fall back to general guidance.

Remind users occasionally (not every message) that replies are AI-assisted and may not reflect the
latest policy; authoritative answers come from their contract and vendor communications.

Keep replies concise unless the user asks for detail. Short Markdown (lists, **bold**) is fine when
it helps readability.
""".strip()

ROUTER_SYSTEM = """You are the routing agent for an enterprise support desk.
Choose exactly one route:
- "general": best answered with standard enterprise support practices; uploaded internal docs unlikely needed.
- "kb": the user likely needs specifics from uploaded runbooks, policies, FAQs, or product docs.
- "hybrid": combine general support framing with uploaded material.

Base your decision only on the latest user message (and brief context is the raw message)."""


class RouteDecision(BaseModel):
    route: Literal["general", "kb", "hybrid"] = Field(description="Which orchestration path to use")


class AgentState(TypedDict, total=False):
    messages: list[dict]
    user_id: str
    route: str
    retrieved_chunks: list[str]
    kb_notes: str
    final_lc_messages: list[BaseMessage]


def _last_user_text(messages: list[dict]) -> str:
    for m in reversed(messages):
        if m.get("role") == "user":
            return str(m.get("content", "")).strip()
    return ""


def supervisor_node(state: AgentState) -> dict:
    last = _last_user_text(state["messages"])
    llm = ChatOpenAI(model=CHAT_MODEL, temperature=0)
    structured = llm.with_structured_output(RouteDecision)
    out: RouteDecision = structured.invoke(
        [
            SystemMessage(content=ROUTER_SYSTEM),
            HumanMessage(content=last or "(empty)"),
        ],
    )
    return {"route": out.route}


def retrieve_node(state: AgentState) -> dict:
    route = state.get("route") or "general"
    user_id = state["user_id"]
    last = _last_user_text(state["messages"])
    kb = get_knowledge_store()
    if route == "general" or kb.chunk_count(user_id) == 0:
        return {"retrieved_chunks": []}
    docs = kb.similarity_search(user_id, last, k=6)
    return {"retrieved_chunks": [d.page_content for d in docs]}


KB_ANALYST_SYSTEM = """You are the knowledge-base analyst agent. You receive raw excerpts from the customer's
uploaded documents. Produce a tight bullet list (max 8 bullets) of facts, procedures, thresholds, and links
implied in the text that the support agent should use. If excerpts are empty or irrelevant, output a single line:
"No usable excerpts for this question."""


def kb_analyst_node(state: AgentState) -> dict:
    chunks = state.get("retrieved_chunks") or []
    if not chunks:
        return {"kb_notes": "No knowledge base excerpts retrieved."}
    body = "\n\n---\n\n".join(chunks[:12])
    llm = ChatOpenAI(model=CHAT_MODEL, temperature=0)
    msg = llm.invoke(
        [
            SystemMessage(content=KB_ANALYST_SYSTEM),
            HumanMessage(content=f"User question:\n{_last_user_text(state['messages'])}\n\nExcerpts:\n{body}"),
        ],
    )
    notes = msg.content if isinstance(msg.content, str) else str(msg.content)
    return {"kb_notes": notes.strip()}


def _dict_messages_to_lc(messages: list[dict]) -> list[BaseMessage]:
    out: list[BaseMessage] = []
    for m in messages:
        role = m.get("role")
        content = str(m.get("content", ""))
        if role == "user":
            out.append(HumanMessage(content=content))
        elif role == "assistant":
            out.append(AIMessage(content=content))
    return out


def prepare_node(state: AgentState) -> dict:
    notes = (state.get("kb_notes") or "").strip()
    sys_parts = [CHAT_SYSTEM_PROMPT]
    if notes:
        sys_parts.append("\n\n## Retrieved knowledge base notes (from multi-agent KB analyst)\n")
        sys_parts.append(notes)
    system = "".join(sys_parts)
    conv = _dict_messages_to_lc(state["messages"])
    final: list[BaseMessage] = [SystemMessage(content=system), *conv]
    return {"final_lc_messages": final}


def build_support_graph():
    g = StateGraph(AgentState)
    g.add_node("supervisor", supervisor_node)
    g.add_node("retrieve", retrieve_node)
    g.add_node("kb_analyst", kb_analyst_node)
    g.add_node("prepare", prepare_node)
    g.set_entry_point("supervisor")
    g.add_edge("supervisor", "retrieve")
    g.add_edge("retrieve", "kb_analyst")
    g.add_edge("kb_analyst", "prepare")
    g.add_edge("prepare", END)
    return g.compile()


_compiled_graph = None


def get_support_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_support_graph()
    return _compiled_graph


def run_orchestration(user_id: str, messages: list[dict]) -> list[BaseMessage]:
    graph = get_support_graph()
    out = graph.invoke({"messages": messages, "user_id": user_id})
    return out.get("final_lc_messages") or []
