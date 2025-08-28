# 오픈다트 회사 검색 서비스

한국의 상장/비상장 기업 정보를 빠르게 검색할 수 있는 웹 서비스입니다. 오픈다트의 corp.xml 파일을 기반으로 구축되었습니다.

## 🚀 주요 기능

- **빠른 회사 검색**: 회사명으로 실시간 검색
- **상세 정보 제공**: 고유번호(corp_code), 종목코드, 영문명 등
- **상장/비상장 구분**: 회사 유형을 명확히 표시
- **통계 정보**: 전체/상장/비상장 기업 수 통계
- **랜덤 추천**: 상장 기업 랜덤 추천 기능
- **복사 기능**: 고유번호, 종목코드 원클릭 복사

## 📋 요구사항

- Python 3.7+
- Flask 2.3.3
- Flask-CORS 4.0.0

## 🛠️ 설치 및 실행

### 1. 프로젝트 클론 또는 다운로드

```bash
# 프로젝트 디렉토리로 이동
cd vive_fs5
```

### 2. 필요한 패키지 설치

```bash
pip install -r requirements.txt
```

### 3. 데이터베이스 생성

```bash
python xml_to_db.py
```

이 명령어는 `corp.xml` 파일을 읽어서 SQLite 데이터베이스(`companies.db`)를 생성합니다.

### 4. 웹 서버 실행

```bash
python app.py
```

서버가 시작되면 브라우저에서 `http://localhost:5000`으로 접속하세요.

## 📁 프로젝트 구조

```
vive_fs5/
├── app.py                 # Flask 웹 애플리케이션
├── xml_to_db.py          # XML을 SQLite DB로 변환하는 스크립트
├── corp.xml              # 오픈다트 기업 정보 XML 파일
├── companies.db          # SQLite 데이터베이스 (생성됨)
├── requirements.txt      # Python 패키지 의존성
├── templates/
│   └── index.html       # 메인 웹페이지
├── static/
│   ├── style.css        # CSS 스타일시트
│   └── script.js        # JavaScript
└── README.md            # 프로젝트 설명서
```

## 🔍 API 엔드포인트

### 회사 검색
```
GET /api/search?q={검색어}&limit={결과수}
```

**예시:**
```bash
curl "http://localhost:5000/api/search?q=삼성&limit=10"
```

**응답:**
```json
{
  "success": true,
  "message": "5개의 검색 결과를 찾았습니다.",
  "data": [
    {
      "corp_code": "00126380",
      "corp_name": "삼성전자",
      "corp_eng_name": "SAMSUNG ELECTRONICS CO.,LTD.",
      "stock_code": "005930",
      "modify_date": "20170630"
    }
  ],
  "query": "삼성",
  "count": 5
}
```

### 특정 회사 조회
```
GET /api/company/{corp_code}
```

### 랜덤 회사 목록
```
GET /api/random?limit={개수}
```

### 데이터베이스 통계
```
GET /api/stats
```

## 🎯 사용법

1. **회사 검색**: 메인 페이지에서 회사명을 입력하고 검색 버튼을 클릭하세요.
2. **실시간 검색**: 2글자 이상 입력하면 자동으로 검색이 시작됩니다.
3. **상세 정보**: 검색 결과의 행을 클릭하면 회사 상세 정보를 확인할 수 있습니다.
4. **코드 복사**: 고유번호나 종목코드 옆의 복사 버튼을 클릭하여 클립보드에 복사하세요.
5. **랜덤 추천**: 화면 하단의 추천 기업들을 클릭하여 해당 기업을 검색할 수 있습니다.

## ⌨️ 키보드 단축키

- `Ctrl + K` (또는 `Cmd + K`): 검색창으로 포커스 이동
- `Enter`: 검색 실행
- `ESC`: 검색 결과 초기화

## 📊 데이터 정보

- **데이터 출처**: 오픈다트(OpenDART)
- **총 기업 수**: 3,864개 (corp.xml 기준)
- **상장 기업**: 상장사 정보 포함
- **비상장 기업**: 대형 비상장사 정보 포함
- **마지막 업데이트**: 2017-06-30

## 🔧 기술 스택

- **백엔드**: Python Flask
- **데이터베이스**: SQLite (FTS5 전문검색 지원)
- **프론트엔드**: HTML5, CSS3, JavaScript (Vanilla)
- **UI 프레임워크**: Bootstrap 5
- **아이콘**: Bootstrap Icons

## 🚀 향후 개선 계획

- [ ] 재무 데이터 시각화 추가
- [ ] 기업 상세 정보 페이지
- [ ] 검색 필터 기능 (상장/비상장, 업종별)
- [ ] 즐겨찾기 기능
- [ ] API 키 관리 및 오픈다트 실시간 데이터 연동
- [ ] 데이터 자동 업데이트 기능

## 📝 라이선스

이 프로젝트는 교육 및 연구 목적으로 만들어졌습니다.

## 🤝 기여하기

이슈나 개선 사항이 있으시면 언제든지 제안해주세요!

---

**제작자**: AI Assistant  
**버전**: 1.0.0  
**최종 업데이트**: 2024년 8월
