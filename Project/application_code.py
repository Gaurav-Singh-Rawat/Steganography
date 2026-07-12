from flask import Flask, render_template, request, send_file, jsonify
from PIL import Image
import logging
from io import BytesIO
import secrets
import wave
import numpy as np

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- Image Steganography Logic ----------
def encode_message(img, message, password=None):
    message += chr(0)
    binary_msg = ''.join(f"{ord(c):08b}" for c in message)
    msg_len = len(binary_msg)
    if img.mode != 'RGB':
        img = img.convert('RGB')
    width, height = img.size
    max_bits = width * height * 3
    if msg_len > max_bits:
        raise ValueError(f"Message is too long for this image. Maximum characters allowed: {max_bits // 8}")
    pixels = list(img.getdata())
    encoded_pixels = []
    msg_index = 0
    for pixel in pixels:
        r, g, b = pixel
        if msg_index < msg_len:
            r = (r & ~1) | int(binary_msg[msg_index])
            msg_index += 1
        if msg_index < msg_len:
            g = (g & ~1) | int(binary_msg[msg_index])
            msg_index += 1
        if msg_index < msg_len:
            b = (b & ~1) | int(binary_msg[msg_index])
            msg_index += 1
        encoded_pixels.append((r, g, b))
        if msg_index >= msg_len:
            encoded_pixels.extend(pixels[len(encoded_pixels):])
            break
    encoded_img = Image.new(img.mode, img.size)
    encoded_img.putdata(encoded_pixels)
    return encoded_img

def decode_message(img):
    if img.mode != 'RGB':
        img = img.convert('RGB')
    binary_data = ""
    pixels = list(img.getdata())
    for pixel in pixels:
        r, g, b = pixel
        binary_data += str(r & 1)
        binary_data += str(g & 1)
        binary_data += str(b & 1)
        if len(binary_data) % 8 == 0:
            if len(binary_data) >= 8:
                last_byte = binary_data[-8:]
                if chr(int(last_byte, 2)) == chr(0):
                    break
    message = ""
    for i in range(0, len(binary_data) - 8, 8):
        byte = binary_data[i:i+8]
        if byte:
            char = chr(int(byte, 2))
            if char == chr(0):
                break
            message += char
    return message


# ---------- Audio Steganography Logic ----------
class AudioSteganography:

    END_MARKER = '|||END|||'     # indicates where the hidden message ends

    # Loads a (.wav) file using the wave module
    @staticmethod
    def load_audio(file):
        audio = wave.open(file, 'rb')

        # file parameters (channels, framerate, etc.).
        params = audio.getparams()

        # .wav file should be in 16-bit PCM format (sampwidth == 2).
        if params.sampwidth != 2:
            raise ValueError("Only 16-bit PCM WAV files are supported.")
        
        # Extract raw audio samples into a NumPy array of 16-bit integers
        n_frame = audio.getnframes()
        audio_data = np.frombuffer(audio.readframes(n_frame), dtype=np.int16)
        audio.close()

        return audio_data, params

    # Convert the secret message into a binary string
    @staticmethod
    def msg_to_bits(msgs):
        msgs += AudioSteganography.END_MARKER      # appends the end marker to the secret message
        return ''.join(f"{ord(c):08b}" for c in msgs)

    # Encode the secret message in the audio data
    @staticmethod
    def encode_mesg(audio_data, secret_message):
        bits = AudioSteganography.msg_to_bits(secret_message)    #convert the secret message to binary bits

        # check the capacity of audio data (each bit takes 2 samples)
        if len(bits) > len(audio_data)//2:
            raise ValueError("Secret Message is too large to hide in this audio file.")
        
        # copy of original audio data
        encoded_data = np.copy(audio_data)

        for i, bit in enumerate(bits):
            # pick every second sample, clears the least sigificant bit (LSB) and set the LSB to the derised bit 
            encoded_data[2*i] = audio_data[2*i] & ~1 | int(bit)
        
        return encoded_data

    # save the encoded audio data 
    @staticmethod
    def save_audio(encoded_data, params):
        # prepares a BytesIO stream (in-memory file)
        output = BytesIO()

        #Writes the modified audio data into a valid .wav file using original params.
        with wave.open(output, 'wb') as audio:
            audio.setparams(params)
            audio.writeframes(encoded_data.tobytes())
        output.seek(0)

        return output

    @staticmethod
    def decode_mesg(file):
        # Loads audio and converts it to sample array
        audio_data, p = AudioSteganography.load_audio(file)

        # read LSB from every 2nd sample to extract the hidden bits
        bits = [(audio_data[2*i] & 1) for i in range(len(audio_data)//2)]

        # group the bits into bytes (8-bit each)
        chunks = [bits[i:i+8] for i in range(0, len(bits), 8)]

        # covert each byte to a character 
        decoded_message = ''.join([chr(int(''.join(map(str, byte)), 2)) for byte in chunks])

        # split teh END_MARKER from the decoded message02.
        secret_msg = decoded_message.split(AudioSteganography.END_MARKER)[0]

        return secret_msg



# ---------- Flask Routes ----------
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/image')
def image():
    return render_template('image.html')

@app.route('/audio')
def audio():
    return render_template('audio.html')

@app.route('/encode', methods=['POST'])
def encode():
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image uploaded'}), 400
        if 'message' not in request.form or not request.form['message'].strip():
            return jsonify({'error': 'No message provided'}), 400
        image_file = request.files['image']
        message = request.form['message']
        filename = image_file.filename
        if not filename or not ('.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'bmp', 'jpg', 'jpeg'}):
            return jsonify({'error': 'Invalid image format. Please use PNG, BMP, or JPG'}), 400
        try:
            img = Image.open(image_file)
            password = request.form.get('password', None)
            encoded_img = encode_message(img, message, password)
            img_io = BytesIO()
            encoded_img.save(img_io, 'PNG')
            img_io.seek(0)
            output_filename = f"stego_{secrets.token_hex(4)}.png"
            return send_file(
                img_io,
                mimetype='image/png',
                as_attachment=True,
                download_name=output_filename
            )
        except Exception as e:
            logger.error(f"Encoding error: {str(e)}")
            return jsonify({'error': f'Error processing image: {str(e)}'}), 500
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

@app.route('/decode', methods=['POST'])
def decode():
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image uploaded'}), 400
        image_file = request.files['image']
        filename = image_file.filename
        if not filename or not ('.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'bmp', 'jpg', 'jpeg'}):
            return jsonify({'error': 'Invalid image format. Please use PNG, BMP, or JPG'}), 400
        try:
            img = Image.open(image_file)
            password = request.form.get('password', None)
            hidden_message = decode_message(img)
            if not hidden_message:
                return jsonify({'message': 'No hidden message found or incorrect password'}), 200
            return jsonify({'message': hidden_message}), 200
        except Exception as e:
            logger.error(f"Decoding error: {str(e)}")
            return jsonify({'error': f'Error processing image: {str(e)}'}), 500
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

@app.route('/api/check-capacity', methods=['POST'])
def check_capacity():
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image uploaded'}), 400
        image_file = request.files['image']
        message = request.form.get('message', '')
        img = Image.open(image_file)
        width, height = img.size
        max_bits = width * height * 3
        max_chars = max_bits // 8
        message_length = len(message)
        return jsonify({
            'maxCapacity': max_chars,
            'messageLength': message_length,
            'canEncode': message_length < max_chars,
            'capacityPercent': round((message_length / max_chars) * 100, 1) if max_chars > 0 else 0
        })
    except Exception as e:
        logger.error(f"Capacity check error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ----------- AUDIO ENDPOINTS -----------
@app.route('/audio/encode', methods=['POST'])
def audio_encode():
    try:
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file uploaded'}), 400
        if 'message' not in request.form or not request.form['message'].strip():
            return jsonify({'error': 'No message provided'}), 400
        audio_file = request.files['audio']
        message = request.form['message']
        filename = audio_file.filename
        if not filename or not filename.lower().endswith('.wav'):
            return jsonify({'error': 'Invalid audio format. Please use WAV files only.'}), 400
        try:
            # Read audio file from memory
            audio_file.seek(0)
            audio_data, params = AudioSteganography.load_audio(audio_file)
            encoded_data = AudioSteganography.encode_mesg(audio_data, message)
            output = AudioSteganography.save_audio(encoded_data, params)
            output_filename = f"stego_{secrets.token_hex(4)}.wav"
            return send_file(
                output,
                mimetype='audio/wav',
                as_attachment=True,
                download_name=output_filename
            )
        except Exception as e:
            logger.error(f"Audio encoding error: {str(e)}")
            return jsonify({'error': f'Error processing audio: {str(e)}'}), 500
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

@app.route('/audio/decode', methods=['POST'])
def audio_decode():
    try:
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file uploaded'}), 400
        audio_file = request.files['audio']
        filename = audio_file.filename
        if not filename or not filename.lower().endswith('.wav'):
            return jsonify({'error': 'Invalid audio format. Please use WAV files only.'}), 400
        try:
            audio_file.seek(0)
            message = AudioSteganography.decode_mesg(audio_file)
            if not message:
                return jsonify({'message': 'No hidden message found.'}), 200
            return jsonify({'message': message}), 200
        except Exception as e:
            logger.error(f"Audio decoding error: {str(e)}")
            return jsonify({'error': f'Error processing audio: {str(e)}'}), 500
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

if __name__ == '__main__':
    app.run(debug=True)
