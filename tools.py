#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from ollama import chat, ChatResponse


ROUTER_MODEL = "qwen2.5:7b"
EXPERT_MODEL = "qwen2.5-coder:7b"
DIALECT_DEFAULT = "mysql"

# ===============================
# Tool definition (schema only)
# ===============================

tools = [
    {
        "type": "function",
        "function": {
            "name": "analyze_sql",
            "description": (
                "Analyze a SQL query and recommend database indexes "
                "to improve performance."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The SQL query to analyze"
                    },
                    "dialect": {
                        "type": "string",
                        "description": "SQL dialect (e.g. mysql, postgresql)",
                        "default": "mysql"
                    }
                },
                "required": ["query"]
            }
        }
    }
]


# ===============================
# Tool implementation
# ===============================

COMPLEX_MARKERS = [
    r"\bjoin\b",
    r"\bunion\b",
    r"\bgroup\s+by\b",
    r"\bhaving\b",
    r"\bwith\b",
    r"\bexists\b",
    r"\bin\s*\(\s*select\b",
    r"\bselect\b.*\bselect\b",
]


def normalize_sql(sql: str) -> str:
    return re.sub(r"\s+", " ", sql.strip())


def is_complex_sql(sql: str) -> bool:
    s = normalize_sql(sql).lower()
    return any(re.search(p, s) for p in COMPLEX_MARKERS)


def extract_where_columns(sql: str) -> List[str]:
    s = normalize_sql(sql)

    m = re.search(
        r"\bwhere\b(.*?)(\border\s+by\b|\bgroup\s+by\b|\bhaving\b|\blimit\b|$)",
        s,
        flags=re.IGNORECASE,
    )
    if not m:
        return []

    where_part = m.group(1)

    matches = re.findall(
        r"([a-zA-Z_][\w\.]*)\s*(=|<|>|<=|>=|!=|<>|\bin\b|\blike\b|\bbetween\b)",
        where_part,
        flags=re.IGNORECASE,
    )

    cols = [raw_col.split(".")[-1] for raw_col, _ in matches]
    return list(dict.fromkeys(cols))


def analyze_sql(query: str, dialect: str = DIALECT_DEFAULT) -> Dict[str, Any]:
    q = normalize_sql(query)

    if not is_complex_sql(q):

        print("\n*** simple SQL:\n")

        where_cols = extract_where_columns(q)

        if not where_cols:
            return {
                "mode": "simple",
                "index_recommendation": [],
                "reason": "Query neobsahuje WHERE podmínku."
            }

        return {
            "mode": "simple",
            "index_recommendation": [f"INDEX({', '.join(where_cols)})"],
            "reason": "Jednoduchý SELECT: indexuj sloupce použité ve WHERE."
        }

    # Complex → expert LLM
    print("\n*** Complex SQL, calling expert LLM:\n")

    expert_messages = [
        {
            "role": "system",
            "content": "You are a senior SQL performance expert."
        },
        {
            "role": "user",
            "content": f"Dialect: {dialect}\nSQL:\n{q}\n\nRecommend indexes."
        },
    ]

    expert: ChatResponse = chat(
        model=EXPERT_MODEL,
        messages=expert_messages
    )

    return {
        "mode": "complex",
        "expert_advice": expert.message.content
    }


# ===============================
# System prompt (NO tool instructions)
# ===============================

SYSTEM_PROMPT = """\
You are a helpful backend assistant.
Answer clearly and concisely in Czech.
If a tool is used, interpret its output and explain the result to the user.
"""


# ===============================
# Agent loop
# ===============================

def run_chat():
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

    print("SQL agent (clean tool calling). 'exit' pro konec.\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("exit", "quit"):
            break

        messages.append({"role": "user", "content": user_input})

        while True:
            response: ChatResponse = chat(
                model=ROUTER_MODEL,
                messages=messages,
                tools=tools,
            )

            messages.append(response.message)

            if not response.message.tool_calls:
                print("\n*** Assistant:\n" + response.message.content + "\n")
                break

            for tool_call in response.message.tool_calls:
                name = tool_call.function.name
                args = tool_call.function.arguments or {}

                print("\n*** Tool call: " + name + " " + str(args) + "\n")

                if name == "analyze_sql":
                    result = analyze_sql(**args)
                else:
                    result = {"error": "Unknown tool"}

                messages.append({
                    "role": "tool",
                    "tool_name": name,
                    "content": json.dumps(result, ensure_ascii=False)
                })


if __name__ == "__main__":
    run_chat()
