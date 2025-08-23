import asyncio
import json
import hashlib
import os
import threading
import time
import queue
from typing import Dict, Any, Callable, Optional
from dataclasses import dataclass
from aiortc import RTCPeerConnection, RTCDataChannel, RTCConfiguration, RTCIceServer
from aiortc.contrib.signaling import object_to_string, object_from_string
import firebase_admin
from firebase_admin import credentials, firestore
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_CHUNK_SIZE = 16384
ICE_GATHERING_TIMEOUT = 10
CHUNK_DELAY = 0.001
STUN_SERVERS = [
    "stun:stun.l.google.com:19302",
    "stun:stun1.l.google.com:19302", 
    "stun:stun2.l.google.com:19302",
    "stun:stun3.l.google.com:19302",
    "stun:stun4.l.google.com:19302",
    "stun:stun.ekiga.net",
    "stun:stun.ideasip.com",
    "stun:stun.rixtelecom.se",
    "stun:stun.schlund.de",
    "stun:stunserver.org",
    "stun:stun.softjoys.com",
    "stun:stun.voiparound.com",
    "stun:stun.voipbuster.com",
    "stun:stun.voipstunt.com",
    "stun:stun.voxgratia.org"
]

@dataclass
class FileMetadata:
    filename: str
    size: int
    chunk_size: int
    total_chunks: int
    file_hash: str

class Events:
    def __init__(self):
        self.queue = queue.Queue()
        self.lock = threading.Lock()
    
    TYPES = {
        'offer_created': 'offer_created',
        'answer_created': 'answer_created',
        'answer_received': 'answer_received',
        'connection_state_changed': 'connection_state_changed',
        'error': 'error',
        'progress': 'progress',
        'file_received': 'file_received',
        'message_received': 'message_received',
    }
    
    def add_event(self, event_type, data):
        with self.lock:
            self.queue.put({'type': event_type, 'data': data})
    
    def get_event(self, timeout=1):
        return self.queue.get(timeout=timeout)
    
    def clear_queue(self):
        with self.lock:
            while not self.queue.empty():
                try:
                    self.queue.get_nowait()
                except queue.Empty:
                    break
    

class SignalingManager:
    def __init__(self):
        try :
            cred = credentials.Certificate("secrets/theater-4-friends-firebase-adminsdk-txcja-ae6a2eb7cf.json")
        except Exception as e:
            logger.error(f"Error loading credentials: {e}")
            raise e
        try:
            self.app = firebase_admin.initialize_app(cred)
        except ValueError:
            self.app = firebase_admin.get_app()
        self.db = firestore.client()
    
        self.room_ref = None
        self.room_name = None
        self.user_name = None
        self.listener = None

    def set_offer(self, room_name, user_name, offer, events_instance):
        self.room_name = room_name
        self.user_name = user_name
        
        self.room_ref = self.db.collection("rooms").document(room_name)
        self.room_ref.set({
            "name": room_name,
            "initiator": user_name,
            "created_at": firestore.SERVER_TIMESTAMP,
            "offer": offer
        })
        self._setup_room_listener(events_instance)

    def get_offer(self, room_name, user_name):
        self.room_name = room_name
        self.user_name = user_name

        self.room_ref = self.db.collection("rooms").document(room_name)
        self.room_ref.update({"responder": user_name})
        
        doc = self.room_ref.get()
        if doc.exists:
            return doc.to_dict().get("offer")
        logger.error(f"Room {room_name} does not exist")
        return None
    
    def get_answer(self):
        if not self.room_ref:
            return None
        doc = self.room_ref.get()
        if doc.exists:
            return doc.to_dict().get("answer")
        return None

    def set_answer(self,value):
        self.room_ref.update({"answer": value})
    
    def _setup_room_listener(self, events_instance):
        def on_room_update(doc_snapshot, changes, read_time):
            for doc in doc_snapshot:
                data = doc.to_dict()
                if "answer" in data and data["answer"]:
                    events_instance.add_event('answer_received', data["answer"])
                    threading.Timer(0.1, lambda: self._cleanup_listener()).start() 
        
        if self.listener:
            self._cleanup_listener()
        self.listener = self.room_ref.on_snapshot(on_room_update)
    
    def _cleanup_listener(self):
        if self.listener:
            try:
                self.listener.unsubscribe()
            except:
                pass
            self.listener = None

    def _reset_signaling(self):
        self._cleanup_listener()
        self.room_ref = None
        self.room_name = None
        self.user_name = None


class WebRTCManager:
    def __init__(self, events_instance, loop):
        self.pc = None
        self.data_channel = None
        self.is_initiator = False
        self.signaling_manager = SignalingManager()
        self.events = events_instance
        self.loop = loop
        
        self.file_chunks = {}
        self.current_file_metadata = None
        self.received_chunks = 0
        
    async def _create_offer(self, room_name, user_name):
        # Close existing connection if any
        if self.pc:
            await self.pc.close()
        
        ice_servers = [RTCIceServer(urls=[url]) for url in STUN_SERVERS]
        self.pc = RTCPeerConnection(RTCConfiguration(iceServers=ice_servers))
        self._setup_pc_handlers()
        self.is_initiator = True
        
        self.data_channel = self.pc.createDataChannel("file_transfer")
        self._setup_datachannel_handlers()
        
        offer = await self.pc.createOffer()
        await self.pc.setLocalDescription(offer)
        await self._wait_for_ice_gathering()
        
        offer_str = object_to_string(self.pc.localDescription)
        self.signaling_manager.set_offer(room_name, user_name, offer_str, self.events)
        self.events.add_event('offer_created', offer_str)

    async def _create_answer(self, room_name, user_name):
        # Close existing connection if any
        if self.pc:
            await self.pc.close()
        
        ice_servers = [RTCIceServer(urls=[url]) for url in STUN_SERVERS]
        self.pc = RTCPeerConnection(RTCConfiguration(iceServers=ice_servers))
        self._setup_pc_handlers()
        
        offer_str = self.signaling_manager.get_offer(room_name, user_name)
        if not offer_str:
            self.events.add_event('error', 'No offer found in room')
            return
            
        offer = object_from_string(offer_str)
        await self.pc.setRemoteDescription(offer)
        
        answer = await self.pc.createAnswer()
        await self.pc.setLocalDescription(answer)
        await self._wait_for_ice_gathering()
        
        answer_str = object_to_string(self.pc.localDescription)
        self.signaling_manager.set_answer(answer_str)
        self.events.add_event('answer_created', answer_str)

    async def _set_answer(self, answer_str=None):
        if not answer_str:
            answer_str = self.signaling_manager.get_answer()
        
        if not answer_str:
            self.events.add_event('error', 'No answer available')
            return
            
        try:
            answer = object_from_string(answer_str)
            await self.pc.setRemoteDescription(answer)
        except Exception as e:
            self.events.add_event('error', f'Failed to set answer: {str(e)}')
  
    async def _wait_for_ice_gathering(self):
        for _ in range(ICE_GATHERING_TIMEOUT * 10):
            if self.pc.iceGatheringState == "complete":
                break
            await asyncio.sleep(0.1)

    def _setup_pc_handlers(self):
        @self.pc.on("connectionstatechange")
        async def on_connectionstatechange():
            self.events.add_event('connection_state_changed', self.pc.connectionState)
        
        @self.pc.on("datachannel")
        def on_datachannel(channel):
            self.data_channel = channel
            self._setup_datachannel_handlers()
    
    def _setup_datachannel_handlers(self):
        @self.data_channel.on("message")
        def on_message(message):
            # Use the correct event loop
            asyncio.run_coroutine_threadsafe(self._handle_message(message), self.loop)
    
    async def _handle_message(self, message):
        if isinstance(message, str):
            data = json.loads(message)
            if data.get('type') == 'file_metadata':
                self.current_file_metadata = FileMetadata(**data['metadata'])
                self.file_chunks = {}
                self.received_chunks = 0
            elif data.get('type') == 'file_complete':
                await self._assemble_file()
            elif data.get('type') == 'text_message':
                self.events.add_event('message_received', data['content'])
        elif isinstance(message, bytes):
            await self._handle_file_chunk(message)

    async def _handle_file_chunk(self, chunk_data):
        if not self.current_file_metadata:
            return
        
        chunk_index = int.from_bytes(chunk_data[:4], byteorder='big')
        chunk_content = chunk_data[4:]
        self.file_chunks[chunk_index] = chunk_content
        self.received_chunks += 1
        
        progress = (self.received_chunks / self.current_file_metadata.total_chunks) * 100
        self.events.add_event('progress', {'progress': progress, 'is_sending': False})   
    
    async def _assemble_file(self):
        if not self.current_file_metadata or not self.file_chunks:
            return
        
        file_data = b''
        for i in range(self.current_file_metadata.total_chunks):
            if i not in self.file_chunks:
                return
            file_data += self.file_chunks[i]
        
        file_hash = hashlib.sha256(file_data).hexdigest()
        if file_hash != self.current_file_metadata.file_hash:
            return
        
        downloads_dir = os.path.expanduser("~/Downloads/Telekinesis")
        os.makedirs(downloads_dir, exist_ok=True)
        file_path = os.path.join(downloads_dir, self.current_file_metadata.filename)
        
        counter = 1
        original_path = file_path
        while os.path.exists(file_path):
            name, ext = os.path.splitext(original_path)
            file_path = f"{name}_{counter}{ext}"
            counter += 1
        
        with open(file_path, 'wb') as f:
            f.write(file_data)
        
        self.events.add_event('file_received', {
            'path': file_path,
            'filename': self.current_file_metadata.filename
        })
        
        self.file_chunks = {}
        self.current_file_metadata = None
        self.received_chunks = 0
    
    async def _send_message(self, message):
        if self.data_channel and self.data_channel.readyState == "open":
            msg = {'type': 'text_message', 'content': message}
            self.data_channel.send(json.dumps(msg))

    async def _send_file(self, file_path):
        if not self.data_channel or self.data_channel.readyState != "open":
            self.events.add_event('error', 'Data channel not ready for file transfer')
            return
        
        if not os.path.exists(file_path):
            self.events.add_event('error', f'File not found: {file_path}')
            return
        
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        filename = os.path.basename(file_path)
        file_size = len(file_data)
        chunk_size = DEFAULT_CHUNK_SIZE
        total_chunks = (file_size + chunk_size - 1) // chunk_size
        file_hash = hashlib.sha256(file_data).hexdigest()
        
        metadata = {
            'type': 'file_metadata',
            'metadata': {
                'filename': filename,
                'size': file_size,
                'chunk_size': chunk_size,
                'total_chunks': total_chunks,
                'file_hash': file_hash
            }
        }
        self.data_channel.send(json.dumps(metadata))
        
        for i in range(total_chunks):
            start = i * chunk_size
            end = min(start + chunk_size, file_size)
            chunk = file_data[start:end]
            chunk_with_index = i.to_bytes(4, byteorder='big') + chunk
            self.data_channel.send(chunk_with_index)
            
            progress = ((i + 1) / total_chunks) * 100
            self.events.add_event('progress', {'progress': progress, 'is_sending': True})
            await asyncio.sleep(CHUNK_DELAY)
        
        self.data_channel.send(json.dumps({'type': 'file_complete'}))
        
        if 'temp' in file_path and os.path.exists(file_path):
            os.remove(file_path)

    def _reset(self):
        if self.pc:
            asyncio.run_coroutine_threadsafe(self.pc.close(), self.loop)
        self.pc = None
        self.data_channel = None
        self.is_initiator = False
        self.signaling_manager._reset_signaling()
        self.file_chunks = {}
        self.current_file_metadata = None
        self.received_chunks = 0
    
    def get_status(self):
        if self.pc:
            return {
                'has_connection': True,
                'connection_state': self.pc.connectionState,
                'is_connected': (self.pc.connectionState == "connected" and 
                               self.data_channel and 
                               self.data_channel.readyState == "open")
            }
        else:
            return {
                'has_connection': False,
                'connection_state': 'disconnected',
                'is_connected': False
            }
