"""
Employee Lookup Service - Tra cứu tên nhân viên từ file Excel
"""

import pandas as pd
from pathlib import Path
from typing import Optional, Dict, Any
from app.core.config import settings

class EmployeeLookup:
    """Tra cứu thông tin nhân viên từ file Excel"""
    
    def __init__(self):
        self.df = None
        self.lookup_dict = {}
        self._load_data()
    
    def _load_data(self):
        """Load dữ liệu từ file Excel"""
        excel_path = settings.employee_lookup_file
        
        if not excel_path or not Path(excel_path).exists():
            print(f"⚠️ Employee lookup file not found: {excel_path}")
            return
        
        try:
            self.df = pd.read_excel(excel_path)
            
            # Chuẩn hóa cột
            # Giả định file có 2 cột: 'full_name' và 'staff_id'
            # Hoặc 'Họ và tên' và 'Mã nhân viên'
            col_mapping = {
                'full_name': ['full_name', 'Full Name', 'Họ và tên', 'Họ tên', 'Tên'],
                'staff_id': ['staff_id', 'Staff ID', 'Mã nhân viên', 'Mã NV', 'ID']
            }
            
            # Tìm cột phù hợp
            name_col = None
            id_col = None
            
            for col in self.df.columns:
                col_lower = col.lower().strip()
                for key, patterns in col_mapping.items():
                    if any(p.lower() in col_lower for p in patterns):
                        if key == 'full_name':
                            name_col = col
                        elif key == 'staff_id':
                            id_col = col
            
            if name_col is None or id_col is None:
                print(f"⚠️ Could not find required columns in Excel file")
                print(f"   Columns found: {list(self.df.columns)}")
                print(f"   Expected: 'full_name' and 'staff_id' or similar")
                return
            
            # Tạo lookup dictionary
            self.lookup_dict = dict(zip(
                self.df[id_col].astype(str).str.strip(),
                self.df[name_col].astype(str).str.strip()
            ))
            
            print(f"✅ Loaded {len(self.lookup_dict)} employee records from: {excel_path}")
            
        except Exception as e:
            print(f"❌ Error loading employee lookup file: {e}")
            self.df = None
            self.lookup_dict = {}
    
    def lookup(self, staff_id: str) -> Optional[str]:
        """Tra cứu tên nhân viên từ staff_id"""
        if not staff_id or not self.lookup_dict:
            return None
        
        # Chuẩn hóa staff_id
        staff_id = staff_id.strip().upper()
        
        # Tìm trực tiếp
        if staff_id in self.lookup_dict:
            return self.lookup_dict[staff_id]
        
        # Tìm với các biến thể (VD: VAE01749 -> VAE 01749)
        variants = [
            staff_id,
            staff_id.replace(' ', ''),
            staff_id.replace('-', ''),
            staff_id[:3] + ' ' + staff_id[3:],
            staff_id[:3] + '-' + staff_id[3:],
        ]
        
        for variant in variants:
            if variant in self.lookup_dict:
                return self.lookup_dict[variant]
        
        return None
    
    def get_all_employees(self) -> Dict[str, str]:
        """Lấy tất cả employees"""
        return self.lookup_dict
    
    def reload(self):
        """Tải lại dữ liệu"""
        self._load_data()