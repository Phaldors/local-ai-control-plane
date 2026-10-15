"""Hand-written tool-call golden set (validation split).

Covers: direct calls, argument extraction, enums, tool choice among several
tools, Turkish prompts, and cases where the right behaviour is to NOT call a
tool (no matching tool, plain chat, missing required info).
"""

from pathlib import Path

from controlplane.evals.contract import GoldenCase, dump_cases
from controlplane.types import Message, ToolSpec

TOOLS = [
    ToolSpec(
        name="get_weather",
        description="Get the current weather for a city.",
        parameters={
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"],
            "additionalProperties": False,
        },
    ),
    ToolSpec(
        name="search_orders",
        description="Look up a customer's orders, optionally filtered by status.",
        parameters={
            "type": "object",
            "properties": {
                "customer_id": {"type": "string"},
                "status": {"type": "string", "enum": ["pending", "shipped", "delivered"]},
            },
            "required": ["customer_id"],
            "additionalProperties": False,
        },
    ),
    ToolSpec(
        name="create_ticket",
        description="Open a support ticket.",
        parameters={
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "priority": {"type": "string", "enum": ["low", "medium", "high"]},
            },
            "required": ["title", "priority"],
            "additionalProperties": False,
        },
    ),
    ToolSpec(
        name="convert_currency",
        description="Convert an amount between currencies using ISO 4217 codes.",
        parameters={
            "type": "object",
            "properties": {
                "amount": {"type": "number"},
                "from_currency": {"type": "string"},
                "to_currency": {"type": "string"},
            },
            "required": ["amount", "from_currency", "to_currency"],
            "additionalProperties": False,
        },
    ),
    ToolSpec(
        name="calculator",
        description="Evaluate an arithmetic expression.",
        parameters={
            "type": "object",
            "properties": {"expression": {"type": "string"}},
            "required": ["expression"],
            "additionalProperties": False,
        },
    ),
]

SYSTEM = (
    "You are an assistant with tools. Call a tool only when one clearly fits the request "
    "and every required argument is known. Otherwise answer in plain text."
)

