from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.routes import chat, whatsapp
import logging
import time

logger = logging.getLogger(__name__)

app = FastAPI(title="WhatsApp Agent API", version="1.0.0")

# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests for debugging"""
    start_time = time.time()
    
    # Print to console (always visible)
    print("\n" + "=" * 60)
    print(f"INCOMING REQUEST")
    print(f"Method: {request.method}")
    print(f"URL: {request.url}")
    print(f"Path: {request.url.path}")
    print(f"Client: {request.client.host if request.client else 'unknown'}")
    print("=" * 60)
    
    # Log to logger
    logger.info(f"=== INCOMING REQUEST ===")
    logger.info(f"Method: {request.method}, URL: {request.url}, Path: {request.url.path}")
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logger.info(f"Response status: {response.status_code}, Time: {process_time:.2f}s")
    logger.info(f"=== REQUEST COMPLETE ===")
    print(f"Response: {response.status_code} ({process_time:.2f}s)")
    print("=" * 60 + "\n")
    
    return response

# Add CORS middleware (configure allowed origins in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(whatsapp.router, tags=["whatsapp"])

@app.get("/")
async def root():
    return {"message": "WhatsApp Agent API is running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