class NetworkingManager:
    def __init__(self):
        self._loop = None
        self._loop_thread = None
        self.events = Events()
        self._start_event_loop()
        self._start_event_processor()
        self.web_rtc_manager = WebRTCManager(self.events, self._loop)
    
    def _start_event_loop(self):
        def start_loop():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_forever()
        
        self._loop_thread = threading.Thread(target=start_loop, daemon=True)
        self._loop_thread.start()
        time.sleep(0.1)
        
    def _start_event_processor(self):
        def process_events():
            while True:
                try:
                    event = self.events.get_event(timeout=1)
                    self._handle_event(event)
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"Event processing error: {e}")
        
        threading.Thread(target=process_events, daemon=True).start()

    def _handle_event(self, event):
        event_type = event['type']
        data = event['data']
        
        if event_type == 'answer_received':
            asyncio.run_coroutine_threadsafe(self.web_rtc_manager._set_answer(data), self._loop)
        elif event_type == 'offer_created':
            logger.info(f"Offer created")
        elif event_type == 'answer_created':
            logger.info(f"Answer created")  
        elif event_type == 'file_received':
            logger.info(f"File received: {data['filename']}")
        elif event_type == 'message_received':
            logger.info(f"Message received: {data}")
        elif event_type == 'connection_state_changed':
            logger.info(f"Connection state: {data}")
        elif event_type == 'error':
            logger.error(f"Error: {data}")
        elif event_type == 'progress':
            if isinstance(data, dict) and 'progress' in data:
                logger.info(f"Progress: {data['progress']}% ({'sending' if data.get('is_sending') else 'receiving'})")
        
        SSEManager.sse_callback(event_type, data)
    
    
    def create_room(self, room_name, user_name):       
        asyncio.run_coroutine_threadsafe(self.web_rtc_manager._create_offer(room_name, user_name), self._loop)
    
    def join_room(self, room_name, user_name):
        asyncio.run_coroutine_threadsafe(self.web_rtc_manager._create_answer(room_name, user_name), self._loop)
               
    def send_file(self, file_path):
        asyncio.run_coroutine_threadsafe(self.web_rtc_manager._send_file(file_path), self._loop)
    
    def send_message(self, message):
        asyncio.run_coroutine_threadsafe(self.web_rtc_manager._send_message(message), self._loop)
    
    def disconnect(self):
        if self.web_rtc_manager.pc:
            asyncio.run_coroutine_threadsafe(self.web_rtc_manager.pc.close(), self._loop)
        self.web_rtc_manager._reset()
        self.events.clear_queue()
        SSEManager.reset_sse_queue()
        if self._loop and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(self._loop.stop)
    
    def get_status(self):
        return self.web_rtc_manager.get_status()
    
    def get_events(self):
        events = {}
        status = self.get_status()
        events.update(status)
        return events

class SSEManager:
    event_queue = queue.Queue()
    event_queue_lock = threading.Lock()
    
    @staticmethod
    def sse_callback(event_type, data):
        event = {
            'type': event_type, 
            'data': data, 
            'timestamp': time.time()
        }
        logger.info(f"📤 Queuing SSE event: {event}")
        SSEManager.event_queue.put(event)

    @staticmethod
    def reset_sse_queue():
        with SSEManager.event_queue_lock:
            while not SSEManager.event_queue.empty():
                try:
                    SSEManager.event_queue.get_nowait()
                except queue.Empty:
                    break