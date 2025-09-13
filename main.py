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

# CORS middleware - Fixed for Render deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Local development
        "http://localhost:5173",  # Vite dev server
        "https://smart-summary-mail.vercel.app",  # Your Vercel app
        "https://*.vercel.app",   # All Vercel deployments
        "*"  # Allow all origins (remove in production if needed)
    ],
    allow_credentials=False,  # Set to False when using "*" in origins
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Environment variables - Fixed for Render
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")
RENDER_SERVICE_NAME = os.getenv("RENDER_SERVICE_NAME")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")

# Log configuration info
logger.info(f"Starting Article Summarizer API...")
logger.info(f"Render Service: {RENDER_SERVICE_NAME}")
logger.info(f"Render External URL: {RENDER_EXTERNAL_URL}")
logger.info(f"N8N Webhook URL configured: {'✅' if N8N_WEBHOOK_URL else '❌'}")

if not N8N_WEBHOOK_URL:
    logger.warning("⚠️  N8N_WEBHOOK_URL not set. Please configure it in Render environment variables.")
    logger.warning("   Go to Render Dashboard → Your Service → Environment → Add N8N_WEBHOOK_URL")
else:
    logger.info(f"✅ N8N Webhook URL configured")

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
    service_name: Optional[str] = None
    external_url: Optional[str] = None

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
        "platform": "Render",
        "service": RENDER_SERVICE_NAME,
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
        version="1.0.0",
        service_name=RENDER_SERVICE_NAME,
        external_url=RENDER_EXTERNAL_URL
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
    
    logger.info(f"Sending payload to n8n webhook")
    
    try:
        # Forward to n8n webhook with proper timeout for Render
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                N8N_WEBHOOK_URL,
                json=n8n_payload,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "ArticleSummarizer-Render/1.0.0"
                }
            )
            
            # Log n8n response for debugging
            logger.info(f"n8n response status: {response.status_code}")
            
            if response.status_code not in [200, 201]:
                logger.warning(f"n8n webhook returned status {response.status_code}: {response.text}")
                # Don't fail immediately as n8n might still process it async
            else:
                logger.info("Successfully sent to n8n webhook")
        
        logger.info(f"Request processed - Session ID: {session_id}")
        
        return SubmissionResponse(
            success=True,
            message="Article submitted successfully. You'll receive the summary by email shortly.",
            session_id=session_id
        )
        
    except httpx.TimeoutException:
        logger.error(f"Timeout while calling n8n webhook - Session ID: {session_id}")
        # Return success anyway as the request might still be processing
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
    
    # Render provides PORT environment variable
    port = int(os.getenv("PORT", 10000))
    host = "0.0.0.0"
    
    logger.info(f"🚀 Starting server on {host}:{port}")
    logger.info(f"🌍 CORS configured for production")
    logger.info(f"📡 Ready to receive requests on Render")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=False,  # Always False in production
        log_level="info",
        access_log=True
    )
