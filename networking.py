"""
WebRTC Networking Module for Peer-to-Peer File Transfer
Handles all networking operations including connection setup, signaling, and file transfer
"""

import asyncio
import json
import hashlib
import os
import threading
import time
from typing import Dict, Any, Callable, Optional
from dataclasses import dataclass
from aiortc import RTCPeerConnection, RTCDataChannel, RTCConfiguration, RTCIceServer
from aiortc.contrib.signaling import object_to_string, object_from_string
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
DEFAULT_CHUNK_SIZE = 16384  # 16KB chunks for file transfer
ICE_GATHERING_TIMEOUT = 10  # seconds
CHUNK_DELAY = 0.001  # seconds between chunks
STUN_SERVERS = [
    "stun:stun.l.google.com:19302",
    "stun:stun1.l.google.com:19302", 
    "stun:stun.cloudflare.com:3478"
]

@dataclass
class FileMetadata:
    """Metadata for file transfer"""
    filename: str
    size: int
    chunk_size: int
    total_chunks: int
    file_hash: str

class WebRTCConnection:
    """Handles WebRTC peer-to-peer connection and file transfer"""
    
    def __init__(self):
        # Use free STUN servers for NAT traversal
        ice_servers = [RTCIceServer(urls=[url]) for url in STUN_SERVERS]
        
        configuration = RTCConfiguration(iceServers=ice_servers)
        self.pc = RTCPeerConnection(configuration)
        self.data_channel: Optional[RTCDataChannel] = None
        self.is_initiator = False
        
        # File transfer state
        self.file_chunks: Dict[int, bytes] = {}
        self.current_file_metadata: Optional[FileMetadata] = None
        self.received_chunks = 0
        
        # Callbacks
        self.on_connection_state_change: Optional[Callable] = None
        self.on_file_received: Optional[Callable] = None
        self.on_transfer_progress: Optional[Callable] = None
        self.on_message: Optional[Callable] = None
        
        self._setup_event_handlers()
    
    def _setup_event_handlers(self):
        """Setup WebRTC event handlers"""
        
        @self.pc.on("connectionstatechange")
        async def on_connectionstatechange():
            state = self.pc.connectionState
            logger.info(f"Connection state: {state}")
            if self.on_connection_state_change:
                await self.on_connection_state_change(state)
            
            # Handle disconnections and failures
            if state in ["disconnected", "failed", "closed"]:
                logger.info(f"Connection terminated: {state}")
                # Clean up data channel reference
                if self.data_channel:
                    self.data_channel = None
        
        @self.pc.on("datachannel")
        def on_datachannel(channel):
            logger.info(f"Data channel received: {channel.label}")
            self.data_channel = channel
            self._setup_datachannel_handlers(channel)
    
    def _setup_datachannel_handlers(self, channel: RTCDataChannel):
        """Setup data channel event handlers"""
        
        @channel.on("open")
        def on_open():
            logger.info(f"Data channel {channel.label} opened")
        
        @channel.on("close")
        def on_close():
            logger.info(f"Data channel {channel.label} closed")
            if self.on_connection_state_change:
                asyncio.create_task(self.on_connection_state_change("closed"))
        
        @channel.on("message")
        def on_message(message):
            asyncio.create_task(self._handle_message(message))
    
    async def _handle_message(self, message):
        """Handle incoming messages on data channel"""
        try:
            if isinstance(message, str):
                # Control message
                data = json.loads(message)
                await self._handle_control_message(data)
            elif isinstance(message, bytes):
                # File chunk
                await self._handle_file_chunk(message)
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    async def _handle_control_message(self, data: Dict[str, Any]):
        """Handle control messages"""
        msg_type = data.get('type')
        
        if msg_type == 'file_metadata':
            # Receiving file metadata
            self.current_file_metadata = FileMetadata(**data['metadata'])
            self.file_chunks = {}
            self.received_chunks = 0
            logger.info(f"Receiving file: {self.current_file_metadata.filename}")
            
        elif msg_type == 'file_complete':
            # File transfer complete
            await self._assemble_file()
            
        elif msg_type == 'text_message':
            # Text message
            if self.on_message:
                await self.on_message(data['content'])
    
    async def _handle_file_chunk(self, chunk_data: bytes):
        """Handle incoming file chunk"""
        if not self.current_file_metadata:
            logger.error("Received file chunk without metadata")
            return
        
        # Extract chunk index (first 4 bytes) and data
        chunk_index = int.from_bytes(chunk_data[:4], byteorder='big')
        chunk_content = chunk_data[4:]
        
        self.file_chunks[chunk_index] = chunk_content
        self.received_chunks += 1
        
        # Update progress
        progress = (self.received_chunks / self.current_file_metadata.total_chunks) * 100
        if self.on_transfer_progress:
            await self.on_transfer_progress(progress, False)  # False = receiving
        
        logger.info(f"Received chunk {chunk_index + 1}/{self.current_file_metadata.total_chunks}")
    
    async def _assemble_file(self):
        """Assemble received file chunks"""
        if not self.current_file_metadata or not self.file_chunks:
            return
        
        # Assemble chunks in order
        file_data = b''
        for i in range(self.current_file_metadata.total_chunks):
            if i not in self.file_chunks:
                logger.error(f"Missing chunk {i}")
                return
            file_data += self.file_chunks[i]
        
        # Verify file integrity
        file_hash = hashlib.sha256(file_data).hexdigest()
        if file_hash != self.current_file_metadata.file_hash:
            logger.error("File integrity check failed")
            return
        
        # Save file
        downloads_dir = os.path.expanduser("~/Downloads")
        os.makedirs(downloads_dir, exist_ok=True)
        file_path = os.path.join(downloads_dir, self.current_file_metadata.filename)
        
        # Handle duplicate filenames
        counter = 1
        original_path = file_path
        while os.path.exists(file_path):
            name, ext = os.path.splitext(original_path)
            file_path = f"{name}_{counter}{ext}"
            counter += 1
        
        with open(file_path, 'wb') as f:
            f.write(file_data)
        
        logger.info(f"File saved: {file_path}")
        
        if self.on_file_received:
            await self.on_file_received(file_path, self.current_file_metadata.filename)
        
        # Clean up
        self.file_chunks = {}
        self.current_file_metadata = None
        self.received_chunks = 0
    
    async def create_offer(self) -> str:
        """Create WebRTC offer (initiator)"""
        self.is_initiator = True
        
        # Create data channel
        self.data_channel = self.pc.createDataChannel("file_transfer")
        self._setup_datachannel_handlers(self.data_channel)
        
        # Create offer
        offer = await self.pc.createOffer()
        await self.pc.setLocalDescription(offer)
        
        # Wait for ICE gathering to complete
        await self._wait_for_ice_gathering()
        
        # Return offer as string for manual signaling
        return object_to_string(self.pc.localDescription)
    
    async def create_answer(self, offer_str: str) -> str:
        """Create WebRTC answer (responder)"""
        self.is_initiator = False
        
        # Set remote description from offer
        offer = object_from_string(offer_str)
        await self.pc.setRemoteDescription(offer)
        
        # Create answer
        answer = await self.pc.createAnswer()
        await self.pc.setLocalDescription(answer)
        
        # Wait for ICE gathering to complete
        await self._wait_for_ice_gathering()
        
        # Return answer as string for manual signaling
        return object_to_string(self.pc.localDescription)
    
    async def set_answer(self, answer_str: str):
        """Set the answer (called by initiator)"""
        answer = object_from_string(answer_str)
        await self.pc.setRemoteDescription(answer)
    
    async def _wait_for_ice_gathering(self, timeout: int = ICE_GATHERING_TIMEOUT):
        """Wait for ICE gathering to complete"""
        for _ in range(timeout * 10):  # Check every 100ms
            if self.pc.iceGatheringState == "complete":
                break
            await asyncio.sleep(0.1)
    
    async def send_file(self, file_path: str):
        """Send a file through the data channel"""
        if not self.data_channel or self.data_channel.readyState != "open":
            raise Exception("Data channel not ready")
        
        if not os.path.exists(file_path):
            raise Exception("File not found")
        
        # Read file and calculate metadata
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        filename = os.path.basename(file_path)
        file_size = len(file_data)
        chunk_size = DEFAULT_CHUNK_SIZE
        total_chunks = (file_size + chunk_size - 1) // chunk_size
        file_hash = hashlib.sha256(file_data).hexdigest()
        
        metadata = FileMetadata(
            filename=filename,
            size=file_size,
            chunk_size=chunk_size,
            total_chunks=total_chunks,
            file_hash=file_hash
        )
        
        # Send metadata
        metadata_msg = {
            'type': 'file_metadata',
            'metadata': {
                'filename': metadata.filename,
                'size': metadata.size,
                'chunk_size': metadata.chunk_size,
                'total_chunks': metadata.total_chunks,
                'file_hash': metadata.file_hash
            }
        }
        self.data_channel.send(json.dumps(metadata_msg))
        
        # Send file chunks
        for i in range(total_chunks):
            start = i * chunk_size
            end = min(start + chunk_size, file_size)
            chunk = file_data[start:end]
            
            # Prepend chunk index (4 bytes)
            chunk_with_index = i.to_bytes(4, byteorder='big') + chunk
            self.data_channel.send(chunk_with_index)
            
            # Update progress
            progress = ((i + 1) / total_chunks) * 100
            if self.on_transfer_progress:
                await self.on_transfer_progress(progress, True)  # True = sending
            
            # Small delay to prevent overwhelming the channel
            await asyncio.sleep(CHUNK_DELAY)
        
        # Send completion message
        complete_msg = {'type': 'file_complete'}
        self.data_channel.send(json.dumps(complete_msg))
        
        logger.info(f"File sent: {filename}")
    
    async def send_message(self, message: str):
        """Send a text message"""
        if not self.data_channel or self.data_channel.readyState != "open":
            raise Exception("Data channel not ready")
        
        msg = {
            'type': 'text_message',
            'content': message
        }
        self.data_channel.send(json.dumps(msg))
    
    def get_connection_state(self) -> str:
        """Get current connection state"""
        return self.pc.connectionState
    
    def is_connected(self) -> bool:
        """Check if connection is established"""
        return (self.pc.connectionState == "connected" and 
                self.data_channel and 
                self.data_channel.readyState == "open")
    
    async def close(self):
        """Close the connection"""
        logger.info("Closing WebRTC connection")
        
        # Close data channel first
        if self.data_channel:
            self.data_channel.close()
            self.data_channel = None
        
        # Close peer connection
        await self.pc.close()
        
        # Notify about closure
        if self.on_connection_state_change:
            await self.on_connection_state_change("closed")

