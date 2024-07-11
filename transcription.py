from speechkit import model_repository, configure_credentials, creds
from speechkit.stt import AudioProcessingType
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

    # Задайте настройки распознавания.
    model.model = 'general'
    model.language = 'ru-RU'
    model.audio_processing_type = AudioProcessingType.Full

    # Распознавание речи в указанном аудиофайле и вывод результатов в консоль.
    await update.message.reply_text("Транскрибация...")
    result = model.transcribe_file(audio_file_path)
    await update.message.reply_text("Транскрибация завершена.")
    for c, res in enumerate(result):
        print('=' * 80)
        print(f'channel: {c}\n\nraw_text:\n{res.raw_text}\n\nnorm_text:\n{res.normalized_text}\n')
        if res.has_utterances():
            print('utterances:')
            for utterance in res.utterances:
                print(utterance)
