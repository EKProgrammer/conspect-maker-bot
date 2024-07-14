import requests
from config import YANDEX_GPT_IDENTIFICATOR, YANDEX_GPT_API_KEY

# Источник:
# https://yandex.cloud/ru/docs/speechkit/sdk/python/request
# Ограничения
# https://yandex.cloud/ru/docs/foundation-models/concepts/limits?from=int-console-help-center-or-nav&from=service-start-page


async def creating_conspect(text, filename, output_format):
    file = open(filename, "a")

    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {YANDEX_GPT_API_KEY}"
    }
    prompt = {
        "modelUri": f"gpt://{YANDEX_GPT_IDENTIFICATOR}/yandexgpt/latest",
        "completionOptions": {
            "stream": False,
            "temperature": 0.6,
            "maxTokens": "2000",
            "max_pause_between_words_hint_ms": 1000
        },
        "messages": [
            {
                "role": "user",
                "text": "Необходимо написать подробный пересказ этого текcта и оформить его в формате " +
                        output_format + ". Текст:\n\"" + text
            }
        ]
    }
    print(text)
    response = requests.post(url, headers=headers, json=prompt).json()

    print("=" * 15)
    print(len(response["result"]["alternatives"]))
    print(len(response["result"]["alternatives"][0]["message"]["text"]))
    file.write(response["result"]["alternatives"][0]["message"]["text"] + '\n')
    file.close()
