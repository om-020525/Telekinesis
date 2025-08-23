"""
Flask Server for WebRTC File Transfer Application
Serves the web interface and handles WebRTC connection management
"""

from flask import Flask, render_template, request, jsonify, send_from_directory, Response
import os
import logging
import argparse
import queue
import time
import json
from threading import Lock
from networking import NetworkingManager, SSEManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

networking_manager = NetworkingManager()

@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')

@app.route('/api/create_room', methods=['POST'])
def create_room():
    """Create room with signaling"""
    try:
        data = request.get_json()
        room_name = data.get('room_name')
        user_name = data.get('user_name')
        
        if not room_name or not user_name:
            return jsonify({'status': 'error', 'message': 'Room name and user name are required'}), 400
        
        networking_manager.create_room(room_name, user_name)
        return jsonify({'status': 'success', 'message': f'Room {room_name} created'})
    except Exception as e:
        logger.error(f"Error in create_room: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/join_room', methods=['POST'])
def join_room():
    """Join existing room"""
    try:
        data = request.get_json()
        room_name = data.get('room_name')
        user_name = data.get('user_name')
        
        if not room_name or not user_name:
            return jsonify({'status': 'error', 'message': 'Room name and user name are required'}), 400
        
        networking_manager.join_room(room_name, user_name)
        return jsonify({'status': 'success', 'message': f'Joined room {room_name}'})
    except Exception as e:
        logger.error(f"Error in join_room: {e}")
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

@app.route('/api/disconnect', methods=['POST'])
def disconnect():
    """Disconnect the WebRTC connection"""
    try:
        global networking_manager
        networking_manager.disconnect()
        del networking_manager
        networking_manager = NetworkingManager()
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

@app.route('/api/events')
def event_stream():
    """Server-Sent Events endpoint for real-time updates"""
    def generate():
        try:
            while True:
                try:
                    # Wait for events with timeout
                    event = SSEManager.event_queue.get(timeout=30)
                    
                    # Send event to client
                    event_data = {
                        'type': event['type'],
                        'data': event['data'],
                        'timestamp': event['timestamp']
                    }
                    logger.info(f"📡 Sending SSE event to client: {event_data}")
                    yield f"data: {json.dumps(event_data)}\n\n"
                    
                except queue.Empty:
                    # Send heartbeat to keep connection alive
                    yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': time.time()})}\n\n"
                    
        except GeneratorExit:
            logger.info("SSE client disconnected")
    
    return Response(generate(), 
                   mimetype='text/event-stream',
                   headers={'Cache-Control': 'no-cache',
                           'Connection': 'keep-alive',
                           'Access-Control-Allow-Origin': '*'})

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
    
    # Run Flask app
    app.run(host='0.0.0.0', port=args.port, debug=True, threaded=True)
