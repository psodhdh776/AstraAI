"""Merge intro video with voiceover audio."""
import subprocess
import imageio_ffmpeg

VIDEO = "C:/Users/admin/Desktop/AstraAI_v2.0_Release/intro.mp4"
AUDIO = "C:/Users/admin/Desktop/AstraAI_v2.0_Release/voiceover.wav"
OUTPUT = "C:/Users/admin/Desktop/AstraAI_v2.0_Release/intro_final.mp4"

ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

cmd = [
    ffmpeg,
    "-i", VIDEO,
    "-i", AUDIO,
    "-c:v", "libx264",
    "-c:a", "aac",
    "-map", "0:v:0",
    "-map", "1:a:0",
    "-shortest",
    "-y",
    OUTPUT,
]

print("Merging video + audio...")
result = subprocess.run(cmd, capture_output=True, text=True)
if result.returncode == 0:
    print(f"Done! Saved to intro_final.mp4")
else:
    print("ERROR:", result.stderr[:500])
