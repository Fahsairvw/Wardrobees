from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from db import init_db

# Import routers
from routes.user import router as user_router
from routes.wardrobe import router as wardrobe_router
from routes.items import router as items_router
from routes.detect import router as detect_router
from routes.search import router as search_router
from routes.feedback import router as feedback_router
from routes.debug import router as debug_router

# App setup
app = FastAPI(
    title='Wardrobees API',
    description='Digital wardrobe',
    version='1.0.0',
)


@app.on_event('startup')
async def startup_event():
    init_db()


app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)

storage_path = Path(__file__).parent / 'storage'
storage_path.mkdir(exist_ok=True)
app.mount('/storage', StaticFiles(directory=str(storage_path)), name='storage')


# Health check
@app.get('/')
def root():
    return {'status': 'API running'}


# Register all routers
app.include_router(user_router)
app.include_router(wardrobe_router)
app.include_router(items_router)
app.include_router(detect_router)
app.include_router(search_router)
app.include_router(feedback_router)
app.include_router(debug_router)
