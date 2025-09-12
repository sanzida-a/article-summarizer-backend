from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, HttpUrl
import httpx
import uuid
import os
from typing import Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Article Summarizer API",
    description="Backend service that forwards article processing requests to n8n workflow",
    version="1.0.0"
)

# CORS middleware for Vercel frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Local development
        "http://localhost:5173",  # Vite dev server
        "https://*.vercel.app",   # All Vercel deployments
        "https://smart-summary-mail.vercel.app",  # Replace with your actual Vercel URL
        "*"  # Allow all origins for testing (remove in production)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment variables
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")
RAILWAY_ENVIRONMENT = os.getenv("RAILWAY_ENVIRONMENT")

# Log configuration info
logger.info(f"Starting Article Summarizer API...")
logger.info(f"Railway Environment: {RAILWAY_ENVIRONMENT}")
logger.info(f"N8N Webhook URL configured: {'✅' if N8N_WEBHOOK_URL else '❌'}")

if not N8N_WEBHOOK_URL:
    logger.warning("⚠️  N8N_WEBHOOK_URL not set. Please configure it in Railway environment variables.")
    logger.warning("   Go to Railway Dashboard → Your Project → Variables → Add N8N_WEBHOOK_URL")
else:
    logger.info(f"✅ N8N Webhook URL: {N8N_WEBHOOK_URL}")

# Request/Response models
class ArticleSubmission(BaseModel):
    email: EmailStr
    article_url: HttpUrl

class SubmissionResponse(BaseModel):
    success: bool
    message: str
    session_id: str

class HealthCheck(BaseModel):
    status: str
    version: str

@app.get("/", response_model=dict)
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Article Summarizer API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "submit": "/submit",
            "docs": "/docs"
        }
    }

@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint"""
    return HealthCheck(
        status="healthy",
        version="1.0.0"
    )

@app.post("/submit", response_model=SubmissionResponse)
async def submit_article(submission: ArticleSubmission):
    """
    Submit article for processing via n8n workflow
    
    This endpoint:
    1. Generates a unique session ID
    2. Forwards the request to n8n webhook
    3. Returns success response to frontend
    """
    
    if not N8N_WEBHOOK_URL:
        logger.error("N8N_WEBHOOK_URL not configured")
        raise HTTPException(
            status_code=500,
            detail="Service configuration error. Please contact administrator."
        )
    
    # Generate unique session ID
    session_id = str(uuid.uuid4())
    
    # Prepare payload for n8n
    n8n_payload = {
        "email": str(submission.email),
        "article_url": str(submission.article_url),
        "session_id": session_id
    }
    
    try:
        logger.info(f"Processing article submission - Session ID: {session_id}")
        logger.info(f"Email: {submission.email}")
        logger.info(f"Article URL: {submission.article_url}")
        
        # Forward to n8n webhook
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                N8N_WEBHOOK_URL,
                json=n8n_payload,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "ArticleSummarizer-FastAPI/1.0.0"
                }
            )
            
            # Log n8n response for debugging
            logger.info(f"n8n response status: {response.status_code}")
            if response.status_code != 200:
                logger.error(f"n8n webhook error: {response.text}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to process article. Please try again later."
                )
        
        logger.info(f"Successfully forwarded to n8n - Session ID: {session_id}")
        
        return SubmissionResponse(
            success=True,
            message="Article submitted successfully. You'll receive the summary by email shortly.",
            session_id=session_id
        )
        
    except httpx.TimeoutException:
        logger.error(f"Timeout while calling n8n webhook - Session ID: {session_id}")
        raise HTTPException(
            status_code=504,
            detail="Request timeout. Please try again later."
        )
    except httpx.RequestError as e:
        logger.error(f"Network error while calling n8n webhook: {str(e)} - Session ID: {session_id}")
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable. Please try again later."
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)} - Session ID: {session_id}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Please try again later."
        )

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 10000))
    host = "0.0.0.0"
    
    logger.info(f"🚀 Starting server on {host}:{port}")
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=False  # Disable reload in production
    )