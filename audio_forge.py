import torch
from TTS.api import TTS
import os
import sys

def generate_audio(text_prompt, output_filename):
    print(":mushroom: Audio Forge booting up....Checking for GPU....")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f":star: Using device: {device.upper()}")

    script_dir = os.path.dirname(os.path.abspath(__file__))

    speaker_wav_path = os.path.join(script_dir, "perfect_clone.wav")

    if not os.path.exists(speaker_wav_path):
        print(f"Error: Can't find your donor voice at {speaker_wav_path}")
        sys.exit(1)

    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)

    print(f"Cloning voice and reading: {text_prompt}")

    
    tts.tts_to_file(
        text=text_prompt, 
        speaker_wav=speaker_wav_path,
        file_path=output_filename,
        language="en"
    )

    print(f":clapper: DONE! Audio saved to: {output_filename}")

if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Error: You forgot to tell me what to say!")
        print('Usage: python audio_forge.py "Hello this is my cloned voice.')
        sys.exit(1)

    user_text = sys.argv[1]

    current_directory = os.getcwd()
    final_save_path = os.path.join(current_directory, "spore_audio.wav")

    generate_audio(user_text, final_save_path)
    