from pydantic import BaseModel, Field, ConfigDict
class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(None, max_length=5000)
class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    description: str | None
    owner_id: str


class ProjectUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(None, max_length=5000)
