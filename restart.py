import subprocess
import sys
import os

def restart_bot():
    # Путь к основному скрипту бота
    bot_script = "main.py"
    
    try:
        # Завершаем текущий процесс
        python = sys.executable
        os.execl(python, python, bot_script)
    except Exception as e:
        print(f"Error restarting bot: {e}") 