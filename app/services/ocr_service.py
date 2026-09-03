"""
OCR Service - Tự động tìm và sử dụng Tesseract
"""

import os
import subprocess
import pytesseract
from PIL import Image
import io
import fitz
from pathlib import Path
from typing import List, Dict, Any

class OCRService:
    """OCR Service với Tesseract"""
    
    def __init__(self):
        self.tesseract_path = self._find_tesseract()
        self.available = False
        
        if self.tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_path
            try:
                # Kiểm tra hoạt động
                pytesseract.get_tesseract_version()
                self.available = True
                print(f"✅ Tesseract OCR initialized at: {self.tesseract_path}")
            except Exception as e:
                print(f"⚠️ Tesseract found but not working: {e}")
        else:
            print("⚠️ Tesseract not found!")
    
    def _find_tesseract(self) -> str:
        """Tìm đường dẫn Tesseract trên Windows"""
        possible_paths = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        ]
        
        # Thêm đường dẫn từ biến môi trường PATH
        try:
            import shutil
            path_from_shutil = shutil.which('tesseract')
            if path_from_shutil:
                possible_paths.insert(0, path_from_shutil)
        except:
            pass
        
        # Thử từng đường dẫn
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # Thử dùng where command (Windows)
        try:
            result = subprocess.run(['where', 'tesseract'], capture_output=True, text=True)
            if result.returncode == 0:
                paths = result.stdout.strip().split('\n')
                if paths:
                    return paths[0]
        except:
            pass
        
        return None
    
    def ocr_pdf(self, pdf_path: Path) -> List[str]:
        """OCR toàn bộ PDF, trả về text từng trang"""
        texts = []
        
        # ⭐ SỬA: Mở file trong context manager để tự động đóng
        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            print(f"❌ Không thể mở file PDF: {e}")
            return texts
        
        try:
            for page_num, page in enumerate(doc, 1):
                print(f"📄 Page {page_num}: ", end="")
                
                # Thử lấy text trực tiếp
                text = page.get_text()
                if text.strip():
                    print(f"Native text ({len(text)} chars)")
                    texts.append(text)
                    continue
                
                # Dùng OCR
                if self.available:
                    try:
                        print("Using OCR...", end=" ")
                        pix = page.get_pixmap(dpi=300)
                        img_data = pix.tobytes("png")
                        img = Image.open(io.BytesIO(img_data))
                        
                        text = pytesseract.image_to_string(img, lang='vie+eng')
                        print(f"✅ {len(text)} chars")
                        texts.append(text)
                    except Exception as e:
                        print(f"❌ Failed: {e}")
                        texts.append("")
                else:
                    print("❌ OCR not available")
                    texts.append("")
        finally:
            # ⭐ QUAN TRỌNG: Đóng file sau khi xử lý xong
            doc.close()
        
        return texts
    
    def ocr_single_page(self, pdf_path: Path, page_num: int) -> str:
        """OCR một trang cụ thể"""
        try:
            doc = fitz.open(pdf_path)
            page = doc[page_num - 1]
            
            text = page.get_text()
            if not text.strip() and self.available:
                pix = page.get_pixmap(dpi=300)
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))
                text = pytesseract.image_to_string(img, lang='vie+eng')
            
            doc.close()
            return text
        except Exception as e:
            print(f"❌ OCR single page failed: {e}")
            return ""