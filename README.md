# Telekinesis 🚀

**Zero-Cost Peer-to-Peer File Transfer Solution**

Telekinesis is a modern, secure, and completely free WebRTC-based file transfer application that allows two people who are not on the same network to share files directly with each other. No servers, no cloud storage, no costs - just pure peer-to-peer magic!

## ✨ Features

- 🔐 **100% Secure**: Direct peer-to-peer transfer with no intermediary servers
- 💰 **Zero Cost**: No servers to maintain, no cloud storage fees
- 🌍 **Cross-Network**: Works between different networks using STUN servers
- 📁 **Any File Type**: Transfer any file regardless of size or format
- 💬 **Real-time Chat**: Communicate while transferring files
- 🎨 **Modern UI**: Beautiful, responsive web interface
- 🔒 **Privacy First**: Files never leave the direct connection between peers
- ⚡ **Fast Transfer**: Direct connection means maximum speed

## 🛠️ Technology Stack

- **Backend**: Python Flask + WebRTC (aiortc)
- **Frontend**: Vanilla JavaScript + Modern CSS
- **Connectivity**: WebRTC DataChannels with STUN servers
- **Signaling**: Manual copy/paste method (zero-cost approach)

## 📋 Prerequisites

- Python 3.7 or higher
- A modern web browser with WebRTC support
- Internet connection (for initial peer discovery via STUN)

## 🚀 Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd Telekinesis

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Run the Application

```bash
# Start the server
python server.py
```

The application will start on `http://localhost:5000`

### 3. Connect Two Peers

**On Computer A (Initiator):**
1. Open `http://localhost:5000` in your browser
2. Click "Create Offer"
3. Copy the generated connection offer
4. Send it to the other person (via email, chat, etc.)

**On Computer B (Responder):**
1. Open `http://localhost:5000` in your browser  
2. Paste the received offer in the "Join Connection" section
3. Click "Create Answer"
4. Copy the generated answer
5. Send it back to Person A

**Back on Computer A:**
1. Paste the received answer in the "Complete Connection" section
2. Click "Complete Connection"

🎉 **You're now connected!** Both parties can transfer files and chat.

## 📖 How to Use

### Transferring Files

1. **Select File**: Click the upload area or drag & drop a file
2. **Send**: Click "Send File" to start the transfer
3. **Monitor**: Watch the progress bar for transfer status
4. **Receive**: Files are automatically saved to your Downloads folder

### Chat Feature

- Type messages in the chat input and press Enter
- Messages appear in real-time on both sides
- Use chat to coordinate file transfers

### Connection Management

- **Status Indicator**: Shows current connection state
- **Disconnect**: Use the disconnect button to end the session
- **Reconnect**: Start a new offer/answer exchange to reconnect

## 🔧 Troubleshooting

### Connection Issues

**Problem**: Connection fails to establish
- **Solution**: Ensure both parties are using modern browsers with WebRTC support
- **Solution**: Check firewall settings and try different networks
- **Solution**: Make sure to copy/paste the complete offer/answer text

**Problem**: File transfer is slow
- **Solution**: Direct WebRTC connections should be fast; slow transfers might indicate routing through TURN servers
- **Solution**: Try closing other bandwidth-intensive applications

**Problem**: Files not received
- **Solution**: Check your Downloads folder permissions
- **Solution**: Ensure sufficient disk space
- **Solution**: Verify the connection status shows "Connected"

### Browser Compatibility

- ✅ Chrome 80+
- ✅ Firefox 75+
- ✅ Safari 14+
- ✅ Edge 80+

## 🏗️ Architecture

```
┌─────────────────┐         ┌─────────────────┐
│   Computer A    │         │   Computer B    │
│                 │         │                 │
│ ┌─────────────┐ │         │ ┌─────────────┐ │
│ │ Browser     │ │         │ │ Browser     │ │
│ │ (Frontend)  │ │◄──────► │ │ (Frontend)  │ │
│ └─────────────┘ │WebRTC   │ └─────────────┘ │
│       │         │DataChannel│       │        │
│ ┌─────────────┐ │         │ ┌─────────────┐ │
│ │ Flask       │ │         │ │ Flask       │ │
│ │ Server      │ │         │ │ Server      │ │
│ │ (Backend)   │ │         │ │ (Backend)   │ │
│ └─────────────┘ │         │ └─────────────┘ │
└─────────────────┘         └─────────────────┘
         │                           │
         └──────── STUN Servers ─────┘
              (For NAT traversal)
```

## 📁 Project Structure

```
Telekinesis/
├── server.py              # Flask web server
├── networking.py          # WebRTC connection management
├── requirements.txt       # Python dependencies
├── templates/
│   └── index.html         # Main web interface
├── static/
│   ├── main_style.css     # Styling
│   └── main_script.js     # Frontend logic
└── README.md              # This file
```

## 🔒 Security & Privacy

- **No Cloud Storage**: Files transfer directly between peers
- **No Server Storage**: No files are stored on any intermediate servers
- **Encrypted Transfer**: WebRTC provides built-in encryption
- **No Data Collection**: The application doesn't collect or store any user data
- **Local Processing**: All file handling happens locally on your machine

## 🤝 Contributing

Contributions are welcome! Here are some areas for improvement:

- **Mobile Support**: Optimize for mobile browsers
- **Resume Transfers**: Add ability to resume interrupted transfers
- **Multiple Files**: Support for multiple file selection
- **Compression**: Add file compression options
- **Advanced Chat**: File previews, emoji support
- **P2P Discovery**: Automatic peer discovery mechanisms

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## ⚠️ Limitations

- **Signaling**: Requires manual copy/paste for connection setup
- **Firewall**: May not work through very restrictive firewalls
- **Single Session**: One file transfer at a time per connection
- **Browser Dependent**: Requires WebRTC-compatible browsers

## 🆘 Support

If you encounter issues:

1. Check the browser console for error messages
2. Verify all dependencies are installed correctly
3. Ensure both parties are using supported browsers
4. Try different networks if connection fails

## 🔮 Future Enhancements

- **QR Code Sharing**: Generate QR codes for easier connection setup
- **Multi-peer Support**: Connect multiple people simultaneously
- **File Sync**: Folder synchronization capabilities
- **Mobile App**: Native mobile applications
- **Enhanced Security**: Additional encryption layers

---

**Made with ❤️ for secure, private, and free file sharing**

