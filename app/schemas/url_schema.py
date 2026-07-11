from pydantic import BaseModel, Field, ConfigDict, HttpUrl
from datetime import datetime

class UrlBase(BaseModel):
    long_url: HttpUrl

class UrlCreate(UrlBase):
    pass

class UrlResponse(UrlBase):
    id: int
    short_code: str
    click_count: int
    created_at: datetime
    last_clicked_at: datetime|None
    expiry_date: datetime

    model_config = ConfigDict(from_attributes=True)

class UrlAnalyticsResponse(BaseModel):
    id: int
    short_code: str
    click_count: int
    last_clicked_at: datetime|None

    model_config = ConfigDict(from_attributes=True)
    

