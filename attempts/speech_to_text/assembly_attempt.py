import assemblyai as aai

# API key
aai.settings.api_key = "00d0fca398c54f68a7d36c93a3371fdf"

FILE = "../../src/audio.wav"
config = aai.TranscriptionConfig(language_code="ru")
transcriber = aai.Transcriber(config=config)
transcript = transcriber.transcribe(FILE)

if transcript.status == aai.TranscriptStatus.error:
    print(transcript.error)
else:
    print(transcript.text)
