from fastapi import FastAPI
from pydantic import BaseModel
import requests
from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip
import os
from uuid import uuid4
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url

app = FastAPI()

# Get Cloudinary credentials from environment variables
CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
API_KEY = os.getenv("CLOUDINARY_API_KEY")
API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

# Cloudinary Configuration
cloudinary.config( 
    cloud_name=CLOUD_NAME, 
    api_key=API_KEY, 
    api_secret=API_SECRET,
    secure=True
)

# Define the input data model
class InputData(BaseModel):
    image_urls: list[str]
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

    # Step 1: Download the audio file and get its duration
    audio_path = os.path.join(temp_dir, "audio.mp3")
    download_file(input_data.audio_url, audio_path)
    audio = AudioFileClip(audio_path)
    audio_duration = audio.duration  # Get the duration of the audio file

    # Step 2: Download the images from the provided URLs
    image_clips = []
    num_images = len(input_data.image_urls)
    duration_per_image = audio_duration / num_images  # Divide the audio duration equally among the images

    for idx, image_url in enumerate(input_data.image_urls):
        image_path = os.path.join(temp_dir, f"image_{idx}.jpg")
        download_file(image_url, image_path)
        clip = ImageClip(image_path, duration=duration_per_image)
        image_clips.append(clip)

    # Step 3: Create a video from the image clips
    video = concatenate_videoclips(image_clips, method="compose")

    # Step 4: Add the audio file to the video
    video = video.set_audio(audio)

    # Step 5: Export the final video to a temporary file
    output_video_filename = f"{str(uuid4())}_output_video.mp4"
    output_video_path = os.path.join(temp_dir, output_video_filename)
    video.write_videofile(output_video_path, fps=24)

    # Step 6: Upload the video to Cloudinary
    upload_result = cloudinary.uploader.upload(output_video_path, resource_type="video", public_id=output_video_filename)
    video_url = upload_result["secure_url"]  # Get the secure URL of the uploaded video

    # Step 7: Return the Cloudinary video URL
    return OutputData(
        message="Video created successfully",
        video_url=video_url
    )
