// 오픈다트 회사 검색 서비스 - JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // DOM 요소들
    const searchInput = document.getElementById('searchInput');
    const searchBtn = document.getElementById('searchBtn');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const resultHeader = document.getElementById('resultHeader');
    const resultSection = document.getElementById('resultSection');
    const noResultSection = document.getElementById('noResultSection');
    const errorSection = document.getElementById('errorSection');
    const resultTitle = document.getElementById('resultTitle');
    const resultCount = document.getElementById('resultCount');
    const resultTableBody = document.getElementById('resultTableBody');
    const errorMessage = document.getElementById('errorMessage');
    const randomBtn = document.getElementById('randomBtn');
    const randomCompanies = document.getElementById('randomCompanies');

    // 차트 관련 요소들
    const chartSection = document.getElementById('chartSection');
    const chartCompanyName = document.getElementById('chartCompanyName');
    const chartLoadingIndicator = document.getElementById('chartLoadingIndicator');
    const chartErrorSection = document.getElementById('chartErrorSection');
    const chartErrorMessage = document.getElementById('chartErrorMessage');

    // 차트 인스턴스들
    let revenueChart = null;
    let assetChart = null;
    let balanceChart = null;
    let currentCompany = null;

    // 통계 요소들
    const totalCompanies = document.getElementById('totalCompanies');
    const listedCompanies = document.getElementById('listedCompanies');
    const unlistedCompanies = document.getElementById('unlistedCompanies');
    const lastModified = document.getElementById('lastModified');

    // 초기화
    init();

    // 이벤트 리스너 등록
    searchBtn.addEventListener('click', performSearch);
    searchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            performSearch();
        }
    });
    searchInput.addEventListener('input', function() {
        clearResults();
    });
    randomBtn.addEventListener('click', loadRandomCompanies);

    /**
     * 초기화 함수
     */
    function init() {
        loadStats();
        loadRandomCompanies();
        searchInput.focus();
    }

    /**
     * 통계 정보 로드
     */
    async function loadStats() {
        try {
            const response = await fetch('/api/stats');
            const data = await response.json();

            if (data.success) {
                const stats = data.data;
                totalCompanies.textContent = formatNumber(stats.total_companies);
                listedCompanies.textContent = formatNumber(stats.listed_companies);
                unlistedCompanies.textContent = formatNumber(stats.unlisted_companies);
                lastModified.textContent = formatDate(stats.last_modified);
            }
        } catch (error) {
            console.error('통계 로드 실패:', error);
        }
    }

    /**
     * 랜덤 회사 목록 로드
     */
    async function loadRandomCompanies() {
        try {
            const response = await fetch('/api/random?limit=8');
            const data = await response.json();

            if (data.success && data.data.length > 0) {
                displayRandomCompanies(data.data);
            }
        } catch (error) {
            console.error('랜덤 회사 로드 실패:', error);
        }
    }

    /**
     * 랜덤 회사 목록 표시
     */
    function displayRandomCompanies(companies) {
        randomCompanies.innerHTML = '';

        companies.forEach(company => {
            const col = document.createElement('div');
            col.className = 'col-md-3 col-sm-6 mb-3';

            col.innerHTML = `
                <div class="random-company-card" onclick="searchCompany('${company.corp_name}')">
                    <div class="random-company-name">${escapeHtml(company.corp_name)}</div>
                    <div class="random-company-eng">${escapeHtml(company.corp_eng_name || '')}</div>
                    <div class="random-company-info">
                        <span class="corp-code">${company.corp_code}</span>
                        <span class="stock-code">${company.stock_code}</span>
                    </div>
                </div>
            `;

            randomCompanies.appendChild(col);
        });
    }

    /**
     * 회사 검색 (랜덤 회사 클릭 시)
     */
    function searchCompany(companyName) {
        searchInput.value = companyName;
        performSearch();
    }

    /**
     * 검색 수행
     */
    async function performSearch() {
        const query = searchInput.value.trim();

        if (!query) {
            showError('검색어를 입력해주세요.');
            return;
        }

        showLoading();

        try {
            const response = await fetch(`/api/search?q=${encodeURIComponent(query)}&limit=50`);
            const data = await response.json();

            if (data.success) {
                displayResults(data.data, query);
            } else {
                showError(data.message || '검색 중 오류가 발생했습니다.');
            }
        } catch (error) {
            console.error('검색 실패:', error);
            showError('서버와의 연결에 실패했습니다.');
        }
    }

    /**
     * 검색 결과 표시
     */
    function displayResults(companies, query) {
        hideAllSections();

        if (companies.length === 0) {
            noResultSection.style.display = 'block';
            return;
        }

        // 결과 헤더 설정
        resultTitle.textContent = `"${query}" 검색 결과`;
        resultCount.textContent = `${companies.length}개`;

        // 테이블 내용 생성
        resultTableBody.innerHTML = '';

        companies.forEach(company => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>
                    <span class="corp-code">${company.corp_code}</span>
                    <button class="copy-btn ms-2" onclick="copyToClipboard('${company.corp_code}')" title="복사">
                        <i class="bi bi-clipboard"></i>
                    </button>
                </td>
                <td>
                    <strong>${highlightText(escapeHtml(company.corp_name), query)}</strong>
                </td>
                <td>
                    <span class="text-muted">${escapeHtml(company.corp_eng_name || '-')}</span>
                </td>
                <td>
                    ${company.stock_code ? 
                        `<span class="stock-code">${company.stock_code}</span>
                         <button class="copy-btn ms-2" onclick="copyToClipboard('${company.stock_code}')" title="복사">
                             <i class="bi bi-clipboard"></i>
                         </button>` : 
                        '<span class="text-muted">-</span>'
                    }
                </td>
                <td>
                    <span class="status-badge ${company.stock_code ? 'status-listed' : 'status-unlisted'}">
                        ${company.stock_code ? '상장' : '비상장'}
                    </span>
                </td>
                <td>
                    ${company.stock_code ? 
                        `<button class="financial-btn" onclick="showFinancialChart('${company.corp_code}', '${escapeHtml(company.corp_name)}')" title="재무 분석">
                             <i class="bi bi-bar-chart-line"></i>
                             분석
                         </button>` : 
                        '<span class="text-muted">-</span>'
                    }
                </td>
            `;

            // 행 클릭 이벤트
            row.addEventListener('click', function(e) {
                if (!e.target.closest('.copy-btn')) {
                    showCompanyDetails(company);
                }
            });

            resultTableBody.appendChild(row);
        });

        // 결과 섹션 표시
        resultHeader.style.display = 'block';
        resultSection.style.display = 'block';
        resultSection.classList.add('fade-in');

        // 결과 섹션으로 스크롤
        resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    /**
     * 회사 상세 정보 표시 (모달 또는 새 창)
     */
    function showCompanyDetails(company) {
        const details = `
회사명: ${company.corp_name}
영문명: ${company.corp_eng_name || '-'}
고유번호: ${company.corp_code}
종목코드: ${company.stock_code || '-'}
구분: ${company.stock_code ? '상장' : '비상장'}
수정일: ${formatDate(company.modify_date)}
        `;

        alert(details);
    }

    /**
     * 클립보드에 복사
     */
    window.copyToClipboard = function(text) {
        navigator.clipboard.writeText(text).then(function() {
            showToast('복사되었습니다: ' + text);
        }).catch(function(err) {
            console.error('복사 실패:', err);
            showToast('복사에 실패했습니다.');
        });
    };

    /**
     * 토스트 메시지 표시
     */
    function showToast(message) {
        // 간단한 토스트 메시지 (Bootstrap 토스트 사용 가능)
        const toast = document.createElement('div');
        toast.className = 'position-fixed top-0 end-0 p-3';
        toast.style.zIndex = '1050';
        toast.innerHTML = `
            <div class="toast show" role="alert">
                <div class="toast-body">
                    ${escapeHtml(message)}
                </div>
            </div>
        `;

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.remove();
        }, 3000);
    }

    /**
     * 로딩 상태 표시
     */
    function showLoading() {
        hideAllSections();
        loadingIndicator.style.display = 'block';
    }

    /**
     * 오류 메시지 표시
     */
    function showError(message) {
        hideAllSections();
        errorMessage.textContent = message;
        errorSection.style.display = 'block';
    }

    /**
     * 결과 초기화
     */
    function clearResults() {
        hideAllSections();
    }

    /**
     * 모든 결과 섹션 숨기기
     */
    function hideAllSections() {
        loadingIndicator.style.display = 'none';
        resultHeader.style.display = 'none';
        resultSection.style.display = 'none';
        noResultSection.style.display = 'none';
        errorSection.style.display = 'none';
    }

    /**
     * 텍스트 하이라이트
     */
    function highlightText(text, query) {
        if (!query) return text;

        const regex = new RegExp(`(${escapeRegex(query)})`, 'gi');
        return text.replace(regex, '<span class="highlight">$1</span>');
    }

    /**
     * HTML 이스케이프
     */
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * 정규식 이스케이프
     */
    function escapeRegex(string) {
        return string.replace(/[.*+?^${}()|[\\]\\]/g, '\\$&');
    }

    /**
     * 숫자 포맷팅 (천 단위 콤마)
     */
    function formatNumber(num) {
        return num.toLocaleString();
    }

    /**
     * 날짜 포맷팅
     */
    function formatDate(dateString) {
        if (!dateString) return '-';

        // YYYYMMDD 형식을 YYYY-MM-DD로 변환
        if (dateString.length === 8) {
            const year = dateString.substring(0, 4);
            const month = dateString.substring(4, 6);
            const day = dateString.substring(6, 8);
            return `${year}-${month}-${day}`;
        }

        return dateString;
    }

    /**
     * 실시간 검색 (옵션)
     */
    let searchTimeout;
    searchInput.addEventListener('input', function() {
        clearTimeout(searchTimeout);
        const query = this.value.trim();

        if (query.length >= 2) {
            searchTimeout = setTimeout(() => {
                performSearch();
            }, 500); // 500ms 딜레이
        } else {
            clearResults();
        }
    });

    // 키보드 단축키
    document.addEventListener('keydown', function(e) {
        // Ctrl+K 또는 Cmd+K로 검색창 포커스
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            searchInput.focus();
            searchInput.select();
        }

        // ESC로 결과 초기화
        if (e.key === 'Escape') {
            clearResults();
            searchInput.focus();
        }
    });

    // ========== 차트 관련 함수들 ==========

    /**
     * 재무 차트 표시
     */
    window.showFinancialChart = function(corpCode, companyName) {
        currentCompany = { corp_code: corpCode, corp_name: companyName };
        chartCompanyName.textContent = companyName;
        
        // 차트 섹션 표시
        chartSection.style.display = 'block';
        chartSection.scrollIntoView({ behavior: 'smooth' });
        
        // 기본 차트 로드 (손익 분석)
        loadRevenueChart(corpCode);
    };

    /**
     * 차트 숨기기
     */
    window.hideCharts = function() {
        chartSection.style.display = 'none';
        
        // 차트 인스턴스 정리
        if (revenueChart) {
            revenueChart.destroy();
            revenueChart = null;
        }
        if (assetChart) {
            assetChart.destroy();
            assetChart = null;
        }
        if (balanceChart) {
            balanceChart.destroy();
            balanceChart = null;
        }
        
        currentCompany = null;
    };

    /**
     * 손익 분석 차트 로드
     */
    function loadRevenueChart(corpCode, years = '2018,2019,2020,2021,2022') {
        showChartLoading();
        
        fetch(`/api/financial/chart/${corpCode}?type=revenue&years=${years}`)
            .then(response => response.json())
            .then(data => {
                hideChartLoading();
                
                if (data.success) {
                    createRevenueChart(data.data.chart_data);
                } else {
                    showChartError(data.message);
                }
            })
            .catch(error => {
                hideChartLoading();
                showChartError('차트 데이터 로드 중 오류가 발생했습니다.');
                console.error('차트 로드 실패:', error);
            });
    }

    /**
     * 재무상태 분석 차트 로드
     */
    function loadAssetChart(corpCode, years = '2018,2019,2020,2021,2022') {
        showChartLoading();
        
        fetch(`/api/financial/chart/${corpCode}?type=asset&years=${years}`)
            .then(response => response.json())
            .then(data => {
                hideChartLoading();
                
                if (data.success) {
                    createAssetChart(data.data.chart_data);
                } else {
                    showChartError(data.message);
                }
            })
            .catch(error => {
                hideChartLoading();
                showChartError('차트 데이터 로드 중 오류가 발생했습니다.');
                console.error('차트 로드 실패:', error);
            });
    }

    /**
     * 회계등식 균형 차트 로드
     */
    function loadBalanceChart(corpCode, years = '2018,2019,2020,2021,2022') {
        showChartLoading();
        
        fetch(`/api/financial/chart/${corpCode}?type=balance&years=${years}`)
            .then(response => response.json())
            .then(data => {
                hideChartLoading();
                
                if (data.success) {
                    createBalanceChart(data.data.chart_data);
                } else {
                    showChartError(data.message);
                }
            })
            .catch(error => {
                hideChartLoading();
                showChartError('차트 데이터 로드 중 오류가 발생했습니다.');
                console.error('차트 로드 실패:', error);
            });
    }

    /**
     * 손익 차트 생성
     */
    function createRevenueChart(chartData) {
        const ctx = document.getElementById('revenueChart').getContext('2d');
        
        // 기존 차트 제거
        if (revenueChart) {
            revenueChart.destroy();
        }
        
        revenueChart = new Chart(ctx, {
            type: 'line',
            data: chartData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: '손익 현황 (단위: 억원)',
                        font: {
                            size: 16,
                            weight: 'bold'
                        }
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: '금액 (억원)'
                        },
                        ticks: {
                            callback: function(value) {
                                return value.toLocaleString() + '억';
                            }
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: '연도'
                        }
                    }
                },
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                tooltips: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': ' + context.parsed.y.toLocaleString() + '억원';
                        }
                    }
                }
            }
        });
    }

    /**
     * 재무상태 차트 생성
     */
    function createAssetChart(chartData) {
        const ctx = document.getElementById('assetChart').getContext('2d');
        
        // 기존 차트 제거
        if (assetChart) {
            assetChart.destroy();
        }
        
        assetChart = new Chart(ctx, {
            type: 'bar',
            data: chartData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: '재무상태 현황 (단위: 억원)',
                        font: {
                            size: 16,
                            weight: 'bold'
                        }
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: '금액 (억원)'
                        },
                        ticks: {
                            callback: function(value) {
                                return value.toLocaleString() + '억';
                            }
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: '연도'
                        }
                    }
                },
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                tooltips: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': ' + context.parsed.y.toLocaleString() + '억원';
                        }
                    }
                }
            }
        });
    }

    /**
     * 회계등식 균형 차트 생성
     */
    function createBalanceChart(chartData) {
        const ctx = document.getElementById('balanceChart').getContext('2d');
        
        // 기존 차트 제거
        if (balanceChart) {
            balanceChart.destroy();
        }
        
        balanceChart = new Chart(ctx, {
            type: 'bar',
            data: chartData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: '회계등식 균형 분석: 자산 = 부채 + 자본 (단위: 억원)',
                        font: {
                            size: 16,
                            weight: 'bold'
                        }
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                label += context.parsed.y.toLocaleString() + '억원';
                                return label;
                            },
                            afterBody: function(tooltipItems) {
                                const dataIndex = tooltipItems[0].dataIndex;
                                const datasets = balanceChart.data.datasets;
                                
                                // 자산, 부채+자본 값 추출
                                const assetValue = datasets.find(d => d.label.includes('자산총계')).data[dataIndex];
                                const debtEquityValue = datasets.find(d => d.label.includes('부채+자본')).data[dataIndex];
                                const difference = Math.abs(assetValue - debtEquityValue);
                                
                                return [
                                    '',
                                    `차이: ${difference.toLocaleString()}억원`,
                                    difference < 1 ? '✅ 균형 일치' : '⚠️ 균형 불일치'
                                ];
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: '금액 (억원)'
                        },
                        ticks: {
                            callback: function(value) {
                                return value.toLocaleString() + '억';
                            }
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: '연도'
                        }
                    }
                },
                interaction: {
                    mode: 'index',
                    intersect: false
                }
            }
        });
    }

    /**
     * 차트 업데이트 함수들
     */
    window.updateRevenueChart = function() {
        if (currentCompany) {
            const years = document.getElementById('revenueYears').value;
            loadRevenueChart(currentCompany.corp_code, years);
        }
    };

    window.updateAssetChart = function() {
        if (currentCompany) {
            const years = document.getElementById('assetYears').value;
            loadAssetChart(currentCompany.corp_code, years);
        }
    };

    window.updateBalanceChart = function() {
        if (currentCompany) {
            const years = document.getElementById('balanceYears').value;
            loadBalanceChart(currentCompany.corp_code, years);
        }
    };

    /**
     * 차트 로딩 상태 표시/숨김
     */
    function showChartLoading() {
        chartLoadingIndicator.style.display = 'block';
        chartErrorSection.style.display = 'none';
    }

    function hideChartLoading() {
        chartLoadingIndicator.style.display = 'none';
    }

    /**
     * 차트 오류 메시지 표시
     */
    function showChartError(message) {
        chartErrorMessage.textContent = message;
        chartErrorSection.style.display = 'block';
        chartLoadingIndicator.style.display = 'none';
    }

    /**
     * AI 분석 시작
     */
    window.startAIAnalysis = function() {
        if (!currentCompany) {
            showAIError('회사 정보가 없습니다. 다시 시도해주세요.');
            return;
        }

        const analysisType = document.getElementById('analysisType').value;
        
        if (analysisType === 'quick') {
            loadQuickInsights(currentCompany.corp_code);
        } else {
            loadDetailedAIAnalysis(currentCompany.corp_code);
        }
    };

    /**
     * 빠른 인사이트 로드
     */
    function loadQuickInsights(corpCode) {
        showAILoading();
        
        fetch(`/api/ai-insights/${corpCode}?year=2022`)
            .then(response => response.json())
            .then(data => {
                hideAILoading();
                
                if (data.success) {
                    displayQuickInsights(data.data.insights);
                } else {
                    showAIError(data.message);
                }
            })
            .catch(error => {
                hideAILoading();
                showAIError('빠른 인사이트 로드 중 오류가 발생했습니다.');
                console.error('AI 인사이트 로드 실패:', error);
            });
    }

    /**
     * 상세 AI 분석 로드
     */
    function loadDetailedAIAnalysis(corpCode) {
        showAILoading();
        
        fetch(`/api/ai-analysis/${corpCode}?years=2020,2021,2022`)
            .then(response => response.json())
            .then(data => {
                hideAILoading();
                
                if (data.success) {
                    displayAIAnalysis(data.data.analysis);
                } else {
                    showAIError(data.message);
                }
            })
            .catch(error => {
                hideAILoading();
                showAIError('AI 분석 중 오류가 발생했습니다.');
                console.error('AI 분석 실패:', error);
            });
    }

    /**
     * 빠른 인사이트 표시
     */
    function displayQuickInsights(insights) {
        // 기존 결과 숨기기
        document.getElementById('aiAnalysisResult').style.display = 'none';
        
        // 인사이트 내용 업데이트
        document.getElementById('revenueScaleInsight').textContent = insights.revenue_scale;
        document.getElementById('profitabilityInsight').textContent = insights.profitability;
        document.getElementById('stabilityInsight').textContent = insights.financial_stability;
        document.getElementById('overallGrade').textContent = insights.overall_grade;
        
        // 빠른 인사이트 섹션 표시
        document.getElementById('quickInsights').style.display = 'block';
        document.getElementById('quickInsights').classList.add('fade-in');
    }

    /**
     * AI 상세 분석 표시
     */
    function displayAIAnalysis(analysisText) {
        // 기존 결과 숨기기
        document.getElementById('quickInsights').style.display = 'none';
        
        // AI 분석 텍스트 처리 및 표시
        const formattedText = formatAIAnalysisText(analysisText);
        document.getElementById('aiAnalysisText').innerHTML = formattedText;
        
        // AI 분석 결과 섹션 표시
        document.getElementById('aiAnalysisResult').style.display = 'block';
        document.getElementById('aiAnalysisResult').classList.add('fade-in');
    }

    /**
     * AI 분석 텍스트 포맷팅
     */
    function formatAIAnalysisText(text) {
        // 기본 HTML 이스케이프 후 마크다운 스타일 변환
        let formatted = escapeHtml(text);
        
        // **굵은 텍스트** 처리
        formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        // *기울임 텍스트* 처리
        formatted = formatted.replace(/\*(.*?)\*/g, '<em>$1</em>');
        
        // 이모지와 함께 시작하는 제목 처리
        formatted = formatted.replace(/^([📊💰🏦⭐🚀⚠️❌✅🎯📈📉💡🔍]+)\s*(.+)$/gm, '<h6><span style="margin-right: 8px;">$1</span>$2</h6>');
        
        // 숫자 목록 처리
        formatted = formatted.replace(/^(\d+)\.\s+(.+)$/gm, '<div style="margin: 0.5rem 0;"><strong>$1.</strong> $2</div>');
        
        // 대시로 시작하는 항목 처리
        formatted = formatted.replace(/^-\s+(.+)$/gm, '<div style="margin: 0.3rem 0; margin-left: 1rem;">• $1</div>');
        
        // 줄바꿈 처리
        formatted = formatted.replace(/\n\n/g, '<br><br>');
        formatted = formatted.replace(/\n/g, '<br>');
        
        return formatted;
    }

    /**
     * AI 로딩 상태 표시/숨김
     */
    function showAILoading() {
        document.getElementById('aiLoadingIndicator').style.display = 'block';
        document.getElementById('aiErrorSection').style.display = 'none';
        document.getElementById('quickInsights').style.display = 'none';
        document.getElementById('aiAnalysisResult').style.display = 'none';
    }

    function hideAILoading() {
        document.getElementById('aiLoadingIndicator').style.display = 'none';
    }

    /**
     * AI 오류 메시지 표시
     */
    function showAIError(message) {
        document.getElementById('aiErrorMessage').textContent = message;
        document.getElementById('aiErrorSection').style.display = 'block';
        document.getElementById('aiLoadingIndicator').style.display = 'none';
        document.getElementById('quickInsights').style.display = 'none';
        document.getElementById('aiAnalysisResult').style.display = 'none';
    }

    // 탭 전환 이벤트 리스너
    document.addEventListener('shown.bs.tab', function(event) {
        if (currentCompany) {
            const targetId = event.target.getAttribute('data-bs-target');
            
            if (targetId === '#asset-pane' && !assetChart) {
                const years = document.getElementById('assetYears').value;
                loadAssetChart(currentCompany.corp_code, years);
            } else if (targetId === '#balance-pane' && !balanceChart) {
                const years = document.getElementById('balanceYears').value;
                loadBalanceChart(currentCompany.corp_code, years);
            }
        }
    });
});
