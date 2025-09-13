from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, HttpUrl, validator
import httpx
import uuid
import os
from typing import Optional
import logging
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Article Summarizer API",
    description="Backend service that forwards article processing requests to n8n workflow",
    version="1.0.0"
)

# CORS middleware - Permissive for testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=False,  # Must be False when allow_origins=["*"]
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Environment variables
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")
RENDER_ENVIRONMENT = os.getenv("RENDER")

# Log configuration info
logger.info(f"Starting Article Summarizer API...")
logger.info(f"Render Environment: {'✅' if RENDER_ENVIRONMENT else '❌'}")
logger.info(f"N8N Webhook URL configured: {'✅' if N8N_WEBHOOK_URL else '❌'}")

if not N8N_WEBHOOK_URL:
    logger.warning("⚠️  N8N_WEBHOOK_URL not set. Please configure it in Render environment variables.")
    logger.warning("   Go to Render Dashboard → Your Service → Environment → Add N8N_WEBHOOK_URL")
else:
    logger.info(f"✅ N8N Webhook URL: {N8N_WEBHOOK_URL}")

def validate_url(url_str: str) -> str:
    """Validate and clean URL"""
    url_str = url_str.strip()
    
    # Add protocol if missing
    if not url_str.startswith(('http://', 'https://')):
        url_str = 'https://' + url_str
    
    # Basic URL validation
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    if not url_pattern.match(url_str):
        raise ValueError("Invalid URL format")
    
    return url_str

# Request/Response models
class ArticleSubmission(BaseModel):
    email: EmailStr
    article_url: str  # Changed from HttpUrl to str for custom validation
    
    @validator('article_url')
    def validate_article_url(cls, v):
        try:
            return validate_url(v)
        except ValueError as e:
            raise ValueError(f"Invalid article URL: {str(e)}")

class SubmissionResponse(BaseModel):
    success: bool
    message: str
    session_id: str

class HealthCheck(BaseModel):
    status: str
    version: str
    cors_enabled: bool = True

# Add explicit OPTIONS handler for CORS preflight
@app.options("/{path:path}")
async def options_handler(path: str):
    """Handle CORS preflight requests"""
    return {"message": "OK"}

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
        },
        "cors_configured": True
    }

@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint"""
    return HealthCheck(
        status="healthy",
        version="1.0.0",
        cors_enabled=True
    )

@app.post("/submit", response_model=SubmissionResponse)
async def submit_article(submission: ArticleSubmission):
    """
    Submit article for processing via n8n workflow
    
    This endpoint:
    1. Validates and formats the URL
    2. Generates a unique session ID
    3. Forwards the request to n8n webhook
    4. Returns success response to frontend
    """
    
    if not N8N_WEBHOOK_URL:
        logger.error("N8N_WEBHOOK_URL not configured")
        raise HTTPException(
            status_code=500,
            detail="Service configuration error. Please contact administrator."
        )
    
    # Generate unique session ID
    session_id = str(uuid.uuid4())
    
    # URL is already validated by pydantic validator
    article_url_str = submission.article_url
    
    # Log for debugging
    logger.info(f"Processing article submission - Session ID: {session_id}")
    logger.info(f"Email: {submission.email}")
    logger.info(f"Validated URL: {article_url_str}")
    
    # Prepare payload for n8n
    n8n_payload = {
        "email": str(submission.email),
        "article_url": article_url_str,
        "session_id": session_id
    }
    
    logger.info(f"Sending payload to n8n: {n8n_payload}")
    
    try:
        # Forward to n8n webhook with longer timeout
        async with httpx.AsyncClient(timeout=60.0) as client:
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
            logger.info(f"n8n response body: {response.text}")
            
            if response.status_code not in [200, 201]:
                logger.error(f"n8n webhook error: {response.text}")
                # Still return success to user, as n8n might process it async
                logger.warning("n8n returned non-200 status, but continuing...")
        
        logger.info(f"Successfully forwarded to n8n - Session ID: {session_id}")
        
        return SubmissionResponse(
            success=True,
            message="Article submitted successfully. You'll receive the summary by email shortly.",
            session_id=session_id
        )
        
    except httpx.TimeoutException:
        logger.error(f"Timeout while calling n8n webhook - Session ID: {session_id}")
        # Return success anyway, as the request might still be processing
        return SubmissionResponse(
            success=True,
            message="Article submitted successfully. Processing may take a few minutes. Check your email.",
            session_id=session_id
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
    logger.info(f"🌍 CORS enabled for all origins (testing mode)")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=False,  # Disable reload in production
        log_level="info"
    )
