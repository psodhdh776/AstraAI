"""Generate shorter voiceover for Astra AI intro video."""
import pyttsx3

OUTPUT = "C:/Users/admin/Desktop/AstraAI_v2.0_Release/voiceover.wav"

# Short phrases to fit ~30 seconds at rate 200
NARRATION = [
    "Astra AI — твой ассистент на Windows.",
    "Живое общение как с другом.",
    "Голосовое управление — просто говори.",
    "Команды: браузер, скриншот, погода.",
    "Gemini AI — любые вопросы и код.",
    "Заметки и напоминания.",
    "Генерация изображений по описанию.",
    "Ctrl+Alt+A — начни прямо сейчас.",
]

full_text = ". ".join(NARRATION) + "."

print(f"Generating voiceover ({len(NARRATION)} lines)...")

engine = pyttsx3.init()
engine.setProperty("rate", 155)
engine.setProperty("volume", 1.0)

for v in engine.getProperty("voices"):
    if "russian" in v.name.lower():
        engine.setProperty("voice", v.id)
        print(f"Using voice: {v.name}")
        break

engine.save_to_file(full_text, OUTPUT)
engine.runAndWait()
engine.stop()

# Check duration
import wave, contextlib
with contextlib.closing(wave.open(OUTPUT, 'r')) as f:
    frames = f.getnframes()
    rate = f.getframerate()
    duration = frames / float(rate)
    print(f"Duration: {duration:.1f}s")