class NetworkingManager:
    """High-level manager for WebRTC connections with event handling"""
    
    def __init__(self):
        self.connection: Optional[WebRTCConnection] = None
        self.connection_events: Dict[str, Any] = {}
        self._loop = None
        self._loop_thread = None
    
    def _get_event_loop(self):
        """Get or create the persistent event loop"""
        if self._loop is None or self._loop.is_closed():
            def start_loop():
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
                self._loop.run_forever()
            
            self._loop_thread = threading.Thread(target=start_loop, daemon=True)
            self._loop_thread.start()
            
            # Wait for loop to start
            time.sleep(0.1)
        
        return self._loop
    
    def _run_async_task(self, operation_name: str, coro):
        """Schedule async task in the persistent event loop (non-blocking)"""
        def done_callback(future):
            try:
                future.result()
                logger.info(f"{operation_name} completed successfully")
            except Exception as e:
                logger.error(f"Error in {operation_name}: {e}")
                self.connection_events['error'] = str(e)
        
        loop = self._get_event_loop()
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        future.add_done_callback(done_callback)
    
    def _execute_async_operation(self, operation_name: str, async_func, result_key: str = None, *args, **kwargs):
        """Generic wrapper for async operations with consistent error handling"""
        async def wrapper():
            try:
                result = await async_func(*args, **kwargs)
                if result is not None and result_key:
                    self.connection_events[result_key] = result
                return result
            except Exception as e:
                error_msg = f"Error in {operation_name}: {e}"
                logger.error(error_msg)
                self.connection_events['error'] = str(e)
                raise
        
        self._run_async_task(operation_name, wrapper())
    
    def _ensure_connection_exists(self, operation_name: str) -> bool:
        """Check if connection exists, set error if not"""
        if not self.connection:
            error_msg = f"No active connection for {operation_name}"
            self.connection_events['error'] = error_msg
            logger.error(error_msg)
            return False
        return True
    
    def _ensure_connection_ready(self, operation_name: str) -> bool:
        """Check if connection is ready for operations"""
        if not self._ensure_connection_exists(operation_name):
            return False
        if not self.connection.is_connected():
            error_msg = f"Connection not ready for {operation_name}"
            self.connection_events['error'] = error_msg
            logger.error(error_msg)
            return False
        return True
    
    def _create_new_connection(self) -> WebRTCConnection:
        """Create and setup a new WebRTC connection with callbacks"""
        connection = WebRTCConnection()
        
        # Setup event callbacks
        async def on_connection_state_change(state):
            self.connection_events['connection_state'] = state
            logger.info(f"Connection state changed to: {state}")
            
            # Clear connection reference on termination
            if state in ["disconnected", "failed", "closed"]:
                logger.info("Connection terminated - clearing connection reference")
                self.connection = None
        
        async def on_file_received(file_path, filename):
            self.connection_events['file_received'] = {
                'path': file_path,
                'filename': filename
            }
            logger.info(f"File received: {filename}")
        
        async def on_transfer_progress(progress, is_sending):
            self.connection_events['progress'] = {
                'progress': progress,
                'is_sending': is_sending
            }
        
        async def on_message(message):
            self.connection_events['message'] = message
            logger.info(f"Message received: {message}")
        
        connection.on_connection_state_change = on_connection_state_change
        connection.on_file_received = on_file_received
        connection.on_transfer_progress = on_transfer_progress
        connection.on_message = on_message
        
        return connection
    
    def create_offer(self):
        """Create WebRTC offer"""
        # Force cleanup any existing connection
        if self.connection:
            try:
                asyncio.run_coroutine_threadsafe(
                    self.connection.close(), 
                    self._get_event_loop()
                )
            except:
                pass
            self.connection = None
        
        # Clear stale events
        self.connection_events.clear()
        
        self.connection = self._create_new_connection()
        self._execute_async_operation("Create Offer", self.connection.create_offer, "offer")
    
    def create_answer(self, offer_str: str):
        """Create WebRTC answer"""
        # Force cleanup any existing connection
        if self.connection:
            try:
                asyncio.run_coroutine_threadsafe(
                    self.connection.close(), 
                    self._get_event_loop()
                )
            except:
                pass
            self.connection = None
        
        # Clear stale events
        self.connection_events.clear()
        
        self.connection = self._create_new_connection()
        self._execute_async_operation("Create Answer", self.connection.create_answer, "answer", offer_str)
    
    def set_answer(self, answer_str: str):
        """Set the answer (called by initiator)"""
        if not self._ensure_connection_exists("Set Answer"):
            return
        self._execute_async_operation("Set Answer", self.connection.set_answer, None, answer_str)
    
    def send_file(self, file_path: str):
        """Send a file through WebRTC with automatic cleanup"""
        if not self._ensure_connection_ready("Send File"):
            return
        
        async def _send_file_with_cleanup():
            try:
                await self.connection.send_file(file_path)
                # Clean up temporary file if it's in temp directory
                if 'temp' in file_path and os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Temporary file cleaned up: {file_path}")
            finally:
                # Ensure cleanup even on error
                if 'temp' in file_path and os.path.exists(file_path):
                    os.remove(file_path)
        
        self._execute_async_operation("Send File", _send_file_with_cleanup, None)
    
    def send_message(self, message: str):
        """Send a text message"""
        if not self._ensure_connection_ready("Send Message"):
            return
        self._execute_async_operation("Send Message", self.connection.send_message, None, message)
    
    def disconnect(self):
        """Disconnect the WebRTC connection"""
        if self.connection:
            self._execute_async_operation("Disconnect", self.connection.close, None)
        
        self.connection_events.clear()
        self.connection = None  # Explicit cleanup
        
        # Stop event loop completely
        if self._loop and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(self._loop.stop)
            self._loop = None
            self._loop_thread = None
    
    def _get_connection_status(self) -> Dict[str, Any]:
        """Get current connection status info"""
        if self.connection:
            return {
                'has_connection': True,
                'connection_state': self.connection.get_connection_state(),
                'is_connected': self.connection.is_connected()
            }
        else:
            return {
                'has_connection': False,
                'connection_state': 'disconnected',
                'is_connected': False
            }
    
    def get_events(self) -> Dict[str, Any]:
        """Get and clear connection events"""
        events = dict(self.connection_events)
        self.connection_events.clear()
        
        # Add current connection status
        status = self._get_connection_status()
        events.update(status)
        
        return events
    
    def get_status(self) -> Dict[str, Any]:
        """Get current connection status"""
        return self._get_connection_status()
    
    def get_connection(self) -> Optional[WebRTCConnection]:
        """Get current connection"""
        return self.connection
    
    async def cleanup(self):
        """Cleanup connections"""
        if self.connection:
            await self.connection.close()
            self.connection = None
