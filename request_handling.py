import telegram.error
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

import subprocess
import json

from pydub import AudioSegment

import isodate

import io
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

import requests

from transcription import recognition

import shutil
import os

from config import YOUTUBE_API_KEY, GOOGLE_DRIVE_API_KEY

# константы
WEIGHT_FILE_LIMIT = 5 * 1024 * 1024 * 1024
FILE_DURATION_LIMIT = 2 * 60 * 60


async def beginning_of_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Посылка первого сообщения пользователю для запроса"""
    await update.message.reply_text("Пришлите аудио, видео или ссылку верного формата.")
    return 1


async def has_audio_streams(file_path) -> int:
    """Проверка наличия аудиопотока"""
    try:
        command = ['ffprobe', '-show_streams', '-print_format', 'json', file_path]
        output = subprocess.check_output(command)
        parsed = json.loads(output)
        streams = parsed['streams']
        audio_streams = list(filter((lambda x: x['codec_type'] == 'audio'), streams))
        return len(audio_streams)
    except subprocess.CalledProcessError:
        return -1


async def cut_audio_from_file(file_path: str) -> None:
    """Выделение аудиодорожки из видео"""
    audio = AudioSegment.from_file(file_path)
    audio.export("src/audio.mp3", format="mp3")


async def audio_processing_with_error_output(update: Update, context: ContextTypes.DEFAULT_TYPE, filename: str):
    """Обработка аудио с выводом возможных ошибок"""
    count_audio_streams = await has_audio_streams(filename)

    if count_audio_streams > 0:
        audio_file = AudioSegment.from_file(filename)
        duration = audio_file.duration_seconds
        print(duration)
        if duration > FILE_DURATION_LIMIT:
            await print_max_duration_error(update)
            return 1

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


async def print_max_weight_error(update):
    await update.message.reply_text(
        "Файл имеет слишком большой объём. Существует ограничение на размер файла в 5 Гбайт. Отправьте файл меньшего размера.")


async def print_max_duration_error(update):
    await update.message.reply_text(
        "Файл имеет слишком большую длительность. Существует ограничение на длительность файла в 2 часа. Отправьте файл меньшей длительности.")


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
        if update.message.audio.file_size <= WEIGHT_FILE_LIMIT:
            if update.message.audio.duration <= FILE_DURATION_LIMIT:
                await update.message.reply_text("Скачивание...")
                try:
                    await downloading_from_telegram(update.message.audio)
                except (telegram.error.TelegramError, telegram.error.TimedOut):
                    await update.message.reply_text("Ошибка Telegram. Попробуйте ещё раз отправить запрос.")
                    return 1
                await update.message.reply_text("Скачивание завершено.")
                context.user_data["input_audio_file_path"] = "src/" + update.message.audio.file_name
            else:
                await print_max_duration_error(update)
                return 1
        else:
            await print_max_weight_error(update)
            return 1

    # telegram video
    elif update.message.video is not None:
        if update.message.video.file_size <= WEIGHT_FILE_LIMIT:
            if update.message.video.duration <= FILE_DURATION_LIMIT:
                await update.message.reply_text("Скачивание...")
                try:
                    await downloading_from_telegram(update.message.video)
                except (telegram.error.TelegramError, telegram.error.TimedOut):
                    await update.message.reply_text("Ошибка Telegram. Попробуйте ещё раз отправить запрос.")
                    return 1
                await cut_audio_from_file("src/" + update.message.video.file_name)
                context.user_data["input_audio_file_path"] = "src/audio.mp3"
                await update.message.reply_text("Скачивание завершено.")
            else:
                await print_max_duration_error(update)
                return 1
        else:
            await print_max_weight_error(update)
            return 1

    # telegram document
    elif update.message.document is not None:
        if update.message.document.file_size <= WEIGHT_FILE_LIMIT:
            await update.message.reply_text("Скачивание...")
            # try:
            await downloading_from_telegram(update.message.document)
            # except (telegram.error.TelegramError, telegram.error.TimedOut) as err:
            #     print(err)
            #     await update.message.reply_text("Ошибка Telegram. Попробуйте ещё раз отправить запрос.")
            #     return 1
            result = await audio_processing_with_error_output(
                update, context, "src/" + update.message.document.file_name)
            if result == 1:
                return result
        else:
            await print_max_weight_error(update)
            return 1

    # В случае, если пользователь отправил ссылку
    elif update.message.text is not None:
        # Загрузка файла с Youtube
        if update.message.text[:32] == "https://www.youtube.com/watch?v=":
            url = f"https://www.googleapis.com/youtube/v3/videos?id={update.message.text[32:]}&part=contentDetails&key={YOUTUBE_API_KEY}"
            responce = requests.get(url).json()
            if not responce["items"]:
                await update.message.reply_text("Некорректная ссылка или видео в ограниченном доступе.")
                return 1
            duration = isodate.parse_duration(responce["items"][0]["contentDetails"]["duration"])
            video_dur = duration.total_seconds()

            if video_dur <= FILE_DURATION_LIMIT:
                try:
                    # Run yt-dlp command
                    command = ["yt-dlp", "-f", "bestaudio", "-o", "src/audio.mp3", update.message.text]
                    await update.message.reply_text("Скачивание...")
                    subprocess.run(command, check=True)
                    context.user_data["input_audio_file_path"] = "src/audio.mp3"
                    await update.message.reply_text("Скачивание завершено.")
                except subprocess.CalledProcessError:
                    await update.message.reply_text("Ошибка скачивания файла. Попробуйте ещё раз отправить запрос.")
                    return 1
            else:
                await print_max_duration_error(update)
                return 1

        # Загрузка файла с Google.Drive
        elif update.message.text[:32] == "https://drive.google.com/file/d/":
            service = build("drive", "v3", developerKey=GOOGLE_DRIVE_API_KEY)
            file_id = update.message.text[32:].split('/')[0]
            # Определяем название и вес файла
            try:
                information = service.files().get(fileId=file_id, fields="name,size").execute()
            except HttpError as error:
                await update.message.reply_text(
                    f"Http ошибка: {error.status_code}. Проверьте, что в настройках доступа к файлу статус (\"Все, у кого есть ссылка\") и url указан корректно.")
                return 1

            # Проверка размера файла
            if int(information["size"]) <= WEIGHT_FILE_LIMIT:
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
                    return 1

                result = await audio_processing_with_error_output(update, context, "src/" + information["name"])
                if result == 1:
                    return result
            else:
                await print_max_weight_error(update)
                return 1

        # Загрузка файла с Yandex.Disk
        elif update.message.text[:23] == "https://disk.yandex.ru/":
            information = requests.get("https://cloud-api.yandex.net/v1/disk/public/resources?public_key=" +
                                       update.message.text + "&fields=name,size").json()
            if int(information["size"]) <= WEIGHT_FILE_LIMIT:
                base_url = 'https://cloud-api.yandex.net/v1/disk/public/resources/download?'
                # Получаем загрузочную ссылку
                final_url = base_url + "public_key=" + update.message.text
                response = requests.get(final_url)
                download_url = response.json()['href']

                # Загружаем файл и сохраняем его
                await update.message.reply_text("Скачивание...")
                download_response = requests.get(download_url)
                await update.message.reply_text("Скачивание завершено.")
                with open("src/" + information["name"], 'wb') as f:
                    f.write(download_response.content)
                result = await audio_processing_with_error_output(update, context, "src/" + information["name"])
                if result == 1:
                    return result
            else:
                await print_max_weight_error(update)
                return 1

        else:
            # Сообщение об ошибке
            await update.message.reply_text("Некорректная ссылка. Обратитесь в справку.")
            return 1

    # Открытие клавиатуры пользователю
    reply_keyboard = [["txt", "markdown", "html", "latex"]]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Выберете формат конспекта.", reply_markup=markup)
    return 2


async def set_output_format(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Установить значение формата конспекта"""
    try:
        await recognition(update, context.user_data["input_audio_file_path"], update.message.text)
    except requests.exceptions.JSONDecodeError:
        await update.message.reply_text("Ошибка запроса к YANDEX GPT.")
    folder_path = "src"
    shutil.rmtree(folder_path)
    os.mkdir(folder_path)
    return ConversationHandler.END
