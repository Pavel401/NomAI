# NomAI Backend API

A comprehensive AI-powered nutrition analysis API with chat functionality.

## Features

- **Nutrition Analysis**: AI-powered food and nutrition analysis
- **Chat Assistant**: Interactive chat interface with AI assistant
- **RESTful API**: Well-structured API endpoints
- **Database Integration**: SQLite for chat history, PostgreSQL for main data
- **Environment Configuration**: Flexible environment-based configuration

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Configuration**:
   - Copy `env_template` to `.env`
   - Fill in the required environment variables:
     - `OPENAI_API_KEY`: Your OpenAI API key for chat functionality
     - `POSTGRESQL_DB_URL`: PostgreSQL database URL
     - `DB_KEY`: Database encryption key
     - `SUPABASE_URL`: Supabase URL (if using)
     - `PROD`: Set to `true` for production, `false` for development

3. **Run the Application**:
   ```bash
   python main.py
   ```

## API Endpoints

### Nutrition Analysis
- `GET /nutrition/` - Nutrition analysis endpoints
- `POST /nutrition/analyze` - Analyze food nutrition

### Chat Assistant
- `GET /chat/` - Chat interface (HTML)
- `GET /chat/messages` - Get chat history
- `POST /chat/messages` - Send chat message
- `GET /chat/chat_app.ts` - TypeScript frontend code

### Health Check
- `GET /` - Basic health check
- `GET /health` - Detailed health check

## Architecture

```
Backend/
├── app/
│   ├── api/endpoints/       # API route handlers
│   ├── models/             # Pydantic models
│   ├── services/           # Business logic services
│   ├── utils/              # Utility functions
│   ├── middleware/         # FastAPI middleware
│   ├── constants/          # Constants and configurations
│   └── exceptions/         # Custom exceptions
├── static/                 # Static files (HTML, CSS, JS)
├── main.py                 # FastAPI application entry point
├── requirements.txt        # Python dependencies
└── env_template           # Environment variables template
```

## Chat Functionality

The chat functionality is built using:
- **pydantic-ai**: For AI agent management
- **OpenAI GPT-4**: As the underlying language model
- **SQLite**: For chat history persistence
- **WebSockets**: For real-time streaming responses
- **TypeScript**: For frontend chat interface

## Development

For development, set `PROD=false` in your environment variables to enable:
- Auto-reload on code changes
- Debug mode
- Detailed error messages

## Deployment

The application is configured for deployment on platforms like Railway, Heroku, or similar:
- `Procfile`: Deployment configuration
- `runtime.txt`: Python version specification
- `railway.json`: Railway-specific configuration

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is proprietary and confidential.