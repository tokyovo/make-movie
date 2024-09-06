from fastapi import FastAPI
from pydantic import BaseModel
import requests
from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip
import os
from uuid import uuid4

app = FastAPI()

# Define the input data model
class InputData(BaseModel):
    image_urls: list[str]
    total_duration: int  # Total duration of the entire video (in seconds)
    audio_url: str

# Define the output data model
class OutputData(BaseModel):
    message: str
    video_url: str

# Helper function to download a file from a URL
def download_file(url, dest_path):
    response = requests.get(url)
    if response.status_code == 200:
        with open(dest_path, 'wb') as f:
            f.write(response.content)
    else:
        raise Exception(f"Failed to download file from {url}")

# Define the API endpoint to create a video
@app.post("/create_video", response_model=OutputData)
async def create_video(input_data: InputData):
    # Directory to save the temporary files under /temp_videos
    temp_dir = "/temp_videos"
    os.makedirs(temp_dir, exist_ok=True)

    # Step 1: Download the images from the provided URLs
    image_clips = []
    num_images = len(input_data.image_urls)
    duration_per_image = input_data.total_duration / num_images  # Divide total duration equally among the images

    for idx, image_url in enumerate(input_data.image_urls):
        image_path = os.path.join(temp_dir, f"image_{idx}.jpg")
        download_file(image_url, image_path)
        clip = ImageClip(image_path, duration=duration_per_image)
        image_clips.append(clip)

    # Step 2: Create a video from the image clips
    video = concatenate_videoclips(image_clips, method="compose")

    # Step 3: Download the audio file and add it to the video
    audio_path = os.path.join(temp_dir, "audio.mp3")
    download_file(input_data.audio_url, audio_path)
    audio = AudioFileClip(audio_path)

    video = video.set_audio(audio)

    # Step 4: Export the final video
    output_video_filename = f"{str(uuid4())}_output_video.mp4"
    output_video_path = os.path.join(temp_dir, output_video_filename)
    video.write_videofile(output_video_path, fps=24)

    # Step 5: Return an example video URL (for now)
    example_url = f"https://example.com/videos/{output_video_filename}"

    return OutputData(
        message="Video created successfully",
        video_url=example_url
    )
