import fitz
import pytesseract
from PIL import Image
import io

# Đường dẫn Tesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

pdf_path = r"C:\Users\trant\OneDrive\Máy tính\scan_pdf_to_sheet\pdf_excel_extractor_completed\pdf_excel_extractor_completed\bckq.pdf"

doc = fitz.open(pdf_path)
for page_num, page in enumerate(doc, 1):
    print(f"\n📄 Page {page_num}:")
    
    # Thử text trực tiếp
    text = page.get_text()
    if text.strip():
        print(f"   ✅ Native text: {len(text)} chars")
        print(f"   Preview: {text[:200]}")
    else:
        print("   ⚠️ No native text, using OCR...")
        try:
            pix = page.get_pixmap(dpi=300)
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            
            ocr_text = pytesseract.image_to_string(img, lang='vie+eng')
            print(f"   ✅ OCR text: {len(ocr_text)} chars")
            print(f"   Preview: {ocr_text[:300]}")
            
            # Tìm VAE
            if "VAE" in ocr_text:
                print(f"   ✅ Found VAE in OCR text!")
                for line in ocr_text.split('\n'):
                    if "VAE" in line:
                        print(f"      {line.strip()}")
        except Exception as e:
            print(f"   ❌ OCR failed: {e}")

doc.close()