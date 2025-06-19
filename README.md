# SHIRUSHIRU AI Secretary

A comprehensive AI secretary application with dual-environment support for both local development and production Dify API integration.

## Features

- **Dual Environment Support**: Automatically switches between local backend and Dify API based on hostname
- **Mobile Optimized**: Responsive design with mobile-specific optimizations
- **Real-time Chat**: Streaming and blocking chat responses
- **File Management**: Upload and manage documents
- **Conversation History**: Persistent conversation management
- **Voice Integration**: Text-to-speech and speech-to-text capabilities

## Quick Start

### Local Development

1. **Start Local Backend**:
   ```bash
   chmod +x start-local.sh
   ./start-local.sh
   ```

2. **Access Application**:
   - Open browser to `http://localhost:8000`
   - Login with any email/password (mock authentication)
   - Start chatting with the AI assistant

### Production Deployment

The application automatically detects production environments and uses Dify API integration.

## Environment Detection

The application automatically detects the environment:

- **Local Development**: `localhost`, `127.0.0.1`, `0.0.0.0` → Uses local Node.js backend
- **Production**: Any other hostname → Uses Dify API integration

## API Configuration

### Local Backend
- **Base URL**: `http://127.0.0.1:8000`
- **Authentication**: JWT tokens
- **Features**: Full API simulation, CORS support, mock data

### Dify API
- **Base URL**: `https://api.dify.ai/v1`
- **Authentication**: API key authentication
- **Features**: Production AI responses, real data processing

## Development

### Prerequisites
- Node.js (for local backend)
- Modern web browser
- Internet connection (for Dify API integration)

### Local Backend Features
- Mock authentication system
- Streaming chat responses
- File upload simulation
- Conversation management
- CORS support for development

### Testing

1. **Test Local Environment**:
   - Start local backend: `./start-local.sh`
   - Access `http://localhost:8000`
   - Verify environment detection shows "local"
   - Test chat functionality

2. **Test Production Environment**:
   - Deploy to production domain
   - Verify environment detection shows "dify"
   - Test Dify API integration

## Mobile Optimizations

- Responsive header layout
- Avatar display optimizations
- Touch-friendly interface
- Mobile-specific chat container sizing

## File Structure

- `index.html` - Main application interface
- `script.js` - Core application logic with dual-environment support
- `style.css` - Responsive styling and mobile optimizations
- `local-backend.js` - Local development backend server
- `package.json` - Node.js dependencies
- `start-local.sh` - Local development startup script

## Contributing

1. Fork the repository
2. Create a feature branch
3. Test both local and production environments
4. Submit a pull request

## License

MIT License
