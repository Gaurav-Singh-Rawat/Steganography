# Steganography Web App

A Flask-based web application for hiding and extracting secret messages in images and audio (WAV) files using steganography.

## Features

- **Image Steganography:** Hide and reveal messages in PNG, BMP, or JPG images.
- **Audio Steganography:** Hide and reveal messages in WAV audio files.
- **Modern UI:** Responsive, user-friendly interface with drag-and-drop support.
- **Password Option:** (Image only) Optionally protect hidden messages with a password.
- **Capacity Check:** See how much text you can hide in your image.

## Project Structure

```
app.py
audio.py
static/
    audio.js
    favicon.svg
    script.js
    style.css
templates/
    audio.html
    home.html
    image.html
```

## Requirements

- Python 3.7+
- Flask
- Pillow
- numpy

Install dependencies:
```sh
pip install Flask Pillow numpy
```

## Running the App

1. Clone this repository:
    ```sh
    git clone https://github.com/AayushiSharma-10/steganography.git
    cd steganography-project
    ```

2. Run the Flask server:
    ```sh
    python app.py
    ```

3. Open your browser and go to [http://127.0.0.1:5000](http://127.0.0.1:5000)

## Usage

- **Image Steganography:**  
  Go to the "Image Steganography" tab, upload an image, enter your secret message, and download the encoded image. To decode, upload the encoded image and reveal the message.

- **Audio Steganography:**  
  Go to the "Audio Steganography" tab, upload a WAV file, enter your secret message, and download the encoded audio. To decode, upload the encoded audio file and reveal the message.

## File Descriptions

- [`app.py`](app.py): Main Flask server with all routes and steganography logic.
- [`audio.py`](audio.py): Standalone audio steganography class (not required for web app).
- [`static/`](static/): Frontend JS, CSS, and assets.
- [`templates/`](templates/): HTML templates for the web interface.

## License

This project is for educational purposes.

---

**Made with ❤️ by team Silentcipher**
