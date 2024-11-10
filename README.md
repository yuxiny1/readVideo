readVideo

Convert videos into text
This project allows you to transcribe videos into text, so you can consume video content in written form, saving time and effort.

Features

	•	Automatically downloads YouTube videos using yt-dlp.
	•	Converts video audio to text using OpenAI transcription API.
	•	Provides a FastAPI endpoint to trigger video downloads and transcriptions.
	•	Simple configuration with OAuth for YouTube API access.
	
	Getting Started
	
	Prerequisites

	1.	YouTube API Access: Obtain a YouTube API key and set up OAuth2 credentials. You’ll need this for the app to access and download YouTube videos.
	2.	Define Download Location: Set your preferred download directory within the code.
	3.	Install Dependencies: Install required libraries from requirements.txt.
	
	Installation
	git clone <repository-url>
	cd readVideo

	conda create -n "readvideo"
  	conda activate readvideo

	2.	Install Requirements:  pip install -r requirements.txt

	pip install -r requirements.txt

Configuration

	1.	API Keys and OAuth Setup:
	•	Follow the instructions in the google_auth.py file to authenticate with Google’s OAuth2.
	•	Save the OAuth tokens and API keys in a token.json file for persistent access.
	2.	Download Location: In download_video, change the download path variable to your preferred directory.
	
	Running the Application
	Start the FastAPI server:
	uvicorn main:app --reload


Usage

	1.	Use curl or another HTTP client to send the video URL to the FastAPI endpoint:

	curl -X POST "http://localhost:8000/process_video/" -H "Content-Type: application/json" -d '{"task_id": "1", "url": "<VIDEO_URL>"}'

	2.	Check task status:
	curl -X GET "http://localhost:8000/task_status/1"

project Structure

	•	google_auth.py: Handles Google OAuth2 setup and token management.
	•	yt_dl.py: Uses yt-dlp to download videos.
	•	audioTranscription.py: Handles audio extraction and transcription using OpenAI’s API.
	•	app.py: FastAPI app with endpoints to process videos and check task status.
