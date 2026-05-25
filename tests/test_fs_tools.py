import os
import shutil
from pathlib import Path
import pytest
import fs_tools

# We will use a dedicated subdirectory inside DATA_ROOT for our tests to avoid polluting production data.
TEST_DIR_NAME = "test_sandbox"
TEST_DIR = fs_tools.DATA_ROOT / TEST_DIR_NAME

@pytest.fixture(autouse=True)
def setup_and_teardown():
    """Fixture to ensure a clean test sandbox directory under DATA_ROOT for every test."""
    # Create the test sandbox directory
    TEST_DIR.mkdir(parents=True, exist_ok=True)
    yield
    # Cleanup the test sandbox directory after the test
    if TEST_DIR.exists():
        shutil.rmtree(TEST_DIR)

def test_read_file_success():
    # 1.6.1: read_file on temp .txt
    filepath = f"{TEST_DIR_NAME}/temp.txt"
    content = "Hello, this is a temporary test file."
    
    # Write the file first
    write_res = fs_tools.write_file(filepath, content)
    assert write_res["success"] is True
    
    # Read the file
    read_res = fs_tools.read_file(filepath)
    assert read_res["success"] is True
    assert read_res["content"] == content
    assert read_res["metadata"]["filename"] == "temp.txt"
    assert read_res["metadata"]["extension"] == ".txt"
    assert "size" in read_res["metadata"]
    assert "modified" in read_res["metadata"]

def test_read_file_missing():
    # 1.6.2: read_file missing file → success: false
    filepath = f"{TEST_DIR_NAME}/non_existent_file.txt"
    read_res = fs_tools.read_file(filepath)
    assert read_res["success"] is False
    assert "File not found" in read_res["error"]

def test_list_files_empty():
    # 1.6.3: list_files empty dir → files: []
    empty_dir = f"{TEST_DIR_NAME}/empty_sub"
    resolved_empty_dir = TEST_DIR / "empty_sub"
    resolved_empty_dir.mkdir(parents=True, exist_ok=True)
    
    list_res = fs_tools.list_files(empty_dir)
    assert list_res["success"] is True
    assert list_res["files"] == []

def test_list_files_with_extension_filter():
    # 1.6.4: list_files with extension filter
    sub_dir = f"{TEST_DIR_NAME}/filter_sub"
    resolved_sub_dir = TEST_DIR / "filter_sub"
    resolved_sub_dir.mkdir(parents=True, exist_ok=True)
    
    # Create files with different extensions
    fs_tools.write_file(f"{sub_dir}/file1.txt", "text content")
    fs_tools.write_file(f"{sub_dir}/file2.pdf", "pdf content")
    fs_tools.write_file(f"{sub_dir}/file3.docx", "docx content")
    fs_tools.write_file(f"{sub_dir}/another.txt", "more text content")
    
    # Filter by .txt
    list_txt = fs_tools.list_files(sub_dir, extension=".txt")
    assert list_txt["success"] is True
    txt_files = [f["name"] for f in list_txt["files"]]
    assert len(txt_files) == 2
    assert "file1.txt" in txt_files
    assert "another.txt" in txt_files
    
    # Filter by pdf (without leading dot)
    list_pdf = fs_tools.list_files(sub_dir, extension="pdf")
    assert list_pdf["success"] is True
    pdf_files = [f["name"] for f in list_pdf["files"]]
    assert len(pdf_files) == 1
    assert "file2.pdf" in pdf_files

def test_write_file_creates_parent_dirs():
    # 1.6.5: write_file creates file under temp dir inside data/
    filepath = f"{TEST_DIR_NAME}/deep/nested/folder/output.txt"
    content = "Nested file content"
    
    write_res = fs_tools.write_file(filepath, content)
    assert write_res["success"] is True
    assert write_res["message"] == "File created successfully"
    
    # Verify file exists and has correct content
    read_res = fs_tools.read_file(filepath)
    assert read_res["success"] is True
    assert read_res["content"] == content

def test_search_in_file_success():
    # 1.6.6: search_in_file finds keyword + snippet
    filepath = f"{TEST_DIR_NAME}/search_test.txt"
    # Create a long text to check the snippet context
    long_text = "This is some prefix text that goes on for a while. The special_keyword is located here. And some suffix text follows it."
    fs_tools.write_file(filepath, long_text)
    
    search_res = fs_tools.search_in_file(filepath, "special_keyword")
    assert search_res["success"] is True
    assert len(search_res["matches"]) == 1
    match = search_res["matches"][0]
    assert match["keyword"] == "special_keyword"
    assert "special_keyword" in match["context"]
    assert len(match["context"]) > len("special_keyword")

def test_search_in_file_no_match():
    # 1.6.7: search_in_file no match → empty matches
    filepath = f"{TEST_DIR_NAME}/search_test.txt"
    fs_tools.write_file(filepath, "Some text without the keyword.")
    
    search_res = fs_tools.search_in_file(filepath, "missing_keyword")
    assert search_res["success"] is True
    assert search_res["matches"] == []

def test_unsupported_extension():
    # 1.6.8: Unsupported extension → failure
    filepath = f"{TEST_DIR_NAME}/file.png"
    
    # Write the file first so it exists
    write_res = fs_tools.write_file(filepath, "fake png content")
    assert write_res["success"] is True
    
    # Trying to read an unsupported file type
    read_res = fs_tools.read_file(filepath)
    assert read_res["success"] is False
    assert "Unsupported file type" in read_res["error"]

def test_path_traversal_protection():
    # Verify sandbox security (ADR & implementation-plan §1.1.9)
    bad_filepath = "../outside_sandbox.txt"
    
    # Try to write outside DATA_ROOT
    write_res = fs_tools.write_file(bad_filepath, "leak")
    assert write_res["success"] is False
    assert "Access denied" in write_res["error"]
    
    # Try to read outside DATA_ROOT
    read_res = fs_tools.read_file(bad_filepath)
    assert read_res["success"] is False
    assert "Access denied" in read_res["error"]
