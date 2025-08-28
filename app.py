#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
오픈다트 재무 데이터 시각화 분석 서비스 - Flask 백엔드
"""

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import sqlite3
import json
import requests
from typing import List, Dict, Optional
import re
from datetime import datetime
import time
import google.generativeai as genai

app = Flask(__name__)
CORS(app)  # CORS 설정으로 프론트엔드에서 API 호출 가능

# 데이터베이스 파일 경로
import os
DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'companies.db')

# 오픈다트 API 설정
OPENDART_API_KEY = '3fa6b39e36fb397c1d70152a51980ed89113b4dc'
OPENDART_BASE_URL = 'https://opendart.fss.or.kr/api'

# Gemini AI 설정
GEMINI_API_KEY = 'AIzaSyCG80k_9bw1xluCkn53oMd7WsB8VLDgK_o'
genai.configure(api_key=GEMINI_API_KEY)

def initialize_database():
    """데이터베이스 파일이 없으면 생성하는 함수"""
    if not os.path.exists(DATABASE_PATH):
        print(f"데이터베이스 파일이 없습니다: {DATABASE_PATH}")
        print("xml_to_db.py를 실행하여 데이터베이스를 생성합니다...")
        try:
            import subprocess
            result = subprocess.run(['python', 'xml_to_db.py'], 
                                  capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__)))
            if result.returncode == 0:
                print("데이터베이스 생성 완료!")
            else:
                print(f"데이터베이스 생성 실패: {result.stderr}")
        except Exception as e:
            print(f"데이터베이스 생성 중 오류: {e}")
    else:
        print(f"데이터베이스 파일 확인됨: {DATABASE_PATH}")

class CompanySearchService:
    """회사 검색 서비스 클래스"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        # 데이터베이스 파일 존재 확인
        if not os.path.exists(self.db_path):
            print(f"경고: 데이터베이스 파일을 찾을 수 없습니다: {self.db_path}")
            initialize_database()
    
    def get_connection(self) -> sqlite3.Connection:
        """데이터베이스 연결을 반환합니다."""
        try:
            if not os.path.exists(self.db_path):
                raise FileNotFoundError(f"데이터베이스 파일을 찾을 수 없습니다: {self.db_path}")
            
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # 딕셔너리 형태로 결과 반환
            
            # 테이블 존재 확인
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='companies'")
            if not cursor.fetchone():
                conn.close()
                raise Exception("companies 테이블이 존재하지 않습니다. 데이터베이스를 다시 생성해주세요.")
                
            return conn
        except Exception as e:
            print(f"데이터베이스 연결 오류: {e}")
            raise
    
    def search_companies(self, query: str, limit: int = 50) -> List[Dict]:
        """회사명으로 검색합니다."""
        if not query or len(query.strip()) < 1:
            return []
        
        query = query.strip()
        results = []
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                # 1. 정확한 회사명 매칭 (우선순위 높음)
                cursor.execute("""
                    SELECT corp_code, corp_name, corp_eng_name, stock_code, modify_date
                    FROM companies 
                    WHERE corp_name = ? 
                    ORDER BY corp_name
                    LIMIT ?
                """, (query, limit))
                
                exact_matches = [dict(row) for row in cursor.fetchall()]
                results.extend(exact_matches)
                
                # 2. 부분 매칭 (정확한 매칭이 없거나 추가 결과가 필요한 경우)
                if len(results) < limit:
                    remaining_limit = limit - len(results)
                    
                    cursor.execute("""
                        SELECT corp_code, corp_name, corp_eng_name, stock_code, modify_date
                        FROM companies 
                        WHERE corp_name LIKE ? AND corp_name != ?
                        ORDER BY 
                            CASE 
                                WHEN corp_name LIKE ? THEN 1  -- 시작하는 경우
                                ELSE 2  -- 포함하는 경우
                            END,
                            LENGTH(corp_name),  -- 짧은 이름 우선
                            corp_name
                        LIMIT ?
                    """, (f'%{query}%', query, f'{query}%', remaining_limit))
                    
                    partial_matches = [dict(row) for row in cursor.fetchall()]
                    results.extend(partial_matches)
                
                # 3. FTS 검색 (전문 검색)
                if len(results) < limit:
                    remaining_limit = limit - len(results)
                    
                    try:
                        cursor.execute("""
                            SELECT c.corp_code, c.corp_name, c.corp_eng_name, c.stock_code, c.modify_date
                            FROM companies_fts fts
                            JOIN companies c ON c.id = fts.rowid
                            WHERE companies_fts MATCH ?
                            AND c.corp_name NOT IN (
                                SELECT corp_name FROM (
                                    SELECT corp_name FROM companies WHERE corp_name = ? OR corp_name LIKE ?
                                )
                            )
                            ORDER BY rank
                            LIMIT ?
                        """, (query, query, f'%{query}%', remaining_limit))
                        
                        fts_matches = [dict(row) for row in cursor.fetchall()]
                        results.extend(fts_matches)
                    except sqlite3.OperationalError:
                        # FTS가 지원되지 않는 경우 무시
                        pass
                
            except Exception as e:
                print(f"검색 오류: {e}")
                return []
        
        return results[:limit]
    
    def get_company_by_code(self, corp_code: str) -> Optional[Dict]:
        """회사 코드로 특정 회사 정보를 가져옵니다."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT corp_code, corp_name, corp_eng_name, stock_code, modify_date
                FROM companies 
                WHERE corp_code = ?
            """, (corp_code,))
            
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_random_companies(self, limit: int = 10) -> List[Dict]:
        """랜덤한 회사 목록을 반환합니다."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT corp_code, corp_name, corp_eng_name, stock_code, modify_date
                FROM companies 
                WHERE stock_code != ''  -- 상장회사만
                ORDER BY RANDOM() 
                LIMIT ?
            """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]

class OpenDartService:
    """오픈다트 API 서비스 클래스"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = OPENDART_BASE_URL
    
    def get_financial_statements(self, corp_code: str, bsns_year: str, reprt_code: str = '11011') -> Dict:
        """단일회사 주요계정 조회"""
        url = f"{self.base_url}/fnlttSinglAcnt.json"
        
        params = {
            'crtfc_key': self.api_key,
            'corp_code': corp_code,
            'bsns_year': bsns_year,
            'reprt_code': reprt_code  # 11011: 사업보고서, 11012: 반기보고서, 11013: 1분기, 11014: 3분기
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status') == '000':  # 정상
                return {
                    'success': True,
                    'data': data.get('list', []),
                    'message': '재무 데이터를 성공적으로 가져왔습니다.'
                }
            else:
                error_messages = {
                    '010': '등록되지 않은 API 키입니다.',
                    '011': '사용할 수 없는 API 키입니다.',
                    '012': '접근할 수 없는 IP입니다.',
                    '013': '조회된 데이터가 없습니다.',
                    '020': '요청 제한을 초과했습니다.',
                    '100': '입력 값이 부적절합니다.',
                    '800': '시스템 점검 중입니다.',
                    '900': '정의되지 않은 오류가 발생했습니다.'
                }
                
                status = data.get('status', '900')
                message = error_messages.get(status, f"API 오류 (코드: {status})")
                
                return {
                    'success': False,
                    'data': [],
                    'message': message,
                    'error_code': status
                }
                
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'data': [],
                'message': f'API 요청 실패: {str(e)}'
            }
    
    def get_multi_year_data(self, corp_code: str, years: List[str], reprt_code: str = '11011') -> Dict:
        """여러 연도의 재무 데이터 조회"""
        results = {}
        
        for year in years:
            # API 요청 간격 조절 (초당 요청 제한 방지)
            time.sleep(0.1)
            
            result = self.get_financial_statements(corp_code, year, reprt_code)
            if result['success']:
                results[year] = result['data']
            else:
                results[year] = []
        
        return {
            'success': True,
            'data': results,
            'message': f'{len(years)}개 연도의 데이터를 조회했습니다.'
        }
    
    def parse_financial_data(self, raw_data: List[Dict]) -> Dict:
        """재무 데이터를 시각화용으로 파싱"""
        parsed = {
            'balance_sheet': {},  # 재무상태표
            'income_statement': {},  # 손익계산서
            'metadata': {}
        }
        
        for item in raw_data:
            fs_div = item.get('fs_div', '')  # OFS: 개별, CFS: 연결
            sj_div = item.get('sj_div', '')  # BS: 재무상태표, IS: 손익계산서
            account_nm = item.get('account_nm', '')
            thstrm_amount = item.get('thstrm_amount', '0')
            frmtrm_amount = item.get('frmtrm_amount', '0')
            bfefrmtrm_amount = item.get('bfefrmtrm_amount', '0')
            
            # 연결재무제표 우선
            if fs_div == 'CFS':
                if sj_div == 'BS':
                    parsed['balance_sheet'][account_nm] = {
                        'current': self._parse_amount(thstrm_amount),
                        'previous': self._parse_amount(frmtrm_amount),
                        'before_previous': self._parse_amount(bfefrmtrm_amount)
                    }
                elif sj_div == 'IS':
                    parsed['income_statement'][account_nm] = {
                        'current': self._parse_amount(thstrm_amount),
                        'previous': self._parse_amount(frmtrm_amount),
                        'before_previous': self._parse_amount(bfefrmtrm_amount)
                    }
            
            # 메타데이터 저장 (첫 번째 항목 기준)
            if not parsed['metadata']:
                parsed['metadata'] = {
                    'corp_code': item.get('corp_code', ''),
                    'stock_code': item.get('stock_code', ''),
                    'bsns_year': item.get('bsns_year', ''),
                    'reprt_code': item.get('reprt_code', ''),
                    'thstrm_nm': item.get('thstrm_nm', ''),
                    'frmtrm_nm': item.get('frmtrm_nm', ''),
                    'bfefrmtrm_nm': item.get('bfefrmtrm_nm', '')
                }
        
        return parsed
    
    def _parse_amount(self, amount_str: str) -> float:
        """금액 문자열을 숫자로 변환 (단위: 억원)"""
        try:
            if not amount_str or amount_str == '-':
                return 0
            
            # 콤마 제거 후 숫자로 변환
            amount = float(amount_str.replace(',', ''))
            
            # 원 단위를 억원 단위로 변환
            return round(amount / 100000000, 2)
        except (ValueError, TypeError):
            return 0

class GeminiAnalysisService:
    """Gemini AI 재무 분석 서비스 클래스"""
    
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-pro')
    
    def analyze_financial_data(self, company_name: str, financial_data: Dict, years: List[str]) -> Dict:
        """재무 데이터를 AI로 분석하여 쉬운 설명 제공"""
        try:
            # 재무 데이터 요약 생성
            financial_summary = self._create_financial_summary(financial_data, years)
            
            # AI 프롬프트 생성
            prompt = self._create_analysis_prompt(company_name, financial_summary, years)
            
            # Gemini AI 호출
            response = self.model.generate_content(prompt)
            
            return {
                'success': True,
                'analysis': response.text,
                'summary': financial_summary
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'analysis': '죄송합니다. AI 분석 중 오류가 발생했습니다.'
            }
    
    def _create_financial_summary(self, data: Dict, years: List[str]) -> Dict:
        """재무 데이터를 요약 형태로 변환"""
        summary = {
            'revenue_trend': [],
            'profit_trend': [],
            'asset_trend': [],
            'debt_ratio_trend': [],
            'key_metrics': {}
        }
        
        for year in years:
            year_data = data.get(year)
            if year_data:
                balance_sheet = year_data.get('balance_sheet', {})
                income_statement = year_data.get('income_statement', {})
                
                # 주요 지표 추출
                revenue = income_statement.get('매출액', {}).get('current', 0)
                operating_profit = income_statement.get('영업이익', {}).get('current', 0)
                net_profit = income_statement.get('당기순이익', {}).get('current', 0)
                total_assets = balance_sheet.get('자산총계', {}).get('current', 0)
                total_debt = balance_sheet.get('부채총계', {}).get('current', 0)
                total_equity = balance_sheet.get('자본총계', {}).get('current', 0)
                
                summary['revenue_trend'].append({
                    'year': year,
                    'value': revenue
                })
                
                summary['profit_trend'].append({
                    'year': year,
                    'operating_profit': operating_profit,
                    'net_profit': net_profit
                })
                
                summary['asset_trend'].append({
                    'year': year,
                    'assets': total_assets,
                    'debt': total_debt,
                    'equity': total_equity
                })
                
                # 부채비율 계산
                debt_ratio = (total_debt / total_assets * 100) if total_assets > 0 else 0
                summary['debt_ratio_trend'].append({
                    'year': year,
                    'debt_ratio': debt_ratio
                })
        
        # 최신년도 주요 지표
        if summary['revenue_trend']:
            latest = summary['revenue_trend'][-1]
            latest_profit = summary['profit_trend'][-1]
            latest_asset = summary['asset_trend'][-1]
            latest_debt_ratio = summary['debt_ratio_trend'][-1]
            
            summary['key_metrics'] = {
                'latest_year': latest['year'],
                'revenue': latest['value'],
                'operating_profit': latest_profit['operating_profit'],
                'net_profit': latest_profit['net_profit'],
                'total_assets': latest_asset['assets'],
                'debt_ratio': latest_debt_ratio['debt_ratio'],
                'operating_margin': (latest_profit['operating_profit'] / latest['value'] * 100) if latest['value'] > 0 else 0,
                'net_margin': (latest_profit['net_profit'] / latest['value'] * 100) if latest['value'] > 0 else 0
            }
        
        return summary
    
    def _create_analysis_prompt(self, company_name: str, summary: Dict, years: List[str]) -> str:
        """AI 분석을 위한 프롬프트 생성"""
        
        # 트렌드 분석을 위한 데이터 정리
        revenue_data = [(item['year'], item['value']) for item in summary['revenue_trend']]
        profit_data = [(item['year'], item['operating_profit'], item['net_profit']) for item in summary['profit_trend']]
        debt_ratio_data = [(item['year'], item['debt_ratio']) for item in summary['debt_ratio_trend']]
        
        key_metrics = summary.get('key_metrics', {})
        
        prompt = f"""
다음은 {company_name}의 {years[0]}년부터 {years[-1]}년까지의 재무 데이터입니다.
일반인도 쉽게 이해할 수 있도록 친근하고 명확한 언어로 분석해주세요.

📊 주요 재무 지표 ({key_metrics.get('latest_year', years[-1])}년 기준):
- 매출액: {key_metrics.get('revenue', 0):,.0f}억원
- 영업이익: {key_metrics.get('operating_profit', 0):,.0f}억원
- 당기순이익: {key_metrics.get('net_profit', 0):,.0f}억원
- 자산총계: {key_metrics.get('total_assets', 0):,.0f}억원
- 부채비율: {key_metrics.get('debt_ratio', 0):.1f}%
- 영업이익률: {key_metrics.get('operating_margin', 0):.1f}%
- 순이익률: {key_metrics.get('net_margin', 0):.1f}%

📈 연도별 매출액 추이:
{revenue_data}

💰 연도별 수익성 추이 (영업이익, 순이익):
{profit_data}

🏦 연도별 부채비율 추이:
{debt_ratio_data}

다음 관점에서 분석해주세요:
1. **매출 성장성**: 매출액이 증가하고 있는지, 성장 속도는 어떤지
2. **수익성 분석**: 영업이익률과 순이익률이 양호한지, 개선되고 있는지
3. **재무 안정성**: 부채비율이 적정한 수준인지, 변화 추이는 어떤지
4. **종합 평가**: 이 회사의 전반적인 재무 건전성과 투자 매력도
5. **주의사항**: 투자 시 고려해야 할 리스크 요인

답변은 다음 형식으로 작성해주세요:
- 이모지를 적극 활용하여 시각적 효과 높이기
- 전문 용어 사용 시 괄호 안에 쉬운 설명 추가
- 구체적인 수치와 함께 설명
- 긍정적인 부분과 주의할 점을 균형있게 제시
- 일반 투자자도 이해할 수 있는 쉬운 언어 사용

한글로 답변해주세요.
"""
        
        return prompt
    
    def analyze_company_comparison(self, companies_data: List[Dict]) -> Dict:
        """여러 회사 비교 분석"""
        try:
            prompt = self._create_comparison_prompt(companies_data)
            response = self.model.generate_content(prompt)
            
            return {
                'success': True,
                'analysis': response.text
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'analysis': '회사 비교 분석 중 오류가 발생했습니다.'
            }
    
    def _create_comparison_prompt(self, companies_data: List[Dict]) -> str:
        """회사 비교 분석을 위한 프롬프트 생성"""
        
        company_info = []
        for data in companies_data:
            company_name = data.get('company_name', '알 수 없음')
            metrics = data.get('key_metrics', {})
            
            company_info.append(f"""
{company_name}:
- 매출액: {metrics.get('revenue', 0):,.0f}억원
- 영업이익률: {metrics.get('operating_margin', 0):.1f}%
- 순이익률: {metrics.get('net_margin', 0):.1f}%
- 부채비율: {metrics.get('debt_ratio', 0):.1f}%
""")
        
        prompt = f"""
다음 회사들의 재무 지표를 비교 분석해주세요:

{chr(10).join(company_info)}

비교 분석 관점:
1. **수익성**: 영업이익률과 순이익률 비교
2. **성장성**: 매출 규모와 성장 잠재력
3. **안정성**: 부채비율과 재무 안정성
4. **투자 매력도**: 각 회사의 강점과 약점
5. **투자 추천**: 어떤 회사가 더 매력적인지 (투자 조언이 아닌 단순 비교)

일반인도 이해하기 쉽게 설명해주세요.
"""
        
        return prompt

# 전역 서비스 인스턴스
search_service = CompanySearchService(DATABASE_PATH)
dart_service = OpenDartService(OPENDART_API_KEY)
ai_service = GeminiAnalysisService()

@app.route('/')
def index():
    """메인 페이지"""
    return render_template('index.html')

@app.route('/health')
def health_check():
    """헬스 체크 엔드포인트"""
    try:
        # 데이터베이스 연결 테스트
        with search_service.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM companies LIMIT 1")
            count = cursor.fetchone()[0]
            
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'total_companies': count,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/search')
def search_companies():
    """회사 검색 API"""
    query = request.args.get('q', '').strip()
    limit = min(int(request.args.get('limit', 50)), 100)  # 최대 100개 제한
    
    if not query:
        return jsonify({
            'success': False,
            'message': '검색어를 입력해주세요.',
            'data': []
        })
    
    try:
        results = search_service.search_companies(query, limit)
        
        return jsonify({
            'success': True,
            'message': f'{len(results)}개의 검색 결과를 찾았습니다.',
            'data': results,
            'query': query,
            'count': len(results)
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'검색 중 오류가 발생했습니다: {str(e)}',
            'data': []
        }), 500

@app.route('/api/company/<corp_code>')
def get_company(corp_code):
    """특정 회사 정보 조회 API"""
    try:
        company = search_service.get_company_by_code(corp_code)
        
        if company:
            return jsonify({
                'success': True,
                'data': company
            })
        else:
            return jsonify({
                'success': False,
                'message': '해당 회사를 찾을 수 없습니다.'
            }), 404
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'조회 중 오류가 발생했습니다: {str(e)}'
        }), 500

@app.route('/api/random')
def get_random_companies():
    """랜덤 회사 목록 API"""
    limit = min(int(request.args.get('limit', 10)), 20)
    
    try:
        companies = search_service.get_random_companies(limit)
        
        return jsonify({
            'success': True,
            'data': companies,
            'count': len(companies)
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'조회 중 오류가 발생했습니다: {str(e)}',
            'data': []
        }), 500

@app.route('/api/stats')
def get_stats():
    """데이터베이스 통계 정보 API"""
    try:
        with search_service.get_connection() as conn:
            cursor = conn.cursor()
            
            # 전체 회사 수
            cursor.execute("SELECT COUNT(*) FROM companies")
            total_companies = cursor.fetchone()[0]
            
            # 상장 회사 수
            cursor.execute("SELECT COUNT(*) FROM companies WHERE stock_code != ''")
            listed_companies = cursor.fetchone()[0]
            
            # 최근 수정일
            cursor.execute("SELECT MAX(modify_date) FROM companies")
            last_modified = cursor.fetchone()[0]
            
            return jsonify({
                'success': True,
                'data': {
                    'total_companies': total_companies,
                    'listed_companies': listed_companies,
                    'unlisted_companies': total_companies - listed_companies,
                    'last_modified': last_modified
                }
            })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'통계 조회 중 오류가 발생했습니다: {str(e)}'
        }), 500

@app.route('/api/financial/<corp_code>')
def get_financial_data(corp_code):
    """단일 회사 재무 데이터 조회 API"""
    try:
        # 요청 파라미터
        year = request.args.get('year', '2022')  # 기본값: 2022년
        reprt_code = request.args.get('reprt_code', '11011')  # 기본값: 사업보고서
        
        # 회사 정보 확인
        company = search_service.get_company_by_code(corp_code)
        if not company:
            return jsonify({
                'success': False,
                'message': '해당 회사를 찾을 수 없습니다.'
            }), 404
        
        # 오픈다트 API 호출
        result = dart_service.get_financial_statements(corp_code, year, reprt_code)
        
        if result['success']:
            # 데이터 파싱
            parsed_data = dart_service.parse_financial_data(result['data'])
            
            return jsonify({
                'success': True,
                'data': {
                    'company': company,
                    'financial_data': parsed_data,
                    'raw_data': result['data']
                },
                'message': f"{company['corp_name']}의 {year}년 재무 데이터를 조회했습니다."
            })
        else:
            return jsonify({
                'success': False,
                'message': result['message'],
                'error_code': result.get('error_code')
            }), 400
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'재무 데이터 조회 중 오류가 발생했습니다: {str(e)}'
        }), 500

@app.route('/api/financial/multi/<corp_code>')
def get_multi_year_financial_data(corp_code):
    """다년도 회사 재무 데이터 조회 API"""
    try:
        # 요청 파라미터
        years_param = request.args.get('years', '2020,2021,2022')
        years = [year.strip() for year in years_param.split(',')]
        reprt_code = request.args.get('reprt_code', '11011')
        
        # 최대 5년으로 제한
        if len(years) > 5:
            return jsonify({
                'success': False,
                'message': '최대 5년까지만 조회 가능합니다.'
            }), 400
        
        # 회사 정보 확인
        company = search_service.get_company_by_code(corp_code)
        if not company:
            return jsonify({
                'success': False,
                'message': '해당 회사를 찾을 수 없습니다.'
            }), 404
        
        # 다년도 데이터 조회
        result = dart_service.get_multi_year_data(corp_code, years, reprt_code)
        
        # 각 연도별 데이터 파싱
        parsed_years = {}
        for year, year_data in result['data'].items():
            if year_data:
                parsed_years[year] = dart_service.parse_financial_data(year_data)
            else:
                parsed_years[year] = None
        
        return jsonify({
            'success': True,
            'data': {
                'company': company,
                'years_data': parsed_years,
                'years': years
            },
            'message': f"{company['corp_name']}의 {len(years)}개년 재무 데이터를 조회했습니다."
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'다년도 재무 데이터 조회 중 오류가 발생했습니다: {str(e)}'
        }), 500

@app.route('/api/financial/chart/<corp_code>')
def get_chart_data(corp_code):
    """차트용 재무 데이터 조회 API"""
    try:
        # 요청 파라미터
        years_param = request.args.get('years', '2018,2019,2020,2021,2022')
        years = [year.strip() for year in years_param.split(',')]
        chart_type = request.args.get('type', 'revenue')  # revenue, profit, asset, debt
        
        # 회사 정보 확인
        company = search_service.get_company_by_code(corp_code)
        if not company:
            return jsonify({
                'success': False,
                'message': '해당 회사를 찾을 수 없습니다.'
            }), 404
        
        # 다년도 데이터 조회
        result = dart_service.get_multi_year_data(corp_code, years)
        
        # 차트 데이터 생성
        chart_data = {
            'labels': years,
            'datasets': []
        }
        
        # 차트 타입별 데이터 처리
        if chart_type == 'revenue':
            revenue_data = []
            operating_profit_data = []
            net_profit_data = []
            
            for year in years:
                year_data = result['data'].get(year, [])
                parsed = dart_service.parse_financial_data(year_data) if year_data else {}
                
                # 매출액, 영업이익, 당기순이익 추출
                income_stmt = parsed.get('income_statement', {})
                revenue_data.append(income_stmt.get('매출액', {}).get('current', 0))
                operating_profit_data.append(income_stmt.get('영업이익', {}).get('current', 0))
                net_profit_data.append(income_stmt.get('당기순이익', {}).get('current', 0))
            
            chart_data['datasets'] = [
                {
                    'label': '매출액',
                    'data': revenue_data,
                    'backgroundColor': 'rgba(54, 162, 235, 0.8)',
                    'borderColor': 'rgba(54, 162, 235, 1)'
                },
                {
                    'label': '영업이익',
                    'data': operating_profit_data,
                    'backgroundColor': 'rgba(255, 99, 132, 0.8)',
                    'borderColor': 'rgba(255, 99, 132, 1)'
                },
                {
                    'label': '당기순이익',
                    'data': net_profit_data,
                    'backgroundColor': 'rgba(75, 192, 192, 0.8)',
                    'borderColor': 'rgba(75, 192, 192, 1)'
                }
            ]
        
        elif chart_type == 'asset':
            asset_data = []
            debt_data = []
            equity_data = []
            
            for year in years:
                year_data = result['data'].get(year, [])
                parsed = dart_service.parse_financial_data(year_data) if year_data else {}
                
                # 자산, 부채, 자본 추출
                balance_sheet = parsed.get('balance_sheet', {})
                asset_data.append(balance_sheet.get('자산총계', {}).get('current', 0))
                debt_data.append(balance_sheet.get('부채총계', {}).get('current', 0))
                equity_data.append(balance_sheet.get('자본총계', {}).get('current', 0))
            
            chart_data['datasets'] = [
                {
                    'label': '자산총계',
                    'data': asset_data,
                    'backgroundColor': 'rgba(153, 102, 255, 0.8)',
                    'borderColor': 'rgba(153, 102, 255, 1)'
                },
                {
                    'label': '부채총계',
                    'data': debt_data,
                    'backgroundColor': 'rgba(255, 159, 64, 0.8)',
                    'borderColor': 'rgba(255, 159, 64, 1)'
                },
                {
                    'label': '자본총계',
                    'data': equity_data,
                    'backgroundColor': 'rgba(54, 162, 235, 0.8)',
                    'borderColor': 'rgba(54, 162, 235, 1)'
                }
            ]
        
        elif chart_type == 'balance':
            # 자산 = 부채 + 자본 균형 차트
            asset_data = []
            debt_equity_data = []  # 부채 + 자본 합계
            debt_data = []
            equity_data = []
            
            for year in years:
                year_data = result['data'].get(year, [])
                parsed = dart_service.parse_financial_data(year_data) if year_data else {}
                
                # 자산, 부채, 자본 추출
                balance_sheet = parsed.get('balance_sheet', {})
                asset = balance_sheet.get('자산총계', {}).get('current', 0)
                debt = balance_sheet.get('부채총계', {}).get('current', 0)
                equity = balance_sheet.get('자본총계', {}).get('current', 0)
                
                asset_data.append(asset)
                debt_data.append(debt)
                equity_data.append(equity)
                debt_equity_data.append(debt + equity)  # 부채 + 자본
            
            chart_data['datasets'] = [
                {
                    'label': '자산총계 (A)',
                    'data': asset_data,
                    'backgroundColor': 'rgba(75, 192, 192, 0.6)',
                    'borderColor': 'rgba(75, 192, 192, 1)',
                    'borderWidth': 2,
                    'type': 'line'
                },
                {
                    'label': '부채+자본 (B+C)',
                    'data': debt_equity_data,
                    'backgroundColor': 'rgba(255, 99, 132, 0.6)',
                    'borderColor': 'rgba(255, 99, 132, 1)',
                    'borderWidth': 2,
                    'type': 'line',
                    'borderDash': [5, 5]
                },
                {
                    'label': '부채총계 (B)',
                    'data': debt_data,
                    'backgroundColor': 'rgba(255, 159, 64, 0.7)',
                    'borderColor': 'rgba(255, 159, 64, 1)',
                    'stack': 'Stack 0'
                },
                {
                    'label': '자본총계 (C)',
                    'data': equity_data,
                    'backgroundColor': 'rgba(54, 162, 235, 0.7)',
                    'borderColor': 'rgba(54, 162, 235, 1)',
                    'stack': 'Stack 0'
                }
            ]
        
        return jsonify({
            'success': True,
            'data': {
                'company': company,
                'chart_data': chart_data,
                'chart_type': chart_type,
                'years': years
            },
            'message': f"{company['corp_name']}의 {chart_type} 차트 데이터를 생성했습니다."
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'차트 데이터 생성 중 오류가 발생했습니다: {str(e)}'
        }), 500

@app.route('/api/ai-analysis/<corp_code>')
def get_ai_analysis(corp_code):
    """AI 재무 분석 API"""
    try:
        # 요청 파라미터
        years_param = request.args.get('years', '2020,2021,2022')
        years = [year.strip() for year in years_param.split(',')]
        
        # 회사 정보 확인
        company = search_service.get_company_by_code(corp_code)
        if not company:
            return jsonify({
                'success': False,
                'message': '해당 회사를 찾을 수 없습니다.'
            }), 404
        
        # 다년도 재무 데이터 조회
        result = dart_service.get_multi_year_data(corp_code, years)
        
        if not result['success']:
            return jsonify({
                'success': False,
                'message': '재무 데이터를 가져올 수 없습니다.'
            }), 400
        
        # 각 연도별 데이터 파싱
        parsed_years = {}
        for year, year_data in result['data'].items():
            if year_data:
                parsed_years[year] = dart_service.parse_financial_data(year_data)
        
        # AI 분석 수행
        ai_result = ai_service.analyze_financial_data(
            company['corp_name'], 
            parsed_years, 
            years
        )
        
        if ai_result['success']:
            return jsonify({
                'success': True,
                'data': {
                    'company': company,
                    'analysis': ai_result['analysis'],
                    'summary': ai_result.get('summary', {}),
                    'years': years
                },
                'message': f"{company['corp_name']}의 AI 재무 분석이 완료되었습니다."
            })
        else:
            return jsonify({
                'success': False,
                'message': ai_result.get('analysis', 'AI 분석 중 오류가 발생했습니다.'),
                'error': ai_result.get('error')
            }), 500
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'AI 분석 중 오류가 발생했습니다: {str(e)}'
        }), 500

@app.route('/api/ai-insights/<corp_code>')
def get_ai_insights(corp_code):
    """간단한 AI 인사이트 API (빠른 분석)"""
    try:
        # 최근 1년 데이터만 조회 (빠른 분석)
        year = request.args.get('year', '2022')
        
        company = search_service.get_company_by_code(corp_code)
        if not company:
            return jsonify({
                'success': False,
                'message': '해당 회사를 찾을 수 없습니다.'
            }), 404
        
        # 단일 연도 재무 데이터 조회
        result = dart_service.get_financial_statements(corp_code, year)
        
        if not result['success']:
            return jsonify({
                'success': False,
                'message': '재무 데이터를 가져올 수 없습니다.'
            }), 400
        
        # 데이터 파싱
        parsed_data = dart_service.parse_financial_data(result['data'])
        
        # 간단한 인사이트 생성
        insights = _generate_quick_insights(company['corp_name'], parsed_data, year)
        
        return jsonify({
            'success': True,
            'data': {
                'company': company,
                'insights': insights,
                'year': year
            },
            'message': f"{company['corp_name']}의 {year}년 재무 인사이트입니다."
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'인사이트 생성 중 오류가 발생했습니다: {str(e)}'
        }), 500

def _generate_quick_insights(company_name: str, data: Dict, year: str) -> Dict:
    """빠른 재무 인사이트 생성"""
    balance_sheet = data.get('balance_sheet', {})
    income_statement = data.get('income_statement', {})
    
    # 주요 지표 계산
    revenue = income_statement.get('매출액', {}).get('current', 0)
    operating_profit = income_statement.get('영업이익', {}).get('current', 0)
    net_profit = income_statement.get('당기순이익', {}).get('current', 0)
    total_assets = balance_sheet.get('자산총계', {}).get('current', 0)
    total_debt = balance_sheet.get('부채총계', {}).get('current', 0)
    
    # 비율 계산
    operating_margin = (operating_profit / revenue * 100) if revenue > 0 else 0
    net_margin = (net_profit / revenue * 100) if revenue > 0 else 0
    debt_ratio = (total_debt / total_assets * 100) if total_assets > 0 else 0
    
    # 인사이트 생성
    insights = {
        'revenue_scale': _get_revenue_insight(revenue),
        'profitability': _get_profitability_insight(operating_margin, net_margin),
        'financial_stability': _get_stability_insight(debt_ratio),
        'overall_grade': _get_overall_grade(operating_margin, net_margin, debt_ratio),
        'key_numbers': {
            'revenue': revenue,
            'operating_margin': operating_margin,
            'net_margin': net_margin,
            'debt_ratio': debt_ratio
        }
    }
    
    return insights

def _get_revenue_insight(revenue: float) -> str:
    """매출 규모 인사이트"""
    if revenue >= 100000:  # 10조원 이상
        return "🏢 대기업 규모의 매출을 기록하고 있어요"
    elif revenue >= 10000:  # 1조원 이상
        return "🏭 중견기업 수준의 안정적인 매출 규모예요"
    elif revenue >= 1000:  # 1000억원 이상
        return "🏪 중소기업 중에서는 큰 규모의 매출이에요"
    else:
        return "🏬 소규모 기업의 매출 수준이에요"

def _get_profitability_insight(operating_margin: float, net_margin: float) -> str:
    """수익성 인사이트"""
    if operating_margin >= 20:
        return "💰 매우 높은 수익성을 보이는 우수한 기업이에요"
    elif operating_margin >= 10:
        return "📈 양호한 수익성을 유지하고 있어요"
    elif operating_margin >= 5:
        return "📊 보통 수준의 수익성을 보여요"
    elif operating_margin >= 0:
        return "⚠️ 수익성이 다소 낮은 편이에요"
    else:
        return "❌ 영업손실을 기록하고 있어 주의가 필요해요"

def _get_stability_insight(debt_ratio: float) -> str:
    """재무 안정성 인사이트"""
    if debt_ratio <= 30:
        return "🛡️ 부채비율이 낮아 재무가 매우 안정적이에요"
    elif debt_ratio <= 50:
        return "✅ 적정 수준의 부채비율을 유지하고 있어요"
    elif debt_ratio <= 70:
        return "⚡ 부채비율이 다소 높은 편이에요"
    else:
        return "🚨 부채비율이 높아 재무 위험이 있어요"

def _get_overall_grade(operating_margin: float, net_margin: float, debt_ratio: float) -> str:
    """종합 등급 산정"""
    score = 0
    
    # 영업이익률 점수
    if operating_margin >= 15:
        score += 30
    elif operating_margin >= 10:
        score += 25
    elif operating_margin >= 5:
        score += 20
    elif operating_margin >= 0:
        score += 10
    
    # 순이익률 점수
    if net_margin >= 10:
        score += 30
    elif net_margin >= 5:
        score += 25
    elif net_margin >= 3:
        score += 20
    elif net_margin >= 0:
        score += 10
    
    # 부채비율 점수 (낮을수록 좋음)
    if debt_ratio <= 30:
        score += 40
    elif debt_ratio <= 50:
        score += 30
    elif debt_ratio <= 70:
        score += 20
    else:
        score += 10
    
    # 등급 결정
    if score >= 80:
        return "⭐⭐⭐ 우수한 재무 상태"
    elif score >= 60:
        return "⭐⭐ 양호한 재무 상태"
    elif score >= 40:
        return "⭐ 보통 수준의 재무 상태"
    else:
        return "⚠️ 재무 상태 개선 필요"

@app.errorhandler(404)
def not_found(error):
    """404 에러 핸들러"""
    return jsonify({
        'success': False,
        'message': '요청한 리소스를 찾을 수 없습니다.'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """500 에러 핸들러"""
    return jsonify({
        'success': False,
        'message': '서버 내부 오류가 발생했습니다.'
    }), 500

if __name__ == '__main__':
    # 서버 실행
    print("=== 오픈다트 재무 데이터 시각화 분석 서비스 ===")
    print("서버가 시작됩니다...")
    
    # 데이터베이스 초기화
    initialize_database()
    
    # 포트 설정 (환경 변수에서 가져오거나 기본값 5000 사용)
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_ENV', 'development') == 'development'
    
    print(f"URL: http://localhost:{port}")
    print("API 문서:")
    print("  - GET /api/search?q=회사명 : 회사 검색")
    print("  - GET /api/company/{corp_code} : 회사 정보 조회")
    print("  - GET /api/random : 랜덤 회사 목록")
    print("  - GET /api/stats : 데이터베이스 통계")
    
    app.run(debug=debug_mode, host='0.0.0.0', port=port)
