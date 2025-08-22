"""
Flask Server for WebRTC File Transfer Application
Serves the web interface and handles WebRTC connection management
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
import asyncio
import threading
import json
import os
import logging
from typing import Dict, Any
from networking import NetworkingManager, WebRTCConnection

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

# Global networking manager
networking_manager = NetworkingManager()
connection_events = {}  # Store connection events for real-time updates

def run_async_task(coro):
    """Run async task in the background"""
    def run_in_thread():
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(coro)
        except Exception as e:
            logger.error(f"Error in async task: {e}")
        finally:
            loop.close()
    
    thread = threading.Thread(target=run_in_thread)
    thread.daemon = True
    thread.start()

@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')

@app.route('/api/create_offer', methods=['POST'])
def create_offer():
    """Create WebRTC offer"""
    try:
        connection = networking_manager.create_connection()
        
        # Setup callbacks
        async def on_connection_state_change(state):
            connection_events['state'] = state
            logger.info(f"Connection state changed to: {state}")
        
        async def on_file_received(file_path, filename):
            connection_events['file_received'] = {
                'path': file_path,
                'filename': filename
            }
            logger.info(f"File received: {filename}")
        
        async def on_transfer_progress(progress, is_sending):
            connection_events['progress'] = {
                'progress': progress,
                'is_sending': is_sending
            }
        
        async def on_message(message):
            connection_events['message'] = message
            logger.info(f"Message received: {message}")
        
        connection.on_connection_state_change = on_connection_state_change
        connection.on_file_received = on_file_received
        connection.on_transfer_progress = on_transfer_progress
        connection.on_message = on_message
        
        # Create offer asynchronously
        def create_offer_async():
            async def _create_offer():
                try:
                    offer_str = await connection.create_offer()
                    connection_events['offer'] = offer_str
                    logger.info("Offer created successfully")
                except Exception as e:
                    logger.error(f"Error creating offer: {e}")
                    connection_events['error'] = str(e)
            
            return _create_offer()
        
        run_async_task(create_offer_async())
        
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
        
        connection = networking_manager.create_connection()
        
        # Setup callbacks
        async def on_connection_state_change(state):
            connection_events['state'] = state
            logger.info(f"Connection state changed to: {state}")
        
        async def on_file_received(file_path, filename):
            connection_events['file_received'] = {
                'path': file_path,
                'filename': filename
            }
            logger.info(f"File received: {filename}")
        
        async def on_transfer_progress(progress, is_sending):
            connection_events['progress'] = {
                'progress': progress,
                'is_sending': is_sending
            }
        
        async def on_message(message):
            connection_events['message'] = message
            logger.info(f"Message received: {message}")
        
        connection.on_connection_state_change = on_connection_state_change
        connection.on_file_received = on_file_received
        connection.on_transfer_progress = on_transfer_progress
        connection.on_message = on_message
        
        # Create answer asynchronously
        def create_answer_async():
            async def _create_answer():
                try:
                    answer_str = await connection.create_answer(offer_str)
                    connection_events['answer'] = answer_str
                    logger.info("Answer created successfully")
                except Exception as e:
                    logger.error(f"Error creating answer: {e}")
                    connection_events['error'] = str(e)
            
            return _create_answer()
        
        run_async_task(create_answer_async())
        
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
        
        connection = networking_manager.get_connection()
        if not connection:
            return jsonify({'status': 'error', 'message': 'No active connection'}), 400
        
        # Set answer asynchronously
        def set_answer_async():
            async def _set_answer():
                try:
                    await connection.set_answer(answer_str)
                    logger.info("Answer set successfully")
                except Exception as e:
                    logger.error(f"Error setting answer: {e}")
                    connection_events['error'] = str(e)
            
            return _set_answer()
        
        run_async_task(set_answer_async())
        
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
        
        connection = networking_manager.get_connection()
        if not connection or not connection.is_connected():
            return jsonify({'status': 'error', 'message': 'No active connection'}), 400
        
        # Save uploaded file temporarily
        temp_dir = os.path.join(os.getcwd(), 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        temp_file_path = os.path.join(temp_dir, file.filename)
        file.save(temp_file_path)
        
        # Send file asynchronously
        def send_file_async():
            async def _send_file():
                try:
                    await connection.send_file(temp_file_path)
                    # Clean up temp file
                    os.remove(temp_file_path)
                    logger.info(f"File sent successfully: {file.filename}")
                except Exception as e:
                    logger.error(f"Error sending file: {e}")
                    connection_events['error'] = str(e)
                    # Clean up temp file on error
                    if os.path.exists(temp_file_path):
                        os.remove(temp_file_path)
            
            return _send_file()
        
        run_async_task(send_file_async())
        
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
        
        connection = networking_manager.get_connection()
        if not connection or not connection.is_connected():
            return jsonify({'status': 'error', 'message': 'No active connection'}), 400
        
        # Send message asynchronously
        def send_message_async():
            async def _send_message():
                try:
                    await connection.send_message(message)
                    logger.info(f"Message sent: {message}")
                except Exception as e:
                    logger.error(f"Error sending message: {e}")
                    connection_events['error'] = str(e)
            
            return _send_message()
        
        run_async_task(send_message_async())
        
        return jsonify({'status': 'success', 'message': 'Message sent'})
    
    except Exception as e:
        logger.error(f"Error in send_message: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/get_events', methods=['GET'])
def get_events():
    """Get connection events (polling endpoint)"""
    try:
        connection = networking_manager.get_connection()
        connection_state = connection.get_connection_state() if connection else 'disconnected'
        is_connected = connection.is_connected() if connection else False
        
        events = dict(connection_events)
        connection_events.clear()  # Clear events after sending
        
        events['connection_state'] = connection_state
        events['is_connected'] = is_connected
        
        return jsonify(events)
    
    except Exception as e:
        logger.error(f"Error in get_events: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/disconnect', methods=['POST'])
def disconnect():
    """Disconnect the WebRTC connection"""
    try:
        connection = networking_manager.get_connection()
        if connection:
            # Disconnect asynchronously
            def disconnect_async():
                async def _disconnect():
                    try:
                        await connection.close()
                        logger.info("Connection closed")
                    except Exception as e:
                        logger.error(f"Error closing connection: {e}")
                
                return _disconnect()
            
            run_async_task(disconnect_async())
        
        # Clear events
        connection_events.clear()
        
        return jsonify({'status': 'success', 'message': 'Disconnected'})
    
    except Exception as e:
        logger.error(f"Error in disconnect: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current connection status"""
    try:
        connection = networking_manager.get_connection()
        if connection:
            return jsonify({
                'has_connection': True,
                'connection_state': connection.get_connection_state(),
                'is_connected': connection.is_connected()
            })
        else:
            return jsonify({
                'has_connection': False,
                'connection_state': 'disconnected',
                'is_connected': False
            })
    
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
    # Create necessary directories
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    os.makedirs('temp', exist_ok=True)
    
    print("🚀 Telekinesis File Transfer Server Starting...")
    print("📡 WebRTC P2P File Transfer Application")
    print("🌐 Open your browser and navigate to: http://localhost:5000")
    print("📁 Files will be saved to your Downloads folder")
    print("⚡ Zero-cost peer-to-peer file sharing!")
    print("\n" + "="*50)
    
    # Run Flask app
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
