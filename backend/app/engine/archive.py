"""
檔案解壓縮與格式預檢模組 (Archive Extraction & Validation)

安全解壓 .zip 與 .7z 檔案，防範路徑遍歷漏洞 (Zip Slip)，並搜尋 Cadence XML 與 Netlist 檔案。
"""

import os
import zipfile
import logging
from typing import Dict, List, Optional
import py7zr

logger = logging.getLogger("designshield.archive")


def safe_extract_zip(zip_path: str, target_dir: str) -> List[str]:
    """
    安全解壓縮 ZIP 檔案，防範 Zip Slip 漏洞
    
    Args:
        zip_path: ZIP 檔案絕對路徑
        target_dir: 解壓縮目標目錄
        
    Returns:
        List[str]: 解壓縮出的檔案相對路徑清單
    """
    extracted_files = []
    abs_target_dir = os.path.abspath(target_dir)
    
    with zipfile.ZipFile(zip_path, 'r') as zf:
        for member in zf.infolist():
            member_path = os.path.abspath(os.path.join(abs_target_dir, member.filename))
            # 安全防護: 檢查解壓縮後的路徑是否在目標資料夾內
            if os.path.commonpath([abs_target_dir, member_path]) != abs_target_dir:
                raise ValueError(f"安全攔截: 偵測到路徑遍歷攻擊檔案 {member.filename}")
            
            zf.extract(member, abs_target_dir)
            if not member.is_dir():
                extracted_files.append(os.path.relpath(member_path, abs_target_dir))
                
    return extracted_files


def safe_extract_7z(archive_path: str, target_dir: str) -> List[str]:
    """
    安全解壓縮 7z 檔案
    
    Args:
        archive_path: 7z 檔案路徑
        target_dir: 解壓縮目標目錄
        
    Returns:
        List[str]: 解壓縮檔案清單
    """
    extracted_files = []
    abs_target_dir = os.path.abspath(target_dir)
    
    with py7zr.SevenZipFile(archive_path, mode='r') as archive:
        for fname, bio in archive.readall().items():
            member_path = os.path.abspath(os.path.join(abs_target_dir, fname))
            if os.path.commonpath([abs_target_dir, member_path]) != abs_target_dir:
                raise ValueError(f"安全攔截: 偵測到路徑遍歷攻擊檔案 {fname}")
            
            os.makedirs(os.path.dirname(member_path), exist_ok=True)
            with open(member_path, 'wb') as out_f:
                out_f.write(bio.read())
            extracted_files.append(os.path.relpath(member_path, abs_target_dir))
            
    return extracted_files


def extract_archive(file_path: str, target_dir: str) -> List[str]:
    """
    統一解壓入口，支援 .zip, .7z 與單一 .xml 檔案複製
    
    Args:
        file_path: 上傳之檔案路徑
        target_dir: 目標解壓縮暫存路徑
        
    Returns:
        List[str]: 解壓縮之檔案路徑清單
    """
    os.makedirs(target_dir, exist_ok=True)
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == '.zip':
        return safe_extract_zip(file_path, target_dir)
    elif ext == '.7z':
        return safe_extract_7z(file_path, target_dir)
    elif ext == '.xml':
        # 單一 XML 檔案直接放置於目標目錄
        dest_path = os.path.join(target_dir, os.path.basename(file_path))
        import shutil
        shutil.copy2(file_path, dest_path)
        return [os.path.basename(file_path)]
    else:
        raise ValueError(f"不支援的檔案格式: {ext}，請提供 .zip, .7z 或 .xml 檔案")


def find_schematic_files(extract_dir: str) -> Dict[str, Optional[str]]:
    """
    搜尋解壓縮目錄中的 Cadence OrCAD XML 與 Allegro Netlist
    
    Args:
        extract_dir: 搜尋目錄
        
    Returns:
        Dict: 包含 'xml_path' 與 'netlist_path' 的字典
    """
    result: Dict[str, Optional[str]] = {
        "xml_path": None,
        "netlist_path": None
    }
    
    for root, _, files in os.walk(extract_dir):
        for f in files:
            lower = f.lower()
            full_path = os.path.join(root, f)
            if lower.endswith(".xml") and not result["xml_path"]:
                result["xml_path"] = full_path
            elif lower == "pstxnet.dat" and not result["netlist_path"]:
                result["netlist_path"] = full_path
                
    return result
