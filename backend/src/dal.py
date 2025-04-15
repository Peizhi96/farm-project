from bson import ObjectID 
# bson is a binary json library,ObjectID is a unique identifier for a document in MongoDB
from motor.motor_asyncio import AsyncIOMotorClient
# motor is a library that allows you to use MongoDB with asyncio
from pymongo import ReturnDocument
# pymongo is a library that allows you to use MongoDB with python
# ReturnDocument is a class that allows you to return the document after an update
from pydantic import BaseModel
# pydantic is a library that allows you to validate data
# BaseModel is a class that allows you to create a model of a database
from uuid import uuid4
# uuid is a library that allows you to create a unique identifier

class ListSummary(BaseModel):
    id:str
    name:str
    item_count:int 
    
    @staticmethod 
    def from_doc(doc)->"ListSummary":
        return ListSummary(
            id=str(doc["_id"]),
            name=doc["name"],
            item_count=doc["item_count"]
        )

class ToDoListItem(BaseModel):
    id:str
    label:str
    is_checked:bool
    
    @staticmethod
    def from_doc(item)->"ToDoListItem":
        return ToDoListItem(
            id=str(item["_id"]),
            label=item["label"],
            is_checked=item["is_checked"]
        )
    
class ToDoList(BaseModel):
    id:str
    name:str
    items:list[ToDoListItem]
    
    @staticmethod
    def from_doc(doc)->"ToDoList":
        return ToDoList(
            id=str(doc["_id"]),
            name=doc["name"],
            items=[ToDoListItem.from_doc(item) for item in doc["items"]]
        )

class ToDoDAL:
    def __init__(self, todo_collection:AsyncIOMotorCollection):
        self._todo_collection = todo_collection
    async def list_todo_lists(self, session=None):
        # access the information of all the todo lists
        async for doc in self.todo_collection.find(
            {},
            projection={
                "name": 1,
                "item_count": {"$size": "$items"},
            },
            sort={"name": 1},
            session=session
        ):
            yield ListSummary.from_doc(doc)
    
    async def create_todo_list(self, name:str, session=None) -> str:
        response = await self.todo_collection.insert_one(
            {"name": name,"items": []},
            session=session,
        )
        # instert_one is a built-in function of MongoDB
        # it inserts a single document into the collection
        # it returns a response object
        # the insert_id is the id of the document that was inserted
        return str(response.inserted_id)
    
    async def get_todo_list(self, id:str | ObjectID, session=None) -> ToDoList:
        doc = await self.todo_collection.find_one(
            {"_id": ObjectID(id)},
            session=session,
        )
        return ToDoList.from_doc(doc)

    async def delete_todo_list(self, id:str | ObjectID, session=None) -> bool:
        response = await self.todo_collection.delete_one(
            {"_id": ObjectID(id)},
            session=session,
        )
        return response.deleted_count == 1
    
    async def create_item(self, id: str | ObjectID, label:str, session=None) -> ToDoList | None:
        res = await self.todo_collection.find_one_and_update_one(
            {"_id": ObjectID(id)},
            # $push is a built-in function of MongoDB
            # it pushes a new item into the items array
            {
                "$push": {
                    "items": {
                        "id": uuid4().hex,
                        "label": label, 
                        "is_checked": False,
                    }
                }
            },
            session=session,
            return_document=ReturnDocument.AFTER,
            # ReturnDocument.AFTER is a built-in function of MongoDB
            # it returns the document after the update
        )
        if res:
            return ToDoList.from_doc(res)
    
    async def set_checked_state(self, doc_id:str | ObjectID, item_id:str, is_checked:bool, session=None) -> ToDoList | None:
        res = await self.todo_collection.find_one_and_update_one(
            # _id is a built-in field of MongoDB
            # it is the id of the document
            # items.id is a built-in field of MongoDB
            # it is the id of the item in the items array
            {"_id": ObjectID(doc_id), "items.id": item_id},
            # set is a built-in function of MongoDB
            # it sets the value of the item with the id item_id to is_checked
            {"$set": {"items.$.is_checked": is_checked}},
            session=session,
            return_document=ReturnDocument.AFTER,
        )
        if res:
            return ToDoList.from_doc(res)
    
    async def delete_item(self, doc_id:str | ObjectID, item_id:str, session=None) -> ToDoList | None:
        res = await self.todo_collection.find_one_and_update_one(
            {"_id": ObjectID(doc_id), "items.id": item_id},
            # $pull is a built-in function of MongoDB
            # it pulls an item from the items array
            {"$pull": {"items": {"id": item_id}}},
            session=session,
            return_document=ReturnDocument.AFTER,
        )
        if res:
            return ToDoList.from_doc(res)
    