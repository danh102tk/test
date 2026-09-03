from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.routes import router
from app.core.config import settings

app=FastAPI(title='PDF Excel Extractor',version='3.0.0')
app.add_middleware(CORSMiddleware,allow_origins=['*'],allow_methods=['*'],allow_headers=['*'])
app.include_router(router)
app.mount('/',StaticFiles(directory=str(settings.base_dir/'app'/'static'),html=True),name='static')
