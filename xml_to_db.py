#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
corp.xml 파일을 SQLite 데이터베이스로 변환하는 스크립트
"""

import xml.etree.ElementTree as ET
import sqlite3
import os
from typing import List, Dict

def parse_corp_xml(xml_file: str) -> List[Dict[str, str]]:
    """corp.xml 파일을 파싱하여 회사 정보를 추출합니다."""
    print(f"XML 파일 파싱 중: {xml_file}")
    
    tree = ET.parse(xml_file)
    root = tree.getroot()
    
    companies = []
    for corp in root.findall('list'):
        corp_data = {}
        for child in corp:
            corp_data[child.tag] = child.text.strip() if child.text else ""
        companies.append(corp_data)
    
    print(f"총 {len(companies)}개 회사 정보 추출 완료")
    return companies

def create_database(db_path: str) -> sqlite3.Connection:
    """SQLite 데이터베이스를 생성하고 테이블을 만듭니다."""
    print(f"데이터베이스 생성 중: {db_path}")
    
    # 기존 데이터베이스 파일이 있으면 삭제
    if os.path.exists(db_path):
        os.remove(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 회사 정보 테이블 생성
    cursor.execute('''
        CREATE TABLE companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            corp_code TEXT UNIQUE NOT NULL,
            corp_name TEXT NOT NULL,
            corp_eng_name TEXT,
            stock_code TEXT,
            modify_date TEXT,
            CONSTRAINT unique_corp_code UNIQUE (corp_code)
        )
    ''')
    
    # 검색 성능을 위한 인덱스 생성
    cursor.execute('CREATE INDEX idx_corp_name ON companies(corp_name)')
    cursor.execute('CREATE INDEX idx_corp_code ON companies(corp_code)')
    cursor.execute('CREATE INDEX idx_stock_code ON companies(stock_code)')
    
    conn.commit()
    print("데이터베이스 테이블 생성 완료")
    return conn

def insert_companies(conn: sqlite3.Connection, companies: List[Dict[str, str]]) -> None:
    """회사 정보를 데이터베이스에 삽입합니다."""
    print("데이터베이스에 회사 정보 삽입 중...")
    
    cursor = conn.cursor()
    
    # 배치 삽입을 위한 데이터 준비
    insert_data = []
    for company in companies:
        insert_data.append((
            company.get('corp_code', ''),
            company.get('corp_name', ''),
            company.get('corp_eng_name', ''),
            company.get('stock_code', ''),
            company.get('modify_date', '')
        ))
    
    # 배치 삽입 실행
    cursor.executemany('''
        INSERT OR IGNORE INTO companies 
        (corp_code, corp_name, corp_eng_name, stock_code, modify_date)
        VALUES (?, ?, ?, ?, ?)
    ''', insert_data)
    
    conn.commit()
    print(f"{cursor.rowcount}개 회사 정보 삽입 완료")

def create_full_text_search_table(conn: sqlite3.Connection) -> None:
    """전문 검색을 위한 FTS 테이블을 생성합니다."""
    print("전문 검색 테이블 생성 중...")
    
    cursor = conn.cursor()
    
    # FTS5 가상 테이블 생성
    cursor.execute('''
        CREATE VIRTUAL TABLE companies_fts USING fts5(
            corp_code,
            corp_name,
            corp_eng_name,
            stock_code,
            content='companies',
            content_rowid='id'
        )
    ''')
    
    # FTS 테이블에 데이터 삽입
    cursor.execute('''
        INSERT INTO companies_fts(corp_code, corp_name, corp_eng_name, stock_code)
        SELECT corp_code, corp_name, corp_eng_name, stock_code FROM companies
    ''')
    
    conn.commit()
    print("전문 검색 테이블 생성 완료")

def main():
    """메인 함수"""
    xml_file = "corp.xml"
    db_file = "companies.db"
    
    try:
        # XML 파일 파싱
        companies = parse_corp_xml(xml_file)
        
        # 데이터베이스 생성
        conn = create_database(db_file)
        
        # 회사 정보 삽입
        insert_companies(conn, companies)
        
        # 전문 검색 테이블 생성
        create_full_text_search_table(conn)
        
        # 통계 정보 출력
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM companies")
        total_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM companies WHERE stock_code != ''")
        stock_count = cursor.fetchone()[0]
        
        print(f"\n=== 데이터베이스 생성 완료 ===")
        print(f"총 회사 수: {total_count}")
        print(f"상장 회사 수: {stock_count}")
        print(f"데이터베이스 파일: {db_file}")
        
        conn.close()
        
    except FileNotFoundError:
        print(f"오류: {xml_file} 파일을 찾을 수 없습니다.")
    except Exception as e:
        print(f"오류 발생: {e}")

if __name__ == "__main__":
    main()
