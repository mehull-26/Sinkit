import re
import pygame
import cv2
import numpy as np
import time
import threading
from pydub import AudioSegment
import speech_recognition as sr
import difflib
import sys
from moviepy.editor import VideoFileClip

def extract_audio_from_video(video_file_path, audio_file_path):
    # Load the video file
    video = VideoFileClip(video_file_path)
    
    # Extract audio
    audio = video.audio
    
    # Write the audio to a file
    audio.write_audiofile(audio_file_path, codec='mp3')  # You can specify other formats as well
    
    # Close the video and audio objects
    audio.close()
    video.close()

running = True

def timestamp_to_ms(timestamp):
    hours, minutes, seconds_milliseconds = timestamp.split(':')
    seconds, milliseconds = seconds_milliseconds.split(',')
    return (int(hours) * 3600 + int(minutes) * 60 + int(seconds)) * 1000 + int(milliseconds)

def ms_to_timestamp(ms):
    hours = ms // 3600000
    ms %= 3600000
    minutes = ms // 60000
    ms %= 60000
    seconds = ms // 1000
    milliseconds = ms % 1000
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"

def extract_timestamps_and_texts(srt_file_path):
    timestamps_and_texts = []
    with open(srt_file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
        i = 0
        while i < len(lines):
            if re.match(r'\d+', lines[i].strip()):
                i += 1
                match = re.match(r'(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})', lines[i].strip())
                if match:
                    start_ms = timestamp_to_ms(match.group(1))
                    end_ms = timestamp_to_ms(match.group(2))
                    i += 1
                    subtitle_text = ""
                    while i < len(lines) and lines[i].strip():
                        subtitle_text += " " + lines[i].strip()
                        i += 1
                    timestamps_and_texts.append((start_ms, end_ms, subtitle_text.strip()))
            i += 1
    return timestamps_and_texts

def calculate_match_ratio(text1, text2):
    return difflib.SequenceMatcher(None, text1, text2).ratio()

def transcribe_audio_segments(audio_file_path, timestamps_and_texts, srt_file_path):
    recognizer = sr.Recognizer()
    audio = AudioSegment.from_file(audio_file_path)

    with open(srt_file_path, 'r', encoding='utf-8') as file:
        srt_lines = file.readlines()

  
    for i, (start, end, subtitle_text) in enumerate(timestamps_and_texts):
        best_match_ratio = 0
        best_start = start
        best_end = end
            
        if (running):
            for offset in range(-3, 4):
                adjusted_start = start + offset * 1000
                adjusted_end = end + offset * 1000
                segment = audio[adjusted_start:adjusted_end]
                segment.export("temp.wav", format="wav")
                with sr.AudioFile("temp.wav") as source:
                    audio_data = recognizer.record(source)
                    try:
                        text = recognizer.recognize_google(audio_data)
                        match_ratio = calculate_match_ratio(subtitle_text, text)
                        if match_ratio > best_match_ratio:
                            best_match_ratio = match_ratio
                            best_start = adjusted_start
                            best_end = adjusted_end
                    except sr.UnknownValueError:
                        continue
                    except sr.RequestError:
                        continue
            
                print(f"Best end timestamp for segment {i}: {best_end}")
    
            srt_lines[i * 5 + 1] = f"{ms_to_timestamp(best_start)} --> {ms_to_timestamp(best_end)}\n"
            with open(srt_file_path, 'w', encoding='utf-8') as file:
                file.writelines(srt_lines)
        print("written")


def overlay_text_on_video(video_path, audio_path, srt_file_path):
    pygame.init()
    pygame.mixer.init()
    clock = pygame.time.Clock()
    pygame.mixer.music.load(audio_path)
    pygame.mixer.music.play()
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Error: Could not open video.")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    screen = pygame.display.set_mode((width, height))

    # State for play/pause
    is_playing = True
    current_frame = 0  # Track the current frame index

    def display_text(screen, text, font, color=(255, 255, 255)):
        text_surface = font.render(text, True, color)
        text_rect = text_surface.get_rect(center=(screen.get_width() // 2, screen.get_height() - 50))
        screen.blit(text_surface, text_rect)

    def read_srt_file(srt_file_path):
        subtitles = []
        with open(srt_file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            i = 0
            while i < len(lines):
                if re.match(r'\d+', lines[i].strip()):
                    i += 1
                    match = re.match(r'(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})', lines[i].strip())
                    if match:
                        start_ms = timestamp_to_ms(match.group(1))
                        end_ms = timestamp_to_ms(match.group(2))
                        i += 1
                        subtitle_text = ""
                        while i < len(lines) and lines[i].strip():
                            subtitle_text += " " + lines[i].strip()
                            i += 1
                        subtitles.append((start_ms / 1000, (end_ms - start_ms) / 1000, subtitle_text.strip()))
                i += 1
        return subtitles

    global running
    
    while running:
        if is_playing:
            ret, frame = cap.read()
            if not ret:
                break
            current_frame += 1  # Increment frame count
        else:
            # When paused, do not read new frames, keep showing the current frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)  # Stay on the current frame
        
        if is_playing:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = np.rot90(frame)
            frame = np.flipud(frame)
        frame_surface = pygame.surfarray.make_surface(frame)
        screen.fill((0, 0, 0))
        screen.blit(frame_surface, (0, 0))
        current_time = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
        subtitles = read_srt_file(srt_file_path)
        font = pygame.font.Font(None, 16)  # Smaller text size
        for start_time, duration, text in subtitles:
            if start_time <= current_time <= (start_time + duration):
                display_text(screen, text, font)
        pygame.display.flip()

        # Check for play/pause toggle
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:  # Space bar to toggle play/pause
                    if is_playing:
                        pygame.mixer.music.pause()
                        is_playing = False
                    else:
                        pygame.mixer.music.unpause()
                        is_playing = True

        # Ensure proper FPS control
        clock.tick(fps)

    cap.release()
    pygame.quit()



if __name__ == "__main__":
    srt_file_path = sys.argv[1]  # First argument is SRT file path
    video_file_path = sys.argv[2] # Second argument is Video file path
    audio_file_path = 'audio.mp3'
    extract_audio_from_video(video_file_path, audio_file_path)

    timestamps_and_texts = extract_timestamps_and_texts(srt_file_path)
    
    # Start the transcription in a separate thread
    transcription_thread = threading.Thread(target=transcribe_audio_segments, args=(audio_file_path, timestamps_and_texts, srt_file_path))
    transcription_thread.start()
    
    # Print the current time and wait for 30 seconds before starting the video playback
    print(f"Waiting for 30 seconds before starting the video playback. Current time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    time.sleep(100)
    
    # Start the video playback and overlay text
    overlay_text_on_video(video_file_path, audio_file_path, srt_file_path)
    
    # Wait for the transcription thread to finish
    transcription_thread.join()
    
    print("Playback completed.")