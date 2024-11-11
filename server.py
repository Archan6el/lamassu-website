from flask import Flask, request, render_template, jsonify
import os
import subprocess
import tempfile
import shutil

app = Flask(__name__)

# Path to save uploaded files temporarily
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Allowed file extensions (e.g., image files)
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'bmp', 'gif'}

def allowed_file(filename):
    """Check if the file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Render the upload page."""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and call calculate_area.py."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    confidence = request.form.get('confidence', type=float)

    # Check if the file is valid
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and allowed_file(file.filename):
        # Save the file temporarily
        filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filename)

        # Call the calculate_area.py script with the uploaded file and confidence level
        try:
            result = run_calculate_area_script(filename, confidence)
            
            # Extract the image path from the result string
            # Example: "The image with the result is saved in: output/exp2/test3.png"
            image_path = result.split("The image with the result is saved in: ")[-1].strip()
            
            # Clean up uploaded file
            os.remove(filename)
            
            # Send the result back with the image path
            return render_template('results.html', image_path=image_path)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return jsonify({'error': 'Invalid file format'}), 400

def run_calculate_area_script(file_path, confidence):

    current_directory = os.getcwd()

    """Run the calculate_area.py script with the given file and confidence."""
    command = [
        'python3', f'{current_directory}/scripts/yolov7-scripts/calculate-area.py',
        '--weights', 'assets/best.pt',
        '--source', file_path,
        '--img-size', '640',
        '--conf-thres', str(confidence),
        '--project', 'output'
    ]
    
    # Run the script
    # Log both stdout and stderr
    try:
        # Run the command and capture the output
        result = subprocess.run(command, check=True, capture_output=True, text=True)

        # Clean the result to extract the correct file path
        output = result.stdout.strip()  # Clean leading/trailing whitespaces and newlines
        print(f"Script output: {output}")  # For debugging
        
        # Extract the image path from the result string
        # We look for the part "The image with the result is saved in: "
        image_path = output.split("The image with the result is saved in: ")[-1].strip()
        # In case there are multiple lines, take only the first part
        image_path = image_path.splitlines()[0].strip()

        # Ensure the processed image path is valid
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"The image file does not exist: {image_path}")

        # Copy the processed image to the Flask static folder
        processed_image_path = os.path.join('static', os.path.basename(image_path))

        # Ensure that the static folder exists
        os.makedirs('static', exist_ok=True)

        # Copy the image to the static folder for Flask to serve it
        shutil.copy(image_path, processed_image_path)

        # Return the relative path for the template
        return processed_image_path

    except subprocess.CalledProcessError as e:
        error_message = f"Script failed with exit code {e.returncode}. stdout: {e.stdout}. stderr: {e.stderr}"
        print(error_message)  # This will print the error to the Flask server's terminal
        return jsonify({'error': error_message}), 500

    except FileNotFoundError as fnf_error:
        print(fnf_error)  # Print the file not found error for debugging
        return jsonify({'error': str(fnf_error)}), 500

if __name__ == '__main__':
    app.run(debug=True)
