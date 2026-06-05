"""CLI-интерфейс для тестирования ИИ онбордера CodeAcademy Pro.

Запуск: python cli.py
Для отладки (показывает вызовы инструментов): python cli.py --verbose
"""

import sys
from agent import run_agent_turn

WELCOME = """
╔═══════════════════════════════════════════════════╗
║          ИИ Онбордер — CodeAcademy Pro            ║
║  Задавай любые вопросы о компании и работе!       ║
║  Введи 'выход' или нажми Ctrl+C для выхода        ║
╚═══════════════════════════════════════════════════╝
"""


def main():
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    print(WELCOME)
    if verbose:
        print("[Режим отладки: показываю вызовы инструментов]\n")

    messages = []

    while True:
        try:
            user_input = input("Вы: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nДо свидания!")
            break

        if not user_input:
            continue

        if user_input.lower() in ("выход", "exit", "quit", "q"):
            print("До свидания!")
            break

        messages.append({"role": "user", "content": user_input})
        print("\nОнбордер: ", end="", flush=True)

        try:
            response = run_agent_turn(messages, verbose=verbose)
            print(f"{response}\n")
        except Exception as e:
            print(f"\n[Ошибка: {e}]\n")
            messages.pop()


if __name__ == "__main__":
    main()
