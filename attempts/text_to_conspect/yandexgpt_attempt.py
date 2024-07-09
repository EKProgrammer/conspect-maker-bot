import requests

def processing(resp):
    if isinstance(resp, dict):
        for key in resp:
            print(key)
            processing(resp[key])
    else:
        print(resp)

prompt = {
    "modelUri": "gpt://b1g70r363n172jhpmn3k/yandexgpt/latest",
    "completionOptions": {
        "stream": False,
        "temperature": 0.6,
        "maxTokens": "2000"
    },
    "messages": [
        {
            "role": "user",
            "text": "Придумай как добраться от Москвы до Рейкъявика."
        }
    ]
}


url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
headers = {
    "Content-Type": "application/json",
    "Authorization": "Api-Key AQVN2IMm0VyDCOEh43YsuiKKYW37Fiqk4uTzoSgy"
}

response = requests.post(url, headers=headers, json=prompt).json()
processing(response)
