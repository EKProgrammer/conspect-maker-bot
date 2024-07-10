from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from subprocess import check_output, CalledProcessError
import json

from pydub import AudioSegment

from pytube import YouTube
from pytube.exceptions import RegexMatchError

import io
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

import requests
from urllib.parse import urlencode


# from speech_to_text import recognition


async def beginning_of_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Посылка первого сообщения пользователю для запроса"""
    await update.message.reply_text("Пришлите аудио, видео или ссылку верного формата.")
    return 1


async def has_audio_streams(file_path) -> int:
    """Проверка наличия аудиопотока"""
    try:
        command = ['ffprobe', '-show_streams', '-print_format', 'json', file_path]
        output = check_output(command)
        parsed = json.loads(output)
        streams = parsed['streams']
        audio_streams = list(filter((lambda x: x['codec_type'] == 'audio'), streams))
        return len(audio_streams)
    except CalledProcessError:
        return -1


async def cut_audio_from_file(file_path) -> None:
    """Выделение аудиодорожки из видео"""
    audio = AudioSegment.from_file(file_path)
    audio.export("src/audio.mp3", format="mp3")


async def audio_processing_with_error_output(update, context, filename):
    """Обработка аудио с выводом возможных ошибок"""
    count_audio_streams = await has_audio_streams(filename)
    if count_audio_streams > 0:
        await cut_audio_from_file(filename)
        context.user_data["input_audio_file_path"] = "src/audio.mp3"
    elif count_audio_streams == -1:
        await update.message.reply_text("Файл не может быть декодирован, возможно он повреждён. Отправьте другой файл.")
        return 1
    else:
        await update.message.reply_text("Файл не имеет аудиопотока. Отправьте другой файл.")
        return 1
    await update.message.reply_text("Скачивание завершено.")


async def downloading_from_telegram(data_instance) -> None:
    """Загрузка файла из Telegram"""
    file_instance = await data_instance.get_file()
    await file_instance.download_to_drive(custom_path="src/" + data_instance.file_name)


async def detection_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Проверка корректности запроса и выбор формата конспекта"""
    print("============Debug============")
    print("audio", update.message.audio)
    print("video", update.message.video)
    print("document", update.message.document)
    print("text", update.message.text)
    print("message", update.message)
    print("=============================")

    # telegram audio
    if update.message.audio is not None:
        if update.message.audio.file_size <= 10 * 1024 * 1024 * 1024:
            await update.message.reply_text("Скачивание...")
            await downloading_from_telegram(update.message.audio)
            await update.message.reply_text("Скачивание завершено.")
            context.user_data["input_audio_file_path"] = "src/" + update.message.audio.file_name
        else:
            await update.message.reply_text(
                "Файл имеет слишком большой объём. Существует ограничение на файл в 10 Гбайт. Отправьте файл меньшего размера.")
            return 1

    # telegram video
    elif update.message.video is not None:
        if update.message.video.file_size <= 10 * 1024 * 1024 * 1024:
            await update.message.reply_text("Скачивание...")
            await downloading_from_telegram(update.message.video)
            await cut_audio_from_file("src/" + update.message.video.file_name)
            context.user_data["input_audio_file_path"] = "src/audio.mp3"
            await update.message.reply_text("Скачивание завершено.")
        else:
            await update.message.reply_text(
                "Файл имеет слишком большой объём. Существует ограничение на размер файла в 10 Гбайт. Отправьте файл меньшего размера.")
            return 1

    # telegram document
    elif update.message.document is not None:
        if update.message.document.file_size <= 10 * 1024 * 1024 * 1024:
            await update.message.reply_text("Скачивание...")
            await downloading_from_telegram(update.message.document)
            await audio_processing_with_error_output(update, context, "src/" + update.message.document.file_name)
        else:
            await update.message.reply_text(
                "Файл имеет слишком большой объём. Существует ограничение на размера файла в 10 Гбайт. Отправьте файл меньшего размера.")
            return 1

    # url case
    elif update.message.text is not None:
        if update.message.text[:32] == "https://www.youtube.com/watch?v=":
            # Загрузка файла с Youtube
            try:
                yt = YouTube(update.message.text)
                stream = yt.streams.get_audio_only()
                await update.message.reply_text("Скачивание...")
                stream.download(filename="src/audio.mp3")
                context.user_data["input_audio_file_path"] = "src/audio.mp3"
                await update.message.reply_text("Скачивание завершено.")
            except RegexMatchError:
                await update.message.reply_text("Некорректная ссылка. Обратитесь в справку.")
                return 1

        elif update.message.text[:32] == "https://drive.google.com/file/d/":
            # Загрузка файла с Google.Drive
            service = build("drive", "v3",
                            developerKey="AIzaSyBZ6SsaeN3pr9eassB19qBXKY4tqrY2UdI")
            file_id = update.message.text[32:].split('/')[0]
            # Определяем название и вес файла
            try:
                information = service.files().get(fileId=file_id, fields="name,size").execute()
            except HttpError as error:
                await update.message.reply_text(
                    f"Http ошибка: {error.status_code}. Проверьте, что в настройках доступа к файлу статус (\"Все, у кого есть ссылка\") и url указан корректно.")
                print(error)
                return 1
            # Проверка веса файла
            if int(information["size"]) <= 10 * 1024 * 1024 * 1024:
                try:
                    # Загрузка файла с сервера
                    request = service.files().get_media(fileId=file_id)
                    file = io.BytesIO()
                    downloader = MediaIoBaseDownload(file, request)
                    done = False
                    await update.message.reply_text("Скачивание...")
                    # Скачивание по чанкам
                    while done is False:
                        status, done = downloader.next_chunk()
                    with open("src/" + information["name"], "wb") as f:
                        f.write(file.getvalue())
                except HttpError as error:
                    await update.message.reply_text(f"Http ошибка: {error.status_code}.")
                    print(error)
                    return 1
                await audio_processing_with_error_output(update, context, "src/" + information["name"])
            else:
                await update.message.reply_text(
                    "Файл имеет слишком большой объём. Существует ограничение на размер файла в 10 Гбайт. Отправьте файл меньшего размера.")
                return 1

        elif update.message.text[:23] == "https://disk.yandex.ru/":
            # Загрузка файла с Yandex.Disk
            information = requests.get("https://compute.api.cloud.yandex.net/compute/v1/filesystems/" +
                                       update.message.text[25:]).json()
            print(information)
            if int(information["size"]) <= 10 * 1024 * 1024 * 1024:
                base_url = 'https://cloud-api.yandex.net/v1/disk/public/resources/download?'
                # Получаем загрузочную ссылку
                final_url = base_url + "public_key=" + update.message.text[23:]
                # public_key = update.message.text[23:]
                # final_url = base_url + urlencode(dict(public_key=public_key))
                response = requests.get(final_url)
                download_url = response.json()['href']
                # Загружаем файл и сохраняем его
                download_response = requests.get(download_url)
                await update.message.reply_text("Скачивание завершено.")
                with open("src/" + information["name"], 'wb') as f:
                    f.write(download_response.content)
                await audio_processing_with_error_output(update, context, "src/" + information["name"])
            else:
                await update.message.reply_text(
                    "Файл имеет слишком большой объём. Существует ограничение на размер файла в 10 Гбайт. Отправьте файл меньшего размера.")
                return 1

        else:
            # Сообщение об ошибке
            await update.message.reply_text("Некорректная ссылка. Обратитесь в справку.")
            return 1

    # Открытие клавиатуры пользователю
    reply_keyboard = [["txt", "markdown", "html", "latex"]]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Выберете формат конспекта.",
                                    reply_markup=markup)
    return 2


async def set_output_format(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Установить значение формата конспекта"""
    print("call recognition")
    await recognition(context.user_data["input_audio_file_path"], update.message.text)
    return ConversationHandler.END
