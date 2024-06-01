from flask import Flask, request, send_from_directory, jsonify
import os
import time
import requests
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
port = os.getenv('PORT', 8080)

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def send_request(data, to_cloud_run):
    """
    Sends a request to either the FIRST_API_HOST or SECOND_API_HOST based on the to_cloud_run flag.
    """
    host = os.getenv('SECOND_API_HOST') if to_cloud_run else os.getenv('FIRST_API_HOST')
    port = os.getenv('SECOND_API_PORT') if to_cloud_run else os.getenv('FIRST_API_PORT')

    url = f"{host}:{port}/upload"
    response = requests.post(url, files=data)
    return response

@app.route('/')
def index():
    return send_from_directory('resources', 'index.html')

@app.route('/start', methods=['POST'])
def start():
    num_of_requests = int(request.form.get('numOfRequests', 1))
    to_cloud_run = request.form.get('toCloudRun', 'false').lower() in ['true', '1', 't', 'y', 'yes']
    file = request.files.get('file')

    if file is None:
        return jsonify({"message": "Must provide a file"}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    with open(filepath, 'rb') as f:
        files = {'file': (filename, f, file.mimetype)}

        start_time = time.time()

        try:
            # Send requests and wait for all to complete
            results = [send_request(files, to_cloud_run) for _ in range(num_of_requests)]
            elapsed_time = (time.time() - start_time) * 1000  # Convert to milliseconds

            fulfilled = []
            rejected = []

            for res in results:
                if res.ok:
                    fulfilled.append(res.text.strip())
                else:
                    rejected.append(res.text.strip())

            return jsonify({
                "numOfRequests": num_of_requests,
                "failedRequests": len(rejected),
                "time": round(elapsed_time, 5),
                "result": fulfilled[0] if fulfilled else None,
                "error": rejected[0] if rejected else None
            })
        except Exception as err:
            print(err)
            return jsonify({"message": "API is down"}), 503
        finally:
            os.remove(filepath)

if __name__ == '__main__':
    app.run(port=port)
