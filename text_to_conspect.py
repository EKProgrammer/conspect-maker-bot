import requests
from config import YANDEX_GPT_IDENTIFICATOR, YANDEX_GPT_API_KEY

# Источник:
# https://yandex.cloud/ru/docs/speechkit/sdk/python/request
# Ограничения
# https://yandex.cloud/ru/docs/foundation-models/concepts/limits?from=int-console-help-center-or-nav&from=service-start-page


async def creating_conspect(text, filename, output_format):
    tasks = {
        "markdown": "Переведите этот текст в формат MARKDOWN.",
        "html": """Поместите этот текст в веб-страницу. В качестве ответа ожидется HTML файл.
        Каждый абзац должен быть заключён в тег <p>. Комментарии к html коду оставлять НЕ НУЖНО.""",
        "latex": """Переведите этот текст в формат LATEX. Добавьте преамбулу со строчками
        \\documentclass[a4paper, 12pt]{article}, \\usepackage[english, russian]{babel}, \\usepackage[T2A]{fontenc},
        \\usepackage[utf8]{inputenc}, \\usepackage{indentfirst}. Сам код нужно обернуть в окружение
        \\begin{document} ... \\end{document}. Где это нужно, можно добавлять секции с заголовками с помощью тега
        \\section{}, а также использовать курсивное и полужирное начертание, используя теги \\textit{} и \\textbf{}
        соответственно. Комментарии к latex коду оставлять НЕ НУЖНО."""
    }

    text = text.strip()
    if text[-1] not in ".!?":
        text += '.'
    file = open(filename, "a")

    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {YANDEX_GPT_API_KEY}"
    }

    start_ind = 0
    limit = 8000
    finish_ind = min(limit, len(text) - 1)
    while start_ind < finish_ind:
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

        print("=" * 30)
        print("Фрагмент:", len(fragment), fragment)
        response = requests.post(url, headers=headers, json=prompt).json()
        print(1, response)

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
                        "text": response["result"]["alternatives"][0]["message"]["text"]
                    }
                ]
            }

            response = requests.post(url, headers=headers, json=prompt).json()
            print(2, response)

        file.write(response["result"]["alternatives"][0]["message"]["text"] + "\n\n")

        start_ind = finish_ind + 1
        finish_ind += limit
        finish_ind = min(finish_ind, len(text) - 1)

    file.close()
