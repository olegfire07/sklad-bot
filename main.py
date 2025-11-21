import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, Form, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import json
from pathlib import Path
import asyncio

from bot_service import create_bot_app
from database.db import db
from config.settings import settings
from services.document import create_document_from_data
from services.excel import update_excel
from services.archive import archive_document
from services.image import compress_image, generate_unique_filename

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global Bot Application
bot_app = create_bot_app()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up...")
    await db.connect()
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start_polling()
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    await bot_app.updater.stop()
    await bot_app.stop()
    await bot_app.shutdown()
    await db.close()

from fastapi.staticfiles import StaticFiles

# ... imports ...

app = FastAPI(lifespan=lifespan)

# Mount Web App
app.mount("/webapp", StaticFiles(directory="webapp", html=True), name="webapp")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/submit-report")
async def submit_report(
    department_number: str = Form(...),
    issue_number: str = Form(...),
    ticket_number: str = Form(...),
    date: str = Form(...),
    region: str = Form(...),
    items: str = Form(...), # JSON string
    photos: List[UploadFile] = File(...)
):
    try:
        items_data = json.loads(items)
        # items_data structure: [{'id': 0, 'description': '...', 'evaluation': '...'}]
        
        # Validate count
        if len(items_data) != len(photos):
            raise HTTPException(status_code=400, detail="Mismatch between items and photos count")

        # Process photos
        processed_photos = []
        settings.TEMP_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

        for i, photo in enumerate(photos):
            unique_name = generate_unique_filename()
            original_path = settings.TEMP_PHOTOS_DIR / f"orig_{unique_name}"
            compressed_path = settings.TEMP_PHOTOS_DIR / unique_name
            
            # Save upload
            with open(original_path, "wb") as buffer:
                content = await photo.read()
                buffer.write(content)
            
            # Compress
            await asyncio.to_thread(compress_image, original_path, compressed_path)
            
            # Cleanup original
            if original_path.exists():
                original_path.unlink()
                
            # Match with item data (assuming order is preserved)
            item_info = items_data[i]
            processed_photos.append({
                'photo': str(compressed_path),
                'description': item_info.get('description', ''),
                'evaluation': item_info.get('evaluation', '')
            })

        # Prepare data for document
        data = {
            'department_number': department_number,
            'issue_number': issue_number,
            'ticket_number': ticket_number,
            'date': date,
            'region': region,
            'photo_desc': processed_photos
        }

        # Generate Document
        # We need a dummy user_id for filename generation or pass it from frontend?
        # Let's use a system user_id or just 0
        user_id = 0 
        username = "WebUser"
        
        filename_path = await create_document_from_data(user_id, username, data)
        
        # Send to Admin Group
        if region in settings.REGION_TOPICS:
            topic_id = settings.REGION_TOPICS[region]
            caption = (f"Заключение от п. {department_number}, "
                       f"билет: {ticket_number}, от {date}")
            
            try:
                await bot_app.bot.send_document(
                    chat_id=settings.MAIN_GROUP_CHAT_ID,
                    document=open(filename_path, 'rb'),
                    caption=caption,
                    message_thread_id=topic_id
                )
            except Exception as e:
                logger.error(f"Failed to send to group: {e}")
                
            # Update Excel & Archive
            try:
                await update_excel(data)
                await archive_document(filename_path, data)
            except Exception as e:
                logger.error(f"Post-processing error: {e}")

        # Cleanup
        if filename_path.exists():
            filename_path.unlink()
            
        for item in processed_photos:
            path = Path(item['photo'])
            if path.exists():
                path.unlink()

        return {"status": "success", "message": "Report submitted successfully"}

    except Exception as e:
        logger.error(f"Error processing report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
