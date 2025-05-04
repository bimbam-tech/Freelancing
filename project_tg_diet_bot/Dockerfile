# Используем образ Python 3.10-slim в качестве базового
FROM python:3.10-slim

# Копирование файлов приложения
COPY project_tg_diet_bot/ /project_tg_diet_bot/
WORKDIR /project_tg_diet_bot


# Устанавливаем зависимости Python
RUN pip install --no-cache-dir -r requirements.txt

# Установка зависимостей приложения
#ENV $(cat /project_tg_diet_bot/.env | xargs)
ENV BOT_TOKEN=BOT_TOKEN
ENV OPENAI_API_KEY=OPENAI_API_KEY
ENV DATABASE_URL=DATABASE_URL


# Указываем главный скрипт для запуска
CMD ["python3", "main.py"]
