import os
import re
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

KB_PATH = Path(__file__).parent / "KnowlageBase"
PROVIDER = os.getenv("AI_PROVIDER", "openrouter").lower()

if PROVIDER == "anthropic":
    import anthropic as _anthropic
    MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-8")
    _client = _anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
else:
    from openai import OpenAI as _OpenAI
    MODEL = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3-ultra-550b-a55b:free")
    _key = os.getenv("OPENROUTER_API_KEY")
    if not _key:
        raise RuntimeError(
            "Не задан OPENROUTER_API_KEY.\n"
            "Задай переменную среды: set OPENROUTER_API_KEY=sk-or-v1-..."
        )
    _client = _OpenAI(base_url="https://openrouter.ai/api/v1", api_key=_key)

SYSTEM_PROMPT = """Ты — ИИ онбордер компании CodeAcademy Pro, EdTech-стартапа, который учит программированию.

Помогаешь новым сотрудникам адаптироваться: отвечаешь на вопросы о компании, процессах, команде, корпоративной культуре и плане адаптации.

ВАЖНО: перед ответом ВСЕГДА ищи информацию в базе знаний через инструменты. Не отвечай из головы.

В файлах встречаются ссылки вида [[Название файла]] — это ссылки на другие документы базы знаний. Читай их через read_file когда нужно.

Общайся дружелюбно, на «ты», без официоза. Поддерживай новичков."""

# Anthropic format
_TOOLS_ANTHROPIC = [
    {
        "name": "list_knowledge_base",
        "description": "Возвращает список всех файлов в базе знаний компании.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "read_file",
        "description": "Читает содержимое файла из базы знаний. Поддерживает: 'Компания', 'Компания.md', '[[Компания]]'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Имя файла, например: 'Компания.md'"}
            },
            "required": ["filename"],
        },
    },
    {
        "name": "search_knowledge_base",
        "description": "Ищет слово или фразу во всех файлах базы знаний.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Поисковый запрос"}
            },
            "required": ["query"],
        },
    },
]

# OpenAI / OpenRouter format
_TOOLS_OPENAI = [
    {
        "type": "function",
        "function": {
            "name": "list_knowledge_base",
            "description": "Возвращает список всех файлов в базе знаний компании.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Читает содержимое файла из базы знаний. Поддерживает: 'Компания', 'Компания.md', '[[Компания]]'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Имя файла, например: 'Компания.md'"}
                },
                "required": ["filename"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "Ищет слово или фразу во всех файлах базы знаний.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Поисковый запрос"}
                },
                "required": ["query"],
            },
        },
    },
]


# ── Knowledge base tools ──────────────────────────────────────────────────────

def _find_file(filename: str) -> Path | None:
    clean = re.sub(r"^\[\[|\]\]$", "", filename.strip())
    for candidate in [KB_PATH / clean, KB_PATH / f"{clean}.md"]:
        if candidate.exists():
            return candidate
    clean_lower = Path(clean).stem.lower()
    for f in KB_PATH.glob("**/*.md"):
        if f.stem.lower() == clean_lower:
            return f
    return None


def _list_knowledge_base() -> str:
    files = sorted(KB_PATH.glob("**/*.md"))
    if not files:
        return "База знаний пуста."
    return "Файлы в базе знаний:\n" + "\n".join(f"- {f.name}" for f in files)


def _read_file(filename: str) -> str:
    target = _find_file(filename)
    if not target:
        available = sorted(f.name for f in KB_PATH.glob("**/*.md"))
        return f"Файл '{filename}' не найден. Доступные файлы: {', '.join(available)}"
    try:
        return target.read_text(encoding="utf-8")
    except Exception as e:
        return f"Ошибка чтения файла: {e}"


def _search_knowledge_base(query: str) -> str:
    results = []
    query_lower = query.lower()
    for f in sorted(KB_PATH.glob("**/*.md")):
        try:
            content = f.read_text(encoding="utf-8")
        except Exception:
            continue
        if query_lower not in content.lower():
            continue
        lines = [l.strip() for l in content.splitlines() if query_lower in l.lower() and l.strip()]
        snippet = "\n".join(f"  > {l}" for l in lines[:3])
        results.append(f"**{f.name}:**\n{snippet}")
    if not results:
        return f"По запросу «{query}» ничего не найдено."
    return f"Найдено в {len(results)} файлах:\n\n" + "\n\n".join(results)


def _execute_tool(name: str, tool_input: dict) -> str:
    if name == "list_knowledge_base":
        return _list_knowledge_base()
    if name == "read_file":
        return _read_file(tool_input.get("filename", ""))
    if name == "search_knowledge_base":
        return _search_knowledge_base(tool_input.get("query", ""))
    return f"Неизвестный инструмент: {name}"


# ── Provider-specific runners ─────────────────────────────────────────────────

def _run_openrouter(messages: list, verbose: bool) -> str:
    api_msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in messages:
        api_msgs.append({"role": m["role"], "content": m["content"]})

    step = 0
    while True:
        step += 1
        print(f"  [шаг {step}] Запрос к {MODEL} (openrouter)...", flush=True)
        try:
            response = _client.chat.completions.create(
                model=MODEL,
                max_tokens=4096,
                messages=api_msgs,
                tools=_TOOLS_OPENAI,
                tool_choice="auto",
            )
        except Exception as e:
            print(f"  [ошибка API] {type(e).__name__}: {e}", flush=True)
            raise

        choice = response.choices[0]
        msg = choice.message
        finish_reason = choice.finish_reason
        print(f"  [шаг {step}] finish_reason={finish_reason!r}", flush=True)

        if finish_reason == "tool_calls" and msg.tool_calls:
            api_msgs.append(msg)
            for tc in msg.tool_calls:
                try:
                    tool_input = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    tool_input = {}
                print(f"  [tool] {tc.function.name}({tool_input})", flush=True)
                result = _execute_tool(tc.function.name, tool_input)
                if verbose:
                    print(f"  [result] {result[:300]}", flush=True)
                api_msgs.append({"role": "tool", "tool_call_id": tc.id, "content": result})
        else:
            return msg.content or f"[finish_reason={finish_reason}]"


def _run_anthropic(messages: list, verbose: bool) -> str:
    api_msgs = [{"role": m["role"], "content": m["content"]} for m in messages]

    step = 0
    while True:
        step += 1
        print(f"  [шаг {step}] Запрос к {MODEL} (anthropic)...", flush=True)
        try:
            response = _client.messages.create(
                model=MODEL,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=_TOOLS_ANTHROPIC,
                messages=api_msgs,
            )
        except Exception as e:
            print(f"  [ошибка API] {type(e).__name__}: {e}", flush=True)
            raise

        print(f"  [шаг {step}] stop_reason={response.stop_reason!r}", flush=True)

        if response.stop_reason == "tool_use":
            api_msgs.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"  [tool] {block.name}({block.input})", flush=True)
                    result = _execute_tool(block.name, block.input)
                    if verbose:
                        print(f"  [result] {result[:300]}", flush=True)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })
            api_msgs.append({"role": "user", "content": tool_results})
        else:
            return next((b.text for b in response.content if b.type == "text"), "")


# ── Public API ────────────────────────────────────────────────────────────────

def run_agent_turn(messages: list, verbose: bool = False) -> str:
    """One conversation turn with tool loop. Appends assistant reply to messages."""
    if PROVIDER == "anthropic":
        text = _run_anthropic(messages, verbose)
    else:
        text = _run_openrouter(messages, verbose)
    messages.append({"role": "assistant", "content": text})
    return text
