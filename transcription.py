import speechkit.stt.transcription
from speechkit import model_repository, configure_credentials, creds
from speechkit.stt import AudioProcessingType

import os

from text_to_conspect import creating_conspect

from config import SPEECHKIT_API_KEY

# Аутентификация через API-ключ.
configure_credentials(
   yandex_credentials=creds.YandexCredentials(
      api_key=SPEECHKIT_API_KEY
   )
)


async def recognition(update, audio_file_path, output_format) -> None:
    """Транскрибация аудио"""
    model = model_repository.recognition_model()

    # Настройки распознавания.
    model.model = 'general'
    model.language = 'ru-RU'
    model.audio_processing_type = AudioProcessingType.Full

    # Распознавание речи в указанном аудиофайле.
    await update.message.reply_text("Транскрибация...")
    result = model.transcribe_file(audio_file_path)
    await update.message.reply_text("Транскрибация завершена.")

    file_extensions = {
        "txt": "txt",
        "markdown": "md",
        "html": "html",
        "latex": "tex"
    }
    filename = f"result.{file_extensions[output_format]}"

    await update.message.reply_text("Формирование конспекта...")

    res = result[0]
    if res.has_utterances():
        index = 0
        while index < len(res.utterances):
            cnt_symbols = 0
            paragraphs = []
            while index < len(res.utterances) and cnt_symbols + len(res.utterances[index].text) <= 4000:
                paragraphs.append(res.utterances[index].text)
                cnt_symbols += len(res.utterances[index].text)
                index += 1
            if not paragraphs:
                paragraphs.append(res.utterances[index].text)
                cnt_symbols += len(res.utterances[index].text)
                index += 1
            await creating_conspect(''.join(paragraphs), filename, output_format)

        await update.message.reply_text("Результат запроса:")
        await update.message.reply_document(filename)
        os.remove(filename)
    else:
        await update.message.reply_text("Файл содержит тишину вместо звука.")
