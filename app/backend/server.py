from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")


class Campaign(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: Optional[str] = ""
    channel: str
    status: str = "draft"
    date: str
    time: Optional[str] = "09:00"
    color: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CampaignCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    channel: str
    status: str = "draft"
    date: str
    time: Optional[str] = "09:00"
    color: str

class CampaignUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    channel: Optional[str] = None
    status: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    color: Optional[str] = None

class Channel(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    label: str
    color: str
    is_default: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ChannelCreate(BaseModel):
    name: str
    label: str
    color: str

class Template(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    channel: str
    default_content: str


@api_router.get("/")
async def root():
    return {"message": "Marketing Calendar API"}


@api_router.post("/campaigns", response_model=Campaign)
async def create_campaign(input: CampaignCreate):
    campaign_dict = input.model_dump()
    campaign_obj = Campaign(**campaign_dict)
    
    doc = campaign_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await db.campaigns.insert_one(doc)
    return campaign_obj


@api_router.get("/campaigns", response_model=List[Campaign])
async def get_campaigns():
    campaigns = await db.campaigns.find({}, {"_id": 0}).to_list(1000)
    
    for campaign in campaigns:
        if isinstance(campaign.get('created_at'), str):
            campaign['created_at'] = datetime.fromisoformat(campaign['created_at'])
        if isinstance(campaign.get('updated_at'), str):
            campaign['updated_at'] = datetime.fromisoformat(campaign['updated_at'])
    
    return campaigns


@api_router.get("/campaigns/{campaign_id}", response_model=Campaign)
async def get_campaign(campaign_id: str):
    campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if isinstance(campaign.get('created_at'), str):
        campaign['created_at'] = datetime.fromisoformat(campaign['created_at'])
    if isinstance(campaign.get('updated_at'), str):
        campaign['updated_at'] = datetime.fromisoformat(campaign['updated_at'])
    
    return campaign


@api_router.put("/campaigns/{campaign_id}", response_model=Campaign)
async def update_campaign(campaign_id: str, input: CampaignUpdate):
    campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    update_data = {k: v for k, v in input.model_dump().items() if v is not None}
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    await db.campaigns.update_one(
        {"id": campaign_id},
        {"$set": update_data}
    )
    
    updated_campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    
    if isinstance(updated_campaign.get('created_at'), str):
        updated_campaign['created_at'] = datetime.fromisoformat(updated_campaign['created_at'])
    if isinstance(updated_campaign.get('updated_at'), str):
        updated_campaign['updated_at'] = datetime.fromisoformat(updated_campaign['updated_at'])
    
    return updated_campaign


@api_router.delete("/campaigns/{campaign_id}")
async def delete_campaign(campaign_id: str):
    result = await db.campaigns.delete_one({"id": campaign_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    return {"message": "Campaign deleted successfully"}


@api_router.get("/channels", response_model=List[Channel])
async def get_channels():
    custom_channels = await db.channels.find({}, {"_id": 0}).to_list(1000)
    
    for channel in custom_channels:
        if isinstance(channel.get('created_at'), str):
            channel['created_at'] = datetime.fromisoformat(channel['created_at'])
    
    default_channels = [
        {"id": "social", "name": "social", "label": "Social Media", "color": "#FF6B6B", "is_default": True, "created_at": datetime.now(timezone.utc)},
        {"id": "email", "name": "email", "label": "Email", "color": "#4ECDC4", "is_default": True, "created_at": datetime.now(timezone.utc)},
        {"id": "blog", "name": "blog", "label": "Blog", "color": "#FFE66D", "is_default": True, "created_at": datetime.now(timezone.utc)},
        {"id": "ads", "name": "ads", "label": "Ads", "color": "#1A535C", "is_default": True, "created_at": datetime.now(timezone.utc)}
    ]
    
    return default_channels + custom_channels


@api_router.post("/channels", response_model=Channel)
async def create_channel(input: ChannelCreate):
    channel_dict = input.model_dump()
    channel_obj = Channel(**channel_dict)
    
    doc = channel_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.channels.insert_one(doc)
    return channel_obj


@api_router.delete("/channels/{channel_id}")
async def delete_channel(channel_id: str):
    channel = await db.channels.find_one({"id": channel_id}, {"_id": 0})
    
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    if channel.get('is_default', False):
        raise HTTPException(status_code=400, detail="Cannot delete default channels")
    
    campaigns_count = await db.campaigns.count_documents({"channel": channel['name']})
    if campaigns_count > 0:
        raise HTTPException(status_code=400, detail=f"Cannot delete channel. {campaigns_count} campaigns are using it")
    
    await db.channels.delete_one({"id": channel_id})
    return {"message": "Channel deleted successfully"}


@api_router.get("/templates", response_model=List[Template])
async def get_templates():
    templates = [
        {
            "id": "1",
            "name": "Product Launch",
            "description": "Comprehensive campaign for new product launches",
            "channel": "social",
            "default_content": "Introducing our latest innovation!"
        },
        {
            "id": "2",
            "name": "Newsletter",
            "description": "Weekly or monthly newsletter template",
            "channel": "email",
            "default_content": "Your weekly update from our team"
        },
        {
            "id": "3",
            "name": "Blog Post",
            "description": "SEO-optimized blog content strategy",
            "channel": "blog",
            "default_content": "Expert insights on..."
        },
        {
            "id": "4",
            "name": "Ad Campaign",
            "description": "Paid advertising campaign template",
            "channel": "ads",
            "default_content": "Limited time offer!"
        }
    ]
    return templates


@api_router.get("/stats")
async def get_stats():
    total_campaigns = await db.campaigns.count_documents({})
    draft_count = await db.campaigns.count_documents({"status": "draft"})
    scheduled_count = await db.campaigns.count_documents({"status": "scheduled"})
    published_count = await db.campaigns.count_documents({"status": "published"})
    
    channels = await get_channels()
    channel_counts = {}
    for channel in channels:
        count = await db.campaigns.count_documents({"channel": channel['name']})
        channel_counts[channel['name']] = count
    
    return {
        "total": total_campaigns,
        "by_status": {
            "draft": draft_count,
            "scheduled": scheduled_count,
            "published": published_count
        },
        "by_channel": channel_counts
    }


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()