#!/usr/bin/env python3
"""Chạy server: python run.py"""
import uvicorn

if __name__ == "__main__":
    print("=" * 60)
    print("  PDF → Excel Extractor (FORM 8014)")
    print("  Architecture: Local OCR → Parser → Validation → Excel")
    print("=" * 60)
    print("  Swagger UI : http://localhost:8000/docs")
    print("  Health     : http://localhost:8000/api/v1/health")
    print("=" * 60)
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
