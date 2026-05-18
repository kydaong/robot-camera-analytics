"""
Claude tool definition for looking up Singapore engineering standards via Qdrant RAG.
"""

TOOL_LOOKUP_STANDARDS = {
    "name": "lookup_singapore_standards",
    "description": (
        "Search Singapore engineering standards (SS, CP, TR series) for relevant "
        "clauses, requirements, or guidance on a given topic."
    ),
    "input_schema": {
        "type": "object",
        "required": ["query"],
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural language description of what standard/clause to find",
            },
            "limit": {
                "type": "integer",
                "default": 5,
                "description": "Number of relevant chunks to return",
            },
        },
    },
}

ALL_STANDARDS_TOOLS = [TOOL_LOOKUP_STANDARDS]
