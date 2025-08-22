"""
Flask Server for WebRTC File Transfer Application
Serves the web interface and handles WebRTC connection management
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import logging
import argparse
from networking import NetworkingManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

# Global networking manager
networking_manager = NetworkingManager()

@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')

@app.route('/api/create_offer', methods=['POST'])
def create_offer():
    """Create WebRTC offer"""
    try:
        networking_manager.create_offer()
        return jsonify({'status': 'success', 'message': 'Creating offer...'})
    except Exception as e:
        logger.error(f"Error in create_offer: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/create_answer', methods=['POST'])
def create_answer():
    """Create WebRTC answer"""
    try:
        data = request.get_json()
        offer_str = data.get('offer')
        
        if not offer_str:
            return jsonify({'status': 'error', 'message': 'Offer is required'}), 400
        
        networking_manager.create_answer(offer_str)
        return jsonify({'status': 'success', 'message': 'Creating answer...'})
    except Exception as e:
        logger.error(f"Error in create_answer: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/set_answer', methods=['POST'])
def set_answer():
    """Set the answer (called by initiator)"""
    try:
        data = request.get_json()
        answer_str = data.get('answer')
        
        if not answer_str:
            return jsonify({'status': 'error', 'message': 'Answer is required'}), 400
        
        networking_manager.set_answer(answer_str)
        return jsonify({'status': 'success', 'message': 'Answer set successfully'})
    except Exception as e:
        logger.error(f"Error in set_answer: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/send_file', methods=['POST'])
def send_file():
    """Send a file through WebRTC"""
    try:
        if 'file' not in request.files:
            return jsonify({'status': 'error', 'message': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'No file selected'}), 400
        
        # Save uploaded file temporarily
        temp_dir = os.path.join(os.getcwd(), 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        temp_file_path = os.path.join(temp_dir, file.filename)
        file.save(temp_file_path)
        
        networking_manager.send_file(temp_file_path)
        return jsonify({'status': 'success', 'message': f'Sending file: {file.filename}'})
    except Exception as e:
        logger.error(f"Error in send_file: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/send_message', methods=['POST'])
def send_message():
    """Send a text message through WebRTC"""
    try:
        data = request.get_json()
        message = data.get('message')
        
        if not message:
            return jsonify({'status': 'error', 'message': 'Message is required'}), 400
        
        networking_manager.send_message(message)
        return jsonify({'status': 'success', 'message': 'Message sent'})
    except Exception as e:
        logger.error(f"Error in send_message: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/get_events', methods=['GET'])
def get_events():
    """Get connection events (polling endpoint)"""
    try:
        return jsonify(networking_manager.get_events())
    except Exception as e:
        logger.error(f"Error in get_events: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/disconnect', methods=['POST'])
def disconnect():
    """Disconnect the WebRTC connection"""
    try:
        networking_manager.disconnect()
        return jsonify({'status': 'success', 'message': 'Disconnected'})
    except Exception as e:
        logger.error(f"Error in disconnect: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current connection status"""
    try:
        return jsonify(networking_manager.get_status())
    except Exception as e:
        logger.error(f"Error in get_status: {e}")
        return jsonify({'error': str(e)}), 500

# Static file serving
@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files"""
    return send_from_directory('static', filename)

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'status': 'error', 'message': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

if __name__ == '__main__':
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Telekinesis - WebRTC P2P File Transfer Server')
    parser.add_argument('-p', '--port', type=int, default=5000, 
    help='Port to run the server on (default: 5000)')
    args = parser.parse_args()
    
    # Create necessary directories
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    os.makedirs('temp', exist_ok=True)
    
    print("🚀 Telekinesis File Transfer Server Starting...")
    print("📡 WebRTC P2P File Transfer Application")
    print(f"🌐 Open your browser and navigate to: http://localhost:{args.port}")
    print("📁 Files will be saved to your Downloads folder")
    print("⚡ Zero-cost peer-to-peer file sharing!")
    print("\n" + "="*50)
    
    # Run Flask app
    app.run(host='0.0.0.0', port=args.port, debug=True, threaded=True)
