import requests
from config import YANDEX_GPT_IDENTIFICATOR, YANDEX_GPT_API_KEY

# Источник:
# https://yandex.cloud/ru/docs/speechkit/sdk/python/request
# Ограничения
# https://yandex.cloud/ru/docs/foundation-models/concepts/limits?from=int-console-help-center-or-nav&from=service-start-page


async def creating_conspect(text, filename, output_format):
    """Создаём из транскрибированного текста удобно читабельный текст нужного формата"""
    # Запросы для genai
    tasks = {
        "markdown": "Переведите этот текст в формат MARKDOWN.",

        "html": """Поместите этот текст в веб-страницу. В качестве ответа ожидется HTML файл.
        Каждый абзац должен быть заключён в тег <p>. Где это нужно, можно добавлять секции с заголовками, а также
        использовать курсивное и полужирное начертание слов. Комментарии к html коду оставлять НЕ НУЖНО.""",

        "latex": """Переведите этот текст в формат LATEX. Добавьте преамбулу со строчками
        \\documentclass[a4paper, 12pt]{article}, \\usepackage[english, russian]{babel}, \\usepackage[T2A]{fontenc},
        \\usepackage[utf8]{inputenc}, \\usepackage{indentfirst}. Сам код нужно обернуть в окружение
        \\begin{document} ... \\end{document}. Где это нужно, можно добавлять секции с заголовками с помощью тега
        \\section{}, а также использовать курсивное и полужирное начертание слов, используя теги \\textit{} и \\textbf{}
        соответственно. Комментарии к latex коду оставлять НЕ НУЖНО."""
    }

    # Удаляем пробелы в начале и в конце, добавляем точку, если нужно.
    text = text.strip()
    if text[-1] not in ".!?":
        text += '.'

    # Файл с ответом
    file = open(filename, "a")

    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {YANDEX_GPT_API_KEY}"
    }

    # Обрабатываем текст по частям - 8000 символов
    first_part_flag = True
    start_ind = 0
    limit = 8000
    finish_ind = min(limit, len(text) - 1)
    while start_ind < finish_ind:
        # Ищем ближайшую точку, восклицательный, вопросительный знак
        while text[finish_ind] not in ".!?":
            finish_ind -= 1
        fragment = text[start_ind:finish_ind + 1]

        prompt = {
            "modelUri": f"gpt://{YANDEX_GPT_IDENTIFICATOR}/yandexgpt/latest",
            "completionOptions": {
                "stream": False,
                "temperature": 0.6,
                "maxTokens": "2000"
            },
            "messages": [
                {
                    "role": "system",
                    "text": "Необходимо написать подробный пересказ данного текcта. Пересказ должен представлять собой чистый текст, разделённый на абзацы."
                },
                {
                    "role": "user",
                    "text": fragment
                }
            ]
        }

        # print("=" * 30)
        # print("Фрагмент:", len(fragment), fragment)

        # Запрос для конвертирования в читабельный текст
        response = requests.post(url, headers=headers, json=prompt).json()
        result_text = response["result"]["alternatives"][0]["message"]["text"]
        # print(1, result_text)

        # В случае markdown, html и latex нужно сделать ещё один запрос
        if output_format != "txt":
            prompt = {
                "modelUri": f"gpt://{YANDEX_GPT_IDENTIFICATOR}/yandexgpt/latest",
                "completionOptions": {
                    "stream": False,
                    "temperature": 0.6,
                    "maxTokens": "2000"
                },
                "messages": [
                    {
                        "role": "system",
                        "text": tasks[output_format]
                    },
                    {
                        "role": "user",
                        "text": result_text
                    }
                ]
            }

            # Конвертация текста в нужный формат
            response = requests.post(url, headers=headers, json=prompt).json()
            result_text = response["result"]["alternatives"][0]["message"]["text"]
            # print(2, result_text)

            # Соединяем две части конспекта в зависимости от формата
            if output_format == "html":
                if first_part_flag:
                    first_part_flag = False
                    begin_ind = result_text.find("```html")
                    if begin_ind != -1:
                        result_text = result_text[begin_ind + 8:]
                else:
                    begin_ind = result_text.find("<body>")
                    if begin_ind != -1:
                        result_text = result_text[begin_ind + 6:]
                end_ind = result_text.find("</body>")
                if end_ind != -1:
                    result_text = result_text[:end_ind]
            elif output_format == "latex":
                if first_part_flag:
                    first_part_flag = False
                    begin_ind = result_text.find("```")
                    if begin_ind != -1:
                        result_text = result_text[begin_ind + 4:]
                else:
                    begin_ind = result_text.find("\\begin{document}")
                    if begin_ind != -1:
                        result_text = result_text[begin_ind + 16:]
                end_ind = result_text.find("\\end{document}")
                if end_ind != -1:
                    result_text = result_text[:end_ind]

        file.write(result_text)

        # Переходим к следующему фрагменту
        start_ind = finish_ind + 1
        finish_ind += limit
        finish_ind = min(finish_ind, len(text) - 1)

    # Добавляем окончание документа
    if output_format == "html":
        file.write("</body>\n</html>\n")
    elif output_format == "latex":
        file.write("\\end{document}\n")
    file.close()
