from fastapi import FastAPI
from pydantic import BaseModel
import requests
from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip
import os
from uuid import uuid4
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()

# Get Cloudinary credentials from environment variables
CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
API_KEY = os.getenv("CLOUDINARY_API_KEY")
API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

# Log Cloudinary configuration
logger.debug(f"Cloudinary configuration - Cloud Name: {CLOUD_NAME}, API Key: {API_KEY}")

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
    logger.debug(f"Downloading file from {url} to {dest_path}")
    response = requests.get(url)
    if response.status_code == 200:
        with open(dest_path, 'wb') as f:
            f.write(response.content)
        logger.debug(f"File downloaded successfully: {dest_path}")
    else:
        logger.error(f"Failed to download file from {url}")
        raise Exception(f"Failed to download file from {url}")

# Define the API endpoint to create a video
@app.post("/create_video", response_model=OutputData)
async def create_video(input_data: InputData):
    logger.info("Received request to create video")
    
    # Directory to save the temporary files under /temp_videos
    temp_dir = "/temp_videos"
    os.makedirs(temp_dir, exist_ok=True)
    logger.debug(f"Temporary directory created: {temp_dir}")

    # Step 1: Download the audio file and get its duration
    try:
        audio_path = os.path.join(temp_dir, "audio.mp3")
        logger.debug(f"Downloading audio from {input_data.audio_url}")
        download_file(input_data.audio_url, audio_path)
        audio = AudioFileClip(audio_path)
        audio_duration = audio.duration  # Get the duration of the audio file
        logger.debug(f"Audio duration: {audio_duration} seconds")
    except Exception as e:
        logger.error(f"Error while processing audio: {e}")
        raise e

    # Step 2: Download the images from the provided URLs
    image_clips = []
    num_images = len(input_data.image_urls)
    logger.debug(f"Number of images: {num_images}")
    duration_per_image = audio_duration / num_images  # Divide the audio duration equally among the images
    logger.debug(f"Duration per image: {duration_per_image} seconds")

    for idx, image_url in enumerate(input_data.image_urls):
        try:
            image_path = os.path.join(temp_dir, f"image_{idx}.jpg")
            logger.debug(f"Downloading image {idx + 1} from {image_url}")
            download_file(image_url, image_path)
            clip = ImageClip(image_path, duration=duration_per_image)
            image_clips.append(clip)
            logger.debug(f"Image {idx + 1} added to video clip list")
        except Exception as e:
            logger.error(f"Error while downloading or processing image {idx + 1}: {e}")
            raise e

    # Step 3: Create a video from the image clips
    try:
        logger.debug("Concatenating video clips")
        video = concatenate_videoclips(image_clips, method="compose")
        video = video.set_audio(audio)
    except Exception as e:
        logger.error(f"Error while creating the video: {e}")
        raise e

    # Step 4: Export the final video to a temporary file
    output_video_filename = f"{str(uuid4())}_output_video.mp4"
    output_video_path = os.path.join(temp_dir, output_video_filename)
    try:
        logger.debug(f"Exporting video to {output_video_path}")
        video.write_videofile(output_video_path, fps=24)
        logger.info(f"Video exported successfully: {output_video_path}")
    except Exception as e:
        logger.error(f"Error while exporting the video: {e}")
        raise e

    # Step 5: Upload the video to Cloudinary
    try:
        logger.debug(f"Uploading video to Cloudinary: {output_video_path}")
        upload_result = cloudinary.uploader.upload(output_video_path, resource_type="video", public_id=output_video_filename)
        video_url = upload_result["secure_url"]
        logger.info(f"Video uploaded successfully to Cloudinary: {video_url}")
    except Exception as e:
        logger.error(f"Error while uploading video to Cloudinary: {e}")
        raise e

    # Step 6: Return the Cloudinary video URL
    return OutputData(
        message="Video created successfully",
        video_url=video_url
    )
