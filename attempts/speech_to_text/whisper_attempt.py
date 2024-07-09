import whisper

model = whisper.load_model("base")
# help(model.transcribe)
result = model.transcribe("audio.mp3")
print(result["text"])
