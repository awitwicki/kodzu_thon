from flask import Flask, request, jsonify
import whisper
import os

app = Flask(__name__)

model = whisper.load_model("small")

@app.route('/transcribe', methods=['POST'])
def transcribe():
    print("Transcribing...")
    print(request.files)
    
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    
    temp_file_path = os.path.join("temp", file.filename)
    os.makedirs("temp", exist_ok=True)
    file.save(temp_file_path)

    try:
        result = model.transcribe(temp_file_path)
        text = result.get("text", "")
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        os.remove(temp_file_path)

    return jsonify({"text": text})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