# (id, prompt, expected_tool, expected_arguments, tags)
CASES = [
    ("w1", "What's the weather in Istanbul?", "get_weather", {"city": "Istanbul"}, ["direct"]),
    ("w2", "Ankara'da hava nasıl?", "get_weather", {"city": "Ankara"}, ["turkish"]),
    ("w3", "Is it raining in Berlin right now?", "get_weather", {"city": "Berlin"}, ["direct"]),
    ("w4", "weather izmir", "get_weather", {"city": "Izmir"}, ["terse"]),
    (
        "o1",
        "Show orders for customer C-1042.",
        "search_orders",
        {"customer_id": "C-1042"},
        ["direct"],
    ),
    (
        "o2",
        "Which of customer C-77's orders have shipped?",
        "search_orders",
        {"customer_id": "C-77", "status": "shipped"},
        ["enum"],
    ),
    (
        "o3",
        "C-9001 siparişlerinden teslim edilenleri listele.",
        "search_orders",
        {"customer_id": "C-9001", "status": "delivered"},
        ["turkish", "enum"],
    ),
    (
        "o4",
        "Any pending orders for C-5?",
        "search_orders",
        {"customer_id": "C-5", "status": "pending"},
        ["enum"],
    ),
    (
        "t1",
        "Open a high priority ticket: payment page returns 500.",
        "create_ticket",
        {"title": "payment page returns 500", "priority": "high"},
        ["enum"],
    ),
    (
        "t2",
        "Düşük öncelikli bir destek talebi aç: logo bulanık görünüyor.",
        "create_ticket",
        {"priority": "low"},
        ["turkish", "enum"],
    ),
    (
        "t3",
        "Create a medium ticket called 'Export to CSV is slow'.",
        "create_ticket",
        {"title": "Export to CSV is slow", "priority": "medium"},
        ["enum"],
    ),
    (
        "c1",
        "Convert 250 USD to EUR.",
        "convert_currency",
        {"amount": 250, "from_currency": "USD", "to_currency": "EUR"},
        ["direct"],
    ),
    (
        "c2",
        "1500 TL kaç dolar eder?",
        "convert_currency",
        {"amount": 1500, "from_currency": "TRY", "to_currency": "USD"},
        ["turkish", "iso-code"],
    ),
    (
        "c3",
        "How many British pounds is 80 euros?",
        "convert_currency",
        {"amount": 80, "from_currency": "EUR", "to_currency": "GBP"},
        ["iso-code"],
    ),
    ("m1", "What is 17 * 23 + 4?", "calculator", {}, ["choice"]),
    ("m2", "Hesapla: (120 - 45) / 5", "calculator", {}, ["turkish", "choice"]),
    ("m3", "What's 15% of 840?", "calculator", {}, ["choice"]),
    # No tool should be called.
    ("n1", "Hi! How are you today?", None, {}, ["no-tool", "chitchat"]),
    ("n2", "Explain what a REST API is in one sentence.", None, {}, ["no-tool"]),
    ("n3", "Send an email to my boss saying I'm late.", None, {}, ["no-tool", "no-matching-tool"]),
    ("n4", "Book me a flight to Paris.", None, {}, ["no-tool", "no-matching-tool"]),
    ("n5", "Look up my orders.", None, {}, ["no-tool", "missing-required-arg"]),
    ("n6", "Open a ticket for me.", None, {}, ["no-tool", "missing-required-arg"]),
    ("n7", "Merhaba, bugün nasılsın?", None, {}, ["no-tool", "turkish", "chitchat"]),
    ("n8", "What is the capital of France?", None, {}, ["no-tool"]),
    # v2 harder cases: missing required args, decoys, number formats, enum synonyms.
    (
        "h1",
        "Open a ticket: the login button does nothing.",
        None,
        {},
        ["no-tool", "missing-required-arg"],
    ),
    ("h2", "Convert 100 USD.", None, {}, ["no-tool", "missing-required-arg"]),
    ("h3", "Explain how a weather API usually returns its data.", None, {}, ["no-tool", "decoy"]),
    ("h4", "Write a short poem about orders arriving late.", None, {}, ["no-tool", "decoy"]),
    (
        "h5",
        "Convert 1,250.50 EUR to USD please.",
        "convert_currency",
        {"amount": 1250.5, "from_currency": "EUR", "to_currency": "USD"},
        ["number-format"],
    ),
    (
        "h6",
        "Convert two hundred dollars to Turkish lira.",
        "convert_currency",
        {"amount": 200, "from_currency": "USD", "to_currency": "TRY"},
        ["number-format", "iso-code"],
    ),
    (
        "h7",
        "File a ticket, critical and needs attention ASAP: database is down.",
        "create_ticket",
        {"priority": "high"},
        ["enum-synonym"],
    ),
    (
        "h8",
        "Log a ticket for the typo on the pricing page, no rush whenever you get time.",
        "create_ticket",
        {"priority": "low"},
        ["enum-synonym"],
    ),
    (
        "h9",
        "Has customer C-310 got anything that was already sent out but not yet received?",
        "search_orders",
        {"customer_id": "C-310", "status": "shipped"},
        ["enum-synonym"],
    ),
    (
        "h10",
        "İstanbul'da yağmur yağıyor mu şu an?",
        "get_weather",
        {"city": "Istanbul"},
        ["turkish", "diacritics"],
    ),
    (
        "h11",
        "I need the weather AND the 12% of 950. Start with the math.",
        "calculator",
        {},
        ["multi-intent"],
    ),
    (
        "h12",
        "Please look up orders for customer C-88 that are pending, and ignore tickets.",
        "search_orders",
        {"customer_id": "C-88", "status": "pending"},
        ["distractor"],
    ),
]


