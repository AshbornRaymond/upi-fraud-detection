"""
FastAPI backend for UPI Fraud Detection System

This is the main web server that handles all incoming requests for fraud detection.
It uses FastAPI (a modern Python web framework) to create API endpoints that can
validate links, VPAs, messages, and QR codes for potential fraud.
"""

# Import necessary libraries
import sys  # For system-level operations like path manipulation
import logging  # For tracking what's happening in the application
from pathlib import Path  # For working with file paths in a clean way
from fastapi import FastAPI, HTTPException, UploadFile, File, Form  # Web framework components
from fastapi.staticfiles import StaticFiles  # For serving HTML/CSS/JS files
from fastapi.responses import JSONResponse  # For sending JSON responses
from fastapi.middleware.cors import CORSMiddleware  # For handling cross-origin requests

# Setup paths - figure out where the project root directory is
# This helps Python find all our other modules
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Setup logging - this helps us see what's happening when the server runs
# It prints messages with timestamps so we can track issues
logging.basicConfig(
    level=logging.INFO,  # Show INFO level and above (INFO, WARNING, ERROR)
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'  # How to format log messages
)
logger = logging.getLogger(__name__)  # Create a logger for this file

# Import the orchestrator module which handles all validation logic
# We use try-except to catch any errors during import
try:
    from backend.orchestrator import validate_input
    logger.info("✓ Successfully imported orchestrator")
except ImportError as e:
    logger.error(f"✗ Failed to import orchestrator: {e}")
    raise  # Stop the program if orchestrator can't be loaded

# Create the FastAPI application instance
# This is the main server object that will handle all web requests
app = FastAPI(title="UPI Fraud Detection API")

# Setup CORS (Cross-Origin Resource Sharing)
# This allows the web frontend to communicate with the backend
# even if they're running on different ports or domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow requests from any origin (for development)
    allow_credentials=True,  # Allow cookies to be sent
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

# Mount static files (HTML, CSS, JavaScript)
# This makes the web interface accessible through the server
static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

@app.get("/health")
async def health():
    """
    Health check endpoint
    
    This is a simple endpoint that tells us if the server is running properly.
    The frontend calls this when the page loads to show the connection status.
    
    Returns a JSON object with status information.
    """
    return {
        "status": "healthy",
        "service": "Detection Engine",
        "version": "1.0 (beta)"
    }

@app.post("/validate")
async def validate(
    type: str = Form(...),  # The type of validation: "link", "vpa", "message", or "qr"
    value: str = Form(None),  # The actual text to validate (not used for QR)
    file: UploadFile = File(None)  # The QR code image file (only for QR validation)
):
    """
    Main validation endpoint
    
    This is the core endpoint that processes all validation requests from the frontend.
    It accepts different types of inputs and routes them to the appropriate validator.
    
    Accepts:
        - link: URL validation (e.g., https://example.com)
        - vpa: Virtual Payment Address validation (e.g., username@bank)
        - message: SMS/message text validation
        - qr: QR code image validation
    
    Returns a JSON response with the validation result including:
        - verdict: "OK", "WARN", or "BLOCK"
        - risk_score: A number between 0 and 1
        - reasons: List of reasons for the verdict
    """
    # Log the incoming request for debugging
    logger.info(f"Received request - type: {type}, value: {value}, file: {file.filename if file else None}")
    
    try:
        # Handle QR code validation differently because it needs a file
        if type == "qr":
            if not file:
                # Return error if QR type selected but no file uploaded
                raise HTTPException(status_code=400, detail="File required for QR validation")
            # Read the uploaded file as bytes
            file_data = await file.read()
            # Send to orchestrator for validation
            result = validate_input("qr", None, file_data)
        else:
            # For all other types (link, vpa, message), we need text value
            if not value:
                raise HTTPException(status_code=400, detail="Value required")
            # Send to orchestrator for validation
            result = validate_input(type, value)
        
        # Check if validation returned an error
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        # Return the validation result as JSON
        return JSONResponse(content=result)
        
    except HTTPException:
        # Re-raise HTTP exceptions (these are expected errors)
        raise
    except Exception as e:
        # Log unexpected errors and return a generic error message
        logger.error(f"Validation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # This code only runs when we start the file directly
    # (not when importing it as a module)
    import uvicorn  # Web server to run FastAPI
    
    # Print startup banner with important information
    logger.info("=" * 60)
    logger.info("🚀 Starting UPI Fraud Detection System")
    logger.info("=" * 60)
    logger.info(f"ROOT directory: {ROOT}")
    logger.info("Server: http://localhost:8008")
    logger.info("Docs: http://localhost:8008/docs")  # FastAPI auto-generates API documentation
    logger.info("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8008)