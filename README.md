# Article Summarizer 📰

A full-stack application that automatically summarizes articles and sends insights via email. Built with a modern tech stack including React frontend, FastAPI backend, and n8n workflow automation.

## 🌐 Live Demo

**Frontend**: [https://smart-summary-mail.vercel.app/](https://smart-summary-mail.vercel.app/)

## 🏗️ Architecture

This project follows a microservices architecture with three main components:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend API   │    │   n8n Workflow  │
│   (Vercel)      │───▶│   (Render)      │───▶│   (n8n Cloud)   │
│   React/Next.js │    │   FastAPI       │    │   Automation    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
                                              ┌─────────────────┐
                                              │   External APIs │
                                              │   • Firecrawl   │
                                              │   • Google AI   │
                                              │   • Gmail       │
                                              │   • Sheets      │
                                              └─────────────────┘
```

## ✨ Features

- **Article Processing**: Submit any article URL for automatic processing
- **AI-Powered Analysis**: Uses Google Gemini 2.5 Flash for intelligent summarization
- **Smart Insights**: Extracts 3-5 key insights from articles
- **Email Delivery**: Sends formatted summaries directly to your inbox
- **Data Storage**: Maintains records in Google Sheets for tracking
- **Web Scraping**: Uses Firecrawl for clean content extraction
- **Modern UI**: Responsive design built with React and modern frameworks

## 🛠️ Tech Stack

### Frontend
- **Framework**: React/Next.js (created with Lovable)
- **Hosting**: Vercel
- **Styling**: Modern CSS with responsive design

### Backend API
- **Framework**: FastAPI (Python)
- **Hosting**: Render (Free tier)
- **Features**: 
  - CORS middleware for cross-origin requests
  - Input validation with Pydantic
  - Async HTTP client with httpx
  - Comprehensive error handling and logging

### Workflow Automation
- **Platform**: n8n Cloud
- **Components**:
  - Webhook trigger
  - Firecrawl web scraper
  - Google Gemini AI for summarization and insights
  - Gmail for email delivery
  - Google Sheets for data storage

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- n8n Cloud account
- Google Cloud account (for Gemini API)
- Firecrawl API key
- Gmail account for sending emails

### Backend Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd article-summarizer
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set environment variables**
   ```bash
   export N8N_WEBHOOK_URL="your-n8n-webhook-url"
   export PORT=8000
   ```

4. **Run the development server**
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

### n8n Workflow Setup

1. **Import the workflow**
   - Copy the contents of `My workflow.json`
   - Import into your n8n Cloud instance

2. **Configure credentials**
   - **Firecrawl API**: Add your Firecrawl API credentials
   - **Google Gemini**: Configure Google PaLM API access
   - **Gmail**: Set up Gmail OAuth2 credentials
   - **Google Sheets**: Configure Google Sheets OAuth2 credentials

3. **Update webhook URL**
   - Copy the webhook URL from n8n
   - Set it as `N8N_WEBHOOK_URL` in your backend environment

### Frontend Deployment

The frontend is deployed on Vercel and configured to communicate with the Render-hosted backend API.

## 📁 Project Structure

```
article-summarizer/
├── main.py                 # FastAPI backend application
├── requirements.txt        # Python dependencies
├── render.yaml            # Render deployment configuration
├── My workflow.json       # n8n workflow definition
└── README.md              # This file
```

## 🔄 Workflow Process

1. **User submits article URL** via the frontend form
2. **Backend validates** the URL and generates a session ID
3. **Request forwarded** to n8n webhook with email, URL, and session ID
4. **n8n workflow executes**:
   - Scrapes article content using Firecrawl
   - Generates summary using Google Gemini AI
   - Extracts insights using Google Gemini AI
   - Stores data in Google Sheets
   - Sends formatted email via Gmail
5. **User receives** summary and insights via email

## 📧 Email Template

The system sends beautifully formatted HTML emails containing:
- **Article Summary**: 3-5 sentence overview
- **Key Insights**: Numbered list of important takeaways
- **Professional formatting** with clear sections

## 🌍 Deployment

### Backend (Render)
- **Platform**: Render (Free tier)
- **Configuration**: `render.yaml`
- **Command**: `gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT`
- **Environment variables**:
  - `N8N_WEBHOOK_URL`: Your n8n webhook URL
  - `PORT`: Auto-generated by Render
  - `RENDER_EXTERNAL_URL`: Auto-generated by Render

### Frontend (Vercel)
- **Platform**: Vercel
- **URL**: https://smart-summary-mail.vercel.app/
- **Auto-deployment**: Connected to Git repository

### Workflow (n8n Cloud)
- **Platform**: n8n Cloud
- **Features**: 
  - Webhook triggers
  - Credential management
  - Execution monitoring

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `N8N_WEBHOOK_URL` | n8n webhook endpoint | Yes |
| `PORT` | Server port (auto-set by Render) | No |
| `RENDER_EXTERNAL_URL` | External service URL | No |

### API Endpoints

- `GET /` - API information and endpoints
- `GET /health` - Health check endpoint
- `POST /submit` - Submit article for processing
- `GET /docs` - FastAPI auto-generated documentation

## 📊 Monitoring & Logging

- **Backend**: Comprehensive logging with Python's logging module
- **n8n**: Built-in execution monitoring and error handling
- **Frontend**: Error boundaries and user feedback

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request


## 🙏 Acknowledgments

- **Lovable** - For the beautiful frontend creation
- **Vercel** - For seamless frontend hosting
- **Render** - For reliable backend hosting
- **n8n** - For powerful workflow automation
- **Google AI** - For intelligent content processing
- **Firecrawl** - For clean web scraping capabilities

---

**Built with ❤️ using modern web technologies**
