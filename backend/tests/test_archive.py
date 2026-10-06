"""
壓縮檔安全解壓與掃描單元測試 (Archive Extraction Tests)

驗證 .zip 與 .7z 檔案解壓、防範 Zip Slip 漏洞以及尋找 Cadence XML 與 Netlist。
"""

import os
import io
import zipfile
import pytest
from backend.app.engine.archive import safe_extract_zip, safe_extract_7z, extract_archive, find_schematic_files
import py7zr


def test_safe_extract_zip_normal(tmp_path):
    """測試正常 ZIP 檔案安全解壓"""
    zip_path = tmp_path / "test.zip"
    target_dir = tmp_path / "extracted"

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("test.xml", "<Design></Design>")
        zf.writestr("sub/netlist.txt", "NET_NAME VCC")

    files = safe_extract_zip(str(zip_path), str(target_dir))
    assert "test.xml" in files
    assert os.path.exists(target_dir / "test.xml")
    assert os.path.exists(target_dir / "sub" / "netlist.txt")


def test_safe_extract_zip_slip_prevention(tmp_path):
    """測試 Zip Slip 路徑遍歷攻擊防護"""
    zip_path = tmp_path / "malicious.zip"
    target_dir = tmp_path / "safe_dir"
    target_dir.mkdir()

    # 構造帶有 ../ 之惡意路徑
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("../evil.txt", "Hacked!")

    with pytest.raises(ValueError, match="安全攔截: 偵測到路徑遍歷攻擊檔案"):
        safe_extract_zip(str(zip_path), str(target_dir))


def test_safe_extract_7z_normal(tmp_path):
    """測試正常 7z 檔案安全解壓"""
    archive_path = tmp_path / "test.7z"
    target_dir = tmp_path / "extracted_7z"
    source_file = tmp_path / "schematic.xml"
    source_file.write_text("<Design><Component/></Design>")

    with py7zr.SevenZipFile(str(archive_path), 'w') as archive:
        archive.write(str(source_file), arcname="schematic.xml")

    files = safe_extract_7z(str(archive_path), str(target_dir))
    assert "schematic.xml" in files
    assert os.path.exists(target_dir / "schematic.xml")


def test_find_schematic_files(tmp_path):
    """測試自動搜尋目錄中的 XML 與 Allegro pstxnet.dat"""
    schematic_dir = tmp_path / "sch_proj"
    schematic_dir.mkdir()
    (schematic_dir / "allegro").mkdir()

    xml_file = schematic_dir / "carrier.xml"
    xml_file.write_text("<Design></Design>")
    net_file = schematic_dir / "allegro" / "pstxnet.dat"
    net_file.write_text("FILE_TYPE = EXPANDEDNETLIST;")

    found = find_schematic_files(str(schematic_dir))
    assert found["xml_path"] == str(xml_file)
    assert found["netlist_path"] == str(net_file)


def test_extract_archive_single_xml(tmp_path):
    """測試直接上傳單一 .xml 檔案時的支援"""
    xml_file = tmp_path / "input.xml"
    xml_file.write_text("<Design></Design>")
    target_dir = tmp_path / "staging"

    res = extract_archive(str(xml_file), str(target_dir))
    assert "input.xml" in res
    assert os.path.exists(target_dir / "input.xml")


def test_extract_archive_unsupported_format(tmp_path):
    """測試不支援的檔案格式拋出例外"""
    dummy_file = tmp_path / "dummy.txt"
    dummy_file.write_text("hello")
    target_dir = tmp_path / "staging"

    with pytest.raises(ValueError, match="不支援的檔案格式"):
        extract_archive(str(dummy_file), str(target_dir))
