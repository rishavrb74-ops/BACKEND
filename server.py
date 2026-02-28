from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timezone


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str

# Investor Request Models
class InvestorRequestCreate(BaseModel):
    full_name: str
    email: EmailStr
    company: str
    title: str
    phone: Optional[str] = None
    message: Optional[str] = None

class InvestorRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    full_name: str
    email: str
    company: str
    title: str
    phone: Optional[str] = None
    message: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Partnership Inquiry Models
class PartnershipInquiryCreate(BaseModel):
    email: EmailStr

class PartnershipInquiry(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    subject: str = "Inquiry: Partnerships"
    forward_to: str = "office@oneaviationresources.in"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "ONE Aviation Resources API"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.model_dump()
    status_obj = StatusCheck(**status_dict)
    
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    
    _ = await db.status_checks.insert_one(doc)
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    
    for check in status_checks:
        if isinstance(check['timestamp'], str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    
    return status_checks

# Investor Request Endpoints
@api_router.post("/investor-requests", response_model=InvestorRequest)
async def create_investor_request(input: InvestorRequestCreate):
    investor_dict = input.model_dump()
    investor_obj = InvestorRequest(**investor_dict)
    
    doc = investor_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    _ = await db.investor_requests.insert_one(doc)
    return investor_obj

@api_router.get("/investor-requests", response_model=List[InvestorRequest])
async def get_investor_requests():
    requests = await db.investor_requests.find({}, {"_id": 0}).to_list(1000)
    
    for req in requests:
        if isinstance(req.get('created_at'), str):
            req['created_at'] = datetime.fromisoformat(req['created_at'])
    
    return requests

# Partnership Inquiry Endpoints
@api_router.post("/partnership-inquiries", response_model=PartnershipInquiry)
async def create_partnership_inquiry(input: PartnershipInquiryCreate):
    inquiry_dict = input.model_dump()
    inquiry_obj = PartnershipInquiry(**inquiry_dict)
    
    doc = inquiry_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    _ = await db.partnership_inquiries.insert_one(doc)
    return inquiry_obj

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
