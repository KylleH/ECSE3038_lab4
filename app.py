from datetime import datetime
from typing import Annotated, List, Optional
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, BeforeValidator, TypeAdapter, Field
import motor.motor_asyncio
from dotenv import dotenv_values
from bson import ObjectId
from pymongo import ReturnDocument
from fastapi.middleware.cors import CORSMiddleware

config = dotenv_values(".env")

client = motor.motor_asyncio.AsyncIOMotorClient(config["MONGO_URL"],tls=True,tlsAllowInvalidCertificates=True)
db = client.tank_man

app = FastAPI()

origins = [ "https://ecse3038-lab3-tester.netlify.app" ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PyObjectId = Annotated[str, BeforeValidator(str)]

class Profile(BaseModel):
    id: Optional[PyObjectId] = Field(alias = "_id", default = None)
    username: Optional[str] = None
    role: Optional[str] = None
    color: Optional[str] = None
    last_updated:Optional[str]=None


@app.get("/profile", response_model=Profile)
async def get_profile():
    most_recent_profile = await db["profile"].find_one({}, sort=[('last_updated', -1)])
    if most_recent_profile:
        await db["profile"].delete_many({"_id": {"$ne": most_recent_profile["_id"]}})
        return Profile(**most_recent_profile)
    return {}

@app.post("/profile",status_code=201)
async def addprofile(profile:Profile):
    profile.last_updated= datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    new_profile= await db["profile"].insert_one(profile.model_dump())
    created_profile = await db["profile"].find_one({"_id": new_profile.inserted_id})
    return Profile(**created_profile)


    


class Tank(BaseModel):
    id: Optional[PyObjectId] = Field(alias = "_id", default = None)
    location: Optional[str] = None
    lat: Optional[float] = None
    long: Optional[float] = None

@app.get("/tank")
async def get_tanks():
    tanks = await db["tanks"].find().to_list(999)
    return TypeAdapter(List[Tank]).validate_python(tanks)

@app.get("/tank{id}")
async def get_tanks():
    tanks =await db["tanks"].find_one({"_id":ObjectId(id)})
    return TypeAdapter(List[Tank]).validate_python(tanks)

@app.post("/tank", status_code=201)
async def create_tank(tank: Tank):
    new_tank = await db["tanks"].insert_one(tank.model_dump())
    created_tank = await db["tanks"].find_one({"_id": new_tank.inserted_id})
    return Tank(**created_tank)

@app.patch("/tank/{id}")
async def update_tank(id: str, tank_update: Tank):
    updated_tank = await db["tanks"].update_one(
        {"_id": ObjectId(id)},
        {"$set": tank_update.model_dump(exclude_unset=True)},
    )

    if updated_tank.modified_count > 0:
        patched_tank = await db["tanks"].find_one(
            {"_id": ObjectId(id)}
        )
        
        return Tank(**patched_tank)
    
    raise HTTPException(status_code = 404, detail = "Tank of id: " + id + " not found.")

@app.delete("/tank/{id}",status_code=204)
async def delete_tank(id:str):
    delete_tank=await db["tanks"].delete_one({"_id":ObjectId(id)})
    if delete_tank.deleted_count<1:
        raise HTTPException(status_code=404,detail="Tank of id"+id+"not found")
    
    