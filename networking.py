"""
WebRTC Networking Module for Peer-to-Peer File Transfer
Handles all networking operations including connection setup, signaling, and file transfer
"""

import asyncio
import json
import base64
import hashlib
import os
from typing import Dict, Any, Callable, Optional
from dataclasses import dataclass
from aiortc import RTCPeerConnection, RTCDataChannel, RTCConfiguration, RTCIceServer
from aiortc.contrib.signaling import object_to_string, object_from_string
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        ice_servers = [
            RTCIceServer(urls=["stun:stun.l.google.com:19302"]),
            RTCIceServer(urls=["stun:stun1.l.google.com:19302"]),
            RTCIceServer(urls=["stun:stun.cloudflare.com:3478"])
        ]
        
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
            logger.info(f"Connection state: {self.pc.connectionState}")
            if self.on_connection_state_change:
                await self.on_connection_state_change(self.pc.connectionState)
        
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
    
    async def _wait_for_ice_gathering(self, timeout: int = 10):
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
        chunk_size = 16384  # 16KB chunks
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
            await asyncio.sleep(0.001)
        
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
        if self.data_channel:
            self.data_channel.close()
        await self.pc.close()

class NetworkingManager:
    """High-level manager for WebRTC connections"""
    
    def __init__(self):
        self.connection: Optional[WebRTCConnection] = None
        self.event_loop = None
    
    def create_connection(self) -> WebRTCConnection:
        """Create a new WebRTC connection"""
        if self.connection:
            asyncio.create_task(self.connection.close())
        
        self.connection = WebRTCConnection()
        return self.connection
    
    def get_connection(self) -> Optional[WebRTCConnection]:
        """Get current connection"""
        return self.connection
    
    async def cleanup(self):
        """Cleanup connections"""
        if self.connection:
            await self.connection.close()
            self.connection = None
