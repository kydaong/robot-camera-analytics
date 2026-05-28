"""
Mode 1 – AI coworker chat orchestration.
Runs the Claude agent loop with CMMS + calculation + standards tools.
"""
import time
import anthropic
import mlflow
from sqlalchemy.orm import Session

from app.config import settings
from app.models.schemas import ChatRequest, ChatResponse, ToolCallRecord
from app.services.context_service import build_context_block
from app.tools import ALL_TOOLS
from app.tools.cmms_queries import CMMS_TOOL_EXECUTORS
from app.tools.calculations import CALC_TOOL_EXECUTORS

_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

# claude-sonnet-4-6 pricing (USD per token)
_INPUT_COST_PER_TOKEN  = 3.00  / 1_000_000   # $3.00 / MTok
_OUTPUT_COST_PER_TOKEN = 15.00 / 1_000_000   # $15.00 / MTok

CHAT_SYSTEM_PROMPT = """You are an AI coworker assistant for facilities and maintenance teams in Singapore.
You have access to the CMMS database, past work orders, Singapore engineering standards,
and OEM equipment manuals. Answer questions clearly and cite sources where possible.
Always use the available tools to look up live data — do not make up figures.
When referencing standards and manuals, quote the clause number if available.
When returning work order information, always state the data_source field so the user
knows whether the record came from v_inspection_tasks or spot_work_orders.
When returning inspection tasks, always include the source field value exactly as stored."""


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
    total_input_tokens = 0
    total_output_tokens = 0
    start_time = time.time()

    # Agentic loop
    while True:
        response = _client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=settings.CLAUDE_MAX_TOKENS,
            system=system,
            tools=ALL_TOOLS,
            messages=messages,
        )

        # Accumulate tokens across every loop iteration
        if response.usage:
            total_input_tokens  += response.usage.input_tokens
            total_output_tokens += response.usage.output_tokens

        if response.stop_reason == "end_turn":
            answer = next(
                (b.text for b in response.content if hasattr(b, "text")), ""
            )
            _log_trace(
                query=request.message,
                session_id=request.session_id or "",
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                num_tool_calls=len(tool_calls_log),
                latency=time.time() - start_time,
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

    _log_trace(
        query=request.message,
        session_id=request.session_id or "",
        input_tokens=total_input_tokens,
        output_tokens=total_output_tokens,
        num_tool_calls=len(tool_calls_log),
        latency=time.time() - start_time,
    )
    return ChatResponse(
        session_id=request.session_id,
        answer="I was unable to complete the request.",
        tool_calls=tool_calls_log,
    )


def _log_trace(
    query: str,
    session_id: str,
    input_tokens: int,
    output_tokens: int,
    num_tool_calls: int,
    latency: float,
) -> None:
    """Log one MLflow run per chat query. Never raises — tracing must not break chat."""
    try:
        cost = (input_tokens * _INPUT_COST_PER_TOKEN) + (output_tokens * _OUTPUT_COST_PER_TOKEN)
        with mlflow.start_run(run_name="chat_query"):
            mlflow.set_tags({
                "model": settings.CLAUDE_MODEL,
                "session_id": session_id,
                "type": "chat_query",
            })
            mlflow.log_param("query", query[:500])
            mlflow.log_metrics({
                "input_tokens":       input_tokens,
                "output_tokens":      output_tokens,
                "total_tokens":       input_tokens + output_tokens,
                "estimated_cost_usd": round(cost, 6),
                "num_tool_calls":     num_tool_calls,
                "latency_seconds":    round(latency, 3),
            })
    except Exception:
        pass


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