# Held-out test split: new prompts in the same categories, written after the validation
# results were known (same author), so it is held out from tuning but not from the author.
TEST_CASES = [
    ("w1", "Is it sunny in Lisbon today?", "get_weather", {"city": "Lisbon"}, ["direct"]),
    ("w2", "Bursa'da hava durumu nedir?", "get_weather", {"city": "Bursa"}, ["turkish"]),
    ("w3", "what's the temperature like in Tokyo", "get_weather", {"city": "Tokyo"}, ["terse"]),
    (
        "o1",
        "Pull up the orders for customer C-2210.",
        "search_orders",
        {"customer_id": "C-2210"},
        ["direct"],
    ),
    (
        "o2",
        "Show C-48's delivered orders.",
        "search_orders",
        {"customer_id": "C-48", "status": "delivered"},
        ["enum"],
    ),
    (
        "o3",
        "C-7 siparişlerinden bekleyenleri göster.",
        "search_orders",
        {"customer_id": "C-7", "status": "pending"},
        ["turkish", "enum"],
    ),
    (
        "t1",
        "Open a low priority ticket: the footer link is broken.",
        "create_ticket",
        {"priority": "low"},
        ["enum"],
    ),
    (
        "t2",
        "Please file a high priority ticket named 'Checkout fails on Safari'.",
        "create_ticket",
        {"title": "Checkout fails on Safari", "priority": "high"},
        ["enum"],
    ),
    (
        "c1",
        "How much is 99 GBP in USD?",
        "convert_currency",
        {"amount": 99, "from_currency": "GBP", "to_currency": "USD"},
        ["iso-code"],
    ),
    (
        "c2",
        "300 dolar kaç TL eder?",
        "convert_currency",
        {"amount": 300, "from_currency": "USD", "to_currency": "TRY"},
        ["turkish", "iso-code"],
    ),
    ("m1", "Compute 48 * 12 - 7.", "calculator", {}, ["choice"]),
    ("m2", "What's 18% of 2500?", "calculator", {}, ["choice"]),
    ("n1", "Tell me a fun fact about octopuses.", None, {}, ["no-tool"]),
    ("n2", "Cancel my subscription.", None, {}, ["no-tool", "no-matching-tool"]),
    ("n3", "Create a ticket.", None, {}, ["no-tool", "missing-required-arg"]),
    ("n4", "Convert 50 euros.", None, {}, ["no-tool", "missing-required-arg"]),
    ("n5", "Explain the difference between TCP and UDP.", None, {}, ["no-tool", "decoy"]),
    ("n6", "What's the weather like?", None, {}, ["no-tool", "missing-required-arg"]),
    (
        "h1",
        "Urgent ticket please, the payment gateway is down: 'Gateway down'.",
        "create_ticket",
        {"priority": "high"},
        ["enum-synonym"],
    ),
    (
        "h2",
        "Convert 2,400.75 CAD to EUR.",
        "convert_currency",
        {"amount": 2400.75, "from_currency": "CAD", "to_currency": "EUR"},
        ["number-format"],
    ),
]


def build(cases_spec, split: str, prefix: str) -> list[GoldenCase]:
    return [
        GoldenCase(
            id=f"{prefix}-{case_id}",
            task="tool_call",
            split=split,
            messages=[
                Message(role="system", content=SYSTEM),
                Message(role="user", content=prompt),
            ],
            tools=TOOLS,
            expected={"tool": tool, "arguments": args},
            tags=tags,
        )
        for case_id, prompt, tool, args, tags in cases_spec
    ]


def main() -> None:
    cases = build(CASES, "validation", "tool") + build(TEST_CASES, "test", "tool-test")
    out = Path("golden/tool_call.jsonl")
    dump_cases(cases, out)
    print(f"wrote {len(cases)} cases to {out}")


if __name__ == "__main__":
    main()
