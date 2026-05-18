"""
Mode 1 – AI coworker chat orchestration.
Runs the Claude agent loop with CMMS + calculation + standards tools.
"""
import anthropic
from sqlalchemy.orm import Session

from app.config import settings
from app.models.schemas import ChatRequest, ChatResponse, ToolCallRecord
from app.services.context_service import build_context_block
from app.tools import ALL_TOOLS
from app.tools.cmms_queries import CMMS_TOOL_EXECUTORS
from app.tools.calculations import CALC_TOOL_EXECUTORS

_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

CHAT_SYSTEM_PROMPT = """You are an AI coworker assistant for facilities and maintenance teams in Singapore.
You have access to the CMMS database, past work orders, Singapore engineering standards,
and OEM equipment manuals. Answer questions clearly and cite sources where possible.
Always use the available tools to look up live data — do not make up figures.
When referencing standards, quote the clause number if available."""


def run_chat(request: ChatRequest, db: Session) -> ChatResponse:
    context = build_context_block(request.message)
    system = CHAT_SYSTEM_PROMPT
    if context:
        system += f"\n\n<retrieved_context>\n{context}\n</retrieved_context>"

    messages = [
        {"role": m.role, "content": m.content}
        for m in request.history
    ] + [{"role": "user", "content": request.message}]

    tool_calls_log: list[ToolCallRecord] = []
    sources: list[str] = []

    # Agentic loop
    while True:
        response = _client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=settings.CLAUDE_MAX_TOKENS,
            system=system,
            tools=ALL_TOOLS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            answer = next(
                (b.text for b in response.content if hasattr(b, "text")), ""
            )
            return ChatResponse(
                session_id=request.session_id,
                answer=answer,
                tool_calls=tool_calls_log,
                sources=sources,
            )

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                tool_name = block.name
                tool_input = block.input

                result = _execute_tool(tool_name, tool_input, db)
                tool_calls_log.append(
                    ToolCallRecord(tool_name=tool_name, input=tool_input, output=result)
                )

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(result),
                })

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
        else:
            break

    return ChatResponse(
        session_id=request.session_id,
        answer="I was unable to complete the request.",
        tool_calls=tool_calls_log,
    )


def _execute_tool(tool_name: str, tool_input: dict, db: Session):
    if tool_name in CMMS_TOOL_EXECUTORS:
        return CMMS_TOOL_EXECUTORS[tool_name](db, tool_input)
    if tool_name in CALC_TOOL_EXECUTORS:
        return CALC_TOOL_EXECUTORS[tool_name](tool_input)
    if tool_name == "lookup_singapore_standards":
        from app.services.context_service import get_standards_context
        limit = tool_input.get("limit", 5)
        results = get_standards_context(tool_input["query"], limit=limit)
        return [r.get("text", "") for r in results]
    return {"error": f"Unknown tool: {tool_name}"}
