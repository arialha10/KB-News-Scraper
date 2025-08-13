from flask import Flask, render_template, render_template_string, request, jsonify
import requests
import urllib3
import os
import json
import time  # 요청 간 딜레이를 위해 사용 (e.g. time.sleep(0.3))
from datetime import datetime  # 기본값 설정용 (datetime.min 등)
from email.utils import parsedate_to_datetime  # Naver pubDate 파싱용
import re
from html import unescape
try:
    import winreg  # Windows-only; used to persist LP list without user files
    HAS_WINREG = True
except Exception:
    HAS_WINREG = False


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

@app.route('/favicon.ico')
def favicon():
  return '', 204

# Replace these with your actual Naver API credentials
NAVER_CLIENT_ID = 'nzDM7w5sD0_aJQOyWFFZ'
NAVER_CLIENT_SECRET = 'ppTjGSKIFT'



# HTML template
TEMPLATE = r'''
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <title>뉴스 스크래퍼</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    :root {
      --primary-color: #1f2937;
      --primary-hover: #111827;
      --secondary-color: #f9fafb;
      --accent-color: #374151;
      --success-color: #059669;
      --danger-color: #dc2626;
      --warning-color: #d97706;
      --text-primary: #111827;
      --text-secondary: #6b7280;
      --border-color: #d1d5db;
      --bg-light: #f9fafb;
      --bg-white: #ffffff;
      --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
      --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
      --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
    }

    * {
      box-sizing: border-box;
    }

    html, body {
      margin: 0;
      height: 100%;
      background: #f5f5f5;
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      color: var(--text-primary);
      line-height: 1.6;
    }

    body {
      padding: 0;
      overflow-x: hidden;
    }

    .main-container {
      height: 100vh;
      background: var(--bg-white);
      margin: 0;
      box-shadow: none;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }

    .header {
      background: var(--primary-color);
      color: white;
      padding: 1.5rem 2rem;
      margin: 0;
      border-bottom: 1px solid var(--border-color);
      flex: 0 0 auto;
    }

    .header-content {
      position: relative;
      z-index: 1;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 1rem;
    }

    .header h3 {
      margin: 0;
      font-size: 1.5rem;
      font-weight: 600;
      letter-spacing: -0.025em;
    }

    .header-links {
      display: flex;
      gap: 0.75rem;
    }

    .header-links .btn {
      background: transparent;
      border: 1px solid rgba(255, 255, 255, 0.3);
      color: white;
      padding: 0.5rem 1rem;
      border-radius: 6px;
      text-decoration: none;
      font-weight: 500;
      transition: all 0.2s ease;
      font-size: 0.875rem;
    }

    .header-links .btn:hover {
      background: rgba(255, 255, 255, 0.1);
      border-color: rgba(255, 255, 255, 0.5);
    }

    .content-wrapper {
      display: flex;
      flex: 1 1 auto;
      min-height: 0; /* allow children to size and scroll without extra space */
    }

    .lp-wrapper {
      width: 300px;
      background: var(--bg-light);
      border-right: 1px solid var(--border-color);
      display: flex;
      flex-direction: column;
      position: sticky;
      top: 0;
      height: 100%;
    }

    .lp-header {
      padding: 1.5rem;
      border-bottom: 1px solid var(--border-color);
      background: white;
      position: sticky;
      top: 0;
      z-index: 2;
    }

    .lp-actions {
      display: flex;
      gap: 0.5rem;
      align-items: center;
    }

    .lp-reset-btn {
      background: var(--accent-color);
      color: white;
      border: none;
      padding: 0.5rem 0.75rem;
      border-radius: 8px;
      font-size: 0.75rem;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.3s ease;
    }

    .lp-reset-btn:hover {
      background: var(--primary-hover);
      transform: translateY(-1px);
    }

    .lp-search {
      position: relative;
      margin-bottom: 1rem;
    }

    .lp-search input {
      width: 100%;
      padding: 0.75rem 1rem 0.75rem 2.5rem;
      border: 1px solid var(--border-color);
      border-radius: 12px;
      font-size: 0.875rem;
      background: white;
      transition: all 0.3s ease;
    }

    .lp-search input:focus {
      outline: none;
      border-color: var(--primary-color);
      box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
    }

    .lp-search::before {
      content: '🔍';
      position: absolute;
      left: 0.75rem;
      top: 50%;
      transform: translateY(-50%);
      font-size: 0.875rem;
      color: var(--text-secondary);
    }

    .edit-btn {
      background: var(--primary-color);
      color: white;
      border: none;
      padding: 0.5rem 1rem;
      border-radius: 8px;
      font-size: 0.75rem;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.3s ease;
    }

    .edit-btn:hover {
      background: var(--primary-hover);
      transform: translateY(-1px);
    }

    .lp-list {
      flex: 1;
      overflow-y: auto;
      padding: 1rem;
      scrollbar-width: thin;
      scrollbar-color: var(--border-color) transparent;
      min-height: 0; /* prevent flex overflow */
    }

    .lp-list::-webkit-scrollbar {
      width: 6px;
    }

    .lp-list::-webkit-scrollbar-track {
      background: transparent;
    }

    .lp-list::-webkit-scrollbar-thumb {
      background: var(--border-color);
      border-radius: 3px;
    }

    .lp-list::-webkit-scrollbar-thumb:hover {
      background: var(--text-secondary);
    }

    .category-label {
      background: #eef2f7;
      color: var(--text-primary);
      padding: 0.5rem 0.75rem;
      border-radius: 4px;
      margin: 1rem 0 0.5rem 0;
      font-weight: 600;
      font-size: 0.75rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      border: 1px solid var(--border-color);
    }

    .category-label button {
      background: white;
      border: 1px solid var(--border-color);
      color: var(--text-primary);
      width: 24px;
      height: 24px;
      border-radius: 6px;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: all 0.3s ease;
    }

    .category-label button:hover {
      background: var(--bg-light);
      transform: scale(1.1);
    }

    .category-actions { display: flex; gap: 0.25rem; }
    .category-reset-btn { font-weight: 700; line-height: 1; }

    /* Active LPs remain clearly distinct */
    .lp-button.active {
      background: var(--primary-color);
      color: white;
      border-color: var(--primary-color);
    }

    .lp-item {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      margin-bottom: 0.5rem;
    }

    .lp-button {
      flex: 1;
      background: white;
      border: 1px solid var(--border-color);
      color: var(--text-primary);
      padding: 0.5rem 0.75rem;
      border-radius: 4px;
      font-size: 0.875rem;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s ease;
      text-align: left;
    }

    .lp-button:hover {
      border-color: var(--primary-color);
      background: var(--bg-light);
    }

    .lp-button.active {
      background: var(--primary-color);
      color: white;
      border-color: var(--primary-color);
    }

    .lp-delete-btn {
      display: none;
      background: var(--danger-color);
      color: white;
      border: none;
      width: 28px;
      height: 28px;
      border-radius: 6px;
      cursor: pointer;
      font-weight: bold;
      transition: all 0.3s ease;
    }

    .edit-mode .lp-delete-btn {
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .lp-delete-btn:hover {
      background: #dc2626;
      transform: scale(1.1);
    }

    .main-content {
      flex: 1;
      padding: 2rem;
      background: white;
      overflow-y: auto;
    }

    .saved-news-card {
      background: var(--bg-white);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      margin-bottom: 2rem;
      box-shadow: var(--shadow-sm);
      overflow: hidden;
    }

    .saved-news-card .card-header {
      background: var(--bg-light);
      color: var(--text-primary);
      border-bottom: 1px solid var(--border-color);
      padding: 1rem 1.5rem;
      font-weight: 600;
    }

    .saved-news-card .btn {
      background: var(--text-secondary);
      border: none;
      color: white;
      padding: 0.375rem 0.75rem;
      border-radius: 4px;
      font-size: 0.75rem;
      transition: all 0.2s ease;
    }

    .saved-news-card .btn:hover {
      background: var(--text-primary);
    }

    .saved-news-list {
      max-height: 300px;
      overflow-y: auto;
      padding: 0;
    }

    .saved-news-list .list-group-item {
      border: none;
      border-bottom: 1px solid rgba(0, 0, 0, 0.1);
      padding: 1rem 1.5rem;
      background: transparent;
      transition: all 0.3s ease;
    }

    .saved-news-list .list-group-item:hover {
      background: rgba(255, 255, 255, 0.5);
    }

    .saved-news-list .list-group-item:last-child {
      border-bottom: none;
    }

    .saved-news-list a {
      color: var(--text-primary);
      text-decoration: none;
      font-weight: 500;
      transition: color 0.3s ease;
    }

    .saved-news-list a:hover {
      color: var(--primary-color);
    }

    .search-section {
      background: var(--bg-white);
      border-radius: 8px;
      padding: 1.5rem;
      margin-bottom: 2rem;
      box-shadow: var(--shadow-sm);
      border: 1px solid var(--border-color);
    }

    .search-section h5 {
      color: var(--text-primary);
      font-weight: 600;
      margin-bottom: 1rem;
      font-size: 1.125rem;
    }

    .category-toggles {
      display: flex;
      flex-wrap: wrap;
      gap: 0.75rem;
      margin-bottom: 1.5rem;
    }

    .category-toggle {
      background: var(--bg-white);
      border: 1px solid var(--border-color);
      color: var(--text-primary);
      padding: 0.5rem 1rem;
      border-radius: 4px;
      font-size: 0.875rem;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s ease;
    }

    .category-toggle:hover {
      border-color: var(--primary-color);
      background: var(--bg-light);
    }

    .category-toggle.active {
      background: var(--primary-color);
      color: white;
      border-color: var(--primary-color);
    }

    .search-actions {
      display: flex;
      gap: 0.75rem;
      margin-top: 1rem;
    }

    .search-btn {
      background: var(--primary-color);
      border: none;
      color: white;
      padding: 0.75rem 1.5rem;
      border-radius: 6px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s ease;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.875rem;
    }

    .search-btn:hover {
      background: var(--primary-hover);
    }

    .search-btn svg {
      width: 16px;
      height: 16px;
    }

    .reset-btn {
      background: var(--text-secondary);
      border: none;
      color: white;
      padding: 0.75rem 1.5rem;
      border-radius: 6px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s ease;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.875rem;
    }

    .reset-btn:hover {
      background: var(--text-primary);
    }

    .reset-btn svg {
      width: 16px;
      height: 16px;
    }

    .keyword-search {
      margin-top: 1.5rem;
    }

    .keyword-search .input-group {
      box-shadow: var(--shadow-md);
      border-radius: 12px;
      overflow: hidden;
    }

    .keyword-search input {
      border: none;
      padding: 1rem 1.5rem;
      font-size: 1rem;
      background: white;
    }

    .keyword-search input:focus {
      outline: none;
      box-shadow: none;
    }

    .keyword-search .btn {
      background: var(--warning-color);
      border: none;
      color: white;
      padding: 1rem 1.5rem;
      font-weight: 600;
      transition: all 0.3s ease;
    }

    .keyword-search .btn:hover {
      background: #d97706;
      transform: translateX(2px);
    }

    .news-container {
      display: grid;
      gap: 1.5rem;
    }

    .article-card {
      background: var(--bg-white);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      overflow: hidden;
      transition: all 0.2s ease;
      box-shadow: var(--shadow-sm);
    }

    .article-card:hover {
      border-color: var(--primary-color);
      box-shadow: var(--shadow-md);
    }

    .article-card .card-body {
      padding: 1.5rem;
    }

    .article-card .card-title {
      margin-bottom: 1rem;
    }

    .article-card .card-title a {
      color: var(--text-primary);
      text-decoration: none;
      font-weight: 600;
      font-size: 1.125rem;
      line-height: 1.4;
      transition: color 0.3s ease;
    }

    .article-card .card-title a:hover {
      color: var(--primary-color);
    }

    .article-card .card-text {
      color: var(--text-secondary);
      margin-bottom: 1rem;
      line-height: 1.6;
    }

    .article-card strong {
      color: var(--primary-color);
      font-weight: 700;
      background: rgba(31, 41, 55, 0.1);
      padding: 0.1rem 0.2rem;
      border-radius: 3px;
    }

    .article-card .text-muted {
      color: var(--text-secondary);
      font-size: 0.875rem;
    }

    /* Bootstrap pagination theme alignment */
    .pagination { --bs-pagination-border-color: var(--border-color); }
    .pagination .page-link {
      color: var(--text-primary);
      border-color: var(--border-color);
      background: var(--bg-white);
    }
    .pagination .page-link:hover {
      background: var(--bg-light);
      border-color: var(--primary-color);
      color: var(--text-primary);
    }
    .pagination .page-item.active .page-link {
      background: var(--primary-color);
      border-color: var(--primary-color);
      color: #fff;
      box-shadow: none;
    }
    .pagination .page-item.disabled .page-link {
      color: var(--text-secondary);
      background: var(--bg-white);
      border-color: var(--border-color);
    }



    .like-btn {
      background: var(--danger-color);
      border: none;
      color: white;
      padding: 0.5rem 1rem;
      border-radius: 4px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s ease;
    }

    .like-btn:hover {
      background: #b91c1c;
    }

    .like-btn.btn-success {
      background: var(--success-color);
    }

    .like-btn.btn-success:hover {
      background: #047857;
    }

    #loadingSpinner {
      display: none;
      position: fixed;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      z-index: 9999;
      background: rgba(255, 255, 255, 0.95);
      padding: 2rem;
      border-radius: 16px;
      box-shadow: var(--shadow-xl);
      backdrop-filter: blur(10px);
    }

    .spinner-border {
      width: 3rem;
      height: 3rem;
      color: var(--primary-color);
    }

    @media (max-width: 768px) {
      .main-container {
        margin: 10px;
        border-radius: 16px;
      }
      
      .header {
        padding: 1.5rem;
      }


      
      .header h3 {
        font-size: 1.5rem;
      }
      
      .content-wrapper {
        flex-direction: column;
      }
      
      .lp-wrapper {
        width: 100%;
        height: auto;
        position: static;
      }
      
      .main-content {
        padding: 1.5rem;
      }
    }

    /* Smooth animations */
    .fade-in {
      animation: fadeIn 0.5s ease-in;
    }

    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(20px); }
      to { opacity: 1; transform: translateY(0); }
    }

    .slide-in {
      animation: slideIn 0.3s ease-out;
    }

    @keyframes slideIn {
      from { transform: translateX(-20px); opacity: 0; }
      to { transform: translateX(0); opacity: 1; }
    }
  </style>
</head>
<body>
  <div id="loadingSpinner">
    <div class="spinner-border" role="status">
      <span class="visually-hidden">Loading...</span>
    </div>
  </div>

  <div class="main-container">
    <div class="header">
      <div class="header-content">
        <h3>Global Investment Solutions Department LP News</h3>
        <div class="header-links">
          <a class="btn" href="/kpasset" target="_self">우정사업본부</a>
          <a class="btn" href="/kofia" target="_self">금융투자협회</a>
      </div>
    </div>
  </div>

    <div class="content-wrapper">
        <div class="lp-wrapper">
        <div class="lp-header">
          <div class="lp-search">
            <input type="text" id="lpSearch" name="lp_query" placeholder="LP 검색...">
          </div>
          <div class="lp-actions">
            <button id="editLpBtn" class="edit-btn">편집</button>
            <button id="resetLpSelectionBtn" class="lp-reset-btn" title="LP 선택 초기화">LP 선택 초기화</button>
          </div>
        </div>
          <div class="lp-list" id="lpButtons">
            {% for lp in LP_LIST %}
              {% if loop.first or lp.category != LP_LIST[loop.index0 - 1].category %}
              <div class="category-label" data-category="{{ lp.category }}">
                <span class="category-name">{{ lp.category }}</span>
                <div class="category-actions">
                  <button class="category-reset-btn" data-category="{{ lp.category }}" title="카테고리 선택 초기화">↺</button>
                  <button onclick="openAddLpModal('{{ lp.category }}')" title="카테고리에 추가">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                      <path d="M8 4a.5.5 0 0 1 .5.5v3h3a.5.5 0 0 1 0 1h-3v3a.5.5 0 0 1-1 0v-3h-3a.5.5 0 0 1 0-1h3v-3A.5.5 0 0 1 8 4"/>
                    </svg>
                  </button>
                </div>
                </div>
              {% endif %}
              <div class="lp-item">
                <button type="button"
                      class="lp-delete-btn"
                        data-name="{{ lp.name }}"
                        data-category="{{ lp.category }}"
                        data-deletable="true"
                        title="삭제">
                ×
                </button>
              <button class="lp-button"
                      data-category="{{ lp.category }}"
                        data-keywords="{{ lp.name }} {{ lp.eng_name }} {{ lp.abbr1 }} {{ lp.abbr2 }} {{ lp.category }}"
                        onclick="toggleLP(this)">{{ lp.name }}</button>
              </div>
            {% endfor %}
        </div>
      </div>

      <div class="main-content">
        <div class="saved-news-card card">
          <div class="card-header d-flex justify-content-between align-items-center">
            <h5 class="mb-0">Saved News</h5>
            <button class="btn" onclick="clearLikedArticles()">전체 삭제</button>
          </div>
          <ul id="likedList" class="saved-news-list list-group list-group-flush"></ul>
        </div>

        <div class="search-section">
          <h5>카테고리 선택</h5>
          <div id="categoryToggles" class="category-toggles">
            {% set seen_categories = [] %}
            {% for lp in LP_LIST %}
              {% if lp.category not in seen_categories %}
                {% set _ = seen_categories.append(lp.category) %}
                <button class="category-toggle" data-category="{{ lp.category }}">{{ lp.category }}</button>
              {% endif %}
            {% endfor %}
            <div class="search-actions">
              <button class="search-btn" id="searchBtn" title="LP + 키워드 검색">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                  <path d="M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001l3.85 3.85a1 1 0 0 0 1.415-1.415l-3.85-3.85zm-5.242 1.106a5.5 5.5 0 1 1 0-11 5.5 5.5 0 0 1 0 11z"/>
                </svg>
                검색
              </button>
              <button class="reset-btn" id="clearSearch" onclick="clearSearch()" title="초기화">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                  <path d="M8 3a5 5 0 1 0 4.546 2.914.5.5 0 0 1 .908-.417A6 6 0 1 1 8 2v1z"/>
                  <path d="M8 4.466V.534a.25.25 0 0 1 .41-.192l2.36 1.966c.12.1.12.284 0 .384L8.41 4.658A.25.25 0 0 1 8 4.466z"/>
                </svg>
                초기화
              </button>
          </div>
        </div>

          <div class="keyword-search">
            <div class="input-group">
              <input type="text" id="articleSearch" class="form-control" placeholder="키워드 검색...">
            </div>
          </div>
        </div>

        <div class="news-container" id="newsContainer">
          {% for article in articles %}
            <div class="article-card card fade-in">
              <div class="card-body">
                <h5 class="card-title">
                  <a href="{{ article.link }}" target="_blank">{{ article.title | safe }}</a>
                </h5>
                <p class="card-text">{{ article.description | safe }}</p>
                <div class="d-flex justify-content-between align-items-center">
                <small class="text-muted">{{ article.pubDate }}</small>
                  <button class="like-btn"
                          data-title="{{ article.title_plain }}" data-link="{{ article.link }}">❤️</button>
                </div>
              </div>
            </div>
          {% endfor %}
        </div>
        <nav aria-label="News pagination" class="mt-4 mb-4">
          <ul id="pagination" class="pagination justify-content-center"></ul>
        </nav>
        <div class="text-center text-muted small mb-3">&copy; 2025 성관. All rights reserved. For support or emergencies, contact <a href="mailto:elijahha12@gmail.com" class="text-muted">elijahha12@gmail.com</a>.</div>
      </div>
    </div>
  </div>

  <!-- Add LP Modal -->
  <div class="modal fade" id="addLpModal" tabindex="-1" aria-labelledby="addLpModalLabel" aria-hidden="true">
    <div class="modal-dialog">
      <div class="modal-content">
        <form id="addLpForm">
          <div class="modal-header">
            <h5 class="modal-title" id="addLpModalLabel">카테고리에 새 LP 추가</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="modal-body">
            <input type="hidden" id="modalCategory" name="category">
            <div class="mb-3">
              <label for="lpName" class="form-label">LP 이름</label>
              <input type="text" class="form-control" id="lpName" name="name" required>
            </div>
            <div class="mb-3">
              <label for="lpEngName" class="form-label">영문 이름</label>
              <input type="text" class="form-control" id="lpEngName" name="eng_name">
            </div>
            <div class="mb-3">
              <label for="lpAbbr1" class="form-label">약어1</label>
              <input type="text" class="form-control" id="lpAbbr1" name="abbr1">
            </div>
            <div class="mb-3">
              <label for="lpAbbr2" class="form-label">약어2</label>
              <input type="text" class="form-control" id="lpAbbr2" name="abbr2">
            </div>
          </div>
          <div class="modal-footer">
            <button type="submit" class="btn btn-primary">추가</button>
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">취소</button>
          </div>
        </form>
      </div>
    </div>
  </div>

  <!-- Bootstrap JS for modal -->
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
  <script>
    const categoryToggles = document.querySelectorAll('.category-toggle');
    const lpButtons = document.querySelectorAll('.lp-button');
    const articleInput = document.getElementById('articleSearch');
    const maxToggleCount = 30;
    let selectedLPs = new Set();
    let selectedCategoriesOrder = [];

    // Helpers for safe like button data
    function stripHtml(html) {
      const tmp = document.createElement('div');
      tmp.innerHTML = html || '';
      return (tmp.textContent || tmp.innerText || '').trim();
    }

    function normalizeText(text, maxLen = 200) {
      const collapsed = (text || '').replace(/\s+/g, ' ').trim();
      if (collapsed.length > maxLen) return collapsed.slice(0, maxLen - 1) + '…';
      return collapsed;
    }

    function isValidUrl(maybeUrl) {
      try { new URL(maybeUrl); return true; } catch { return false; }
    }

    function toggleLP(btn) {
      const lpName = btn.textContent.trim();
      if (selectedLPs.has(lpName)) {
        selectedLPs.delete(lpName);
        btn.classList.remove('active');
      } else {
        if (selectedLPs.size >= maxToggleCount) {
          alert("검색 대상이 너무 많습니다. 다른 LP 선택을 해제해주세요.");
          return;
        }
        selectedLPs.add(lpName);
        btn.classList.add('active');
      }
    }

    categoryToggles.forEach(button => {
      button.addEventListener('click', () => {
        const category = button.getAttribute('data-category');
        const willActivate = !button.classList.contains('active');

        if (willActivate) {
          // Compute LPs that would be added for this category
          const toAdd = [];
        document.querySelectorAll('.lp-button').forEach(lpBtn => {
          if (lpBtn.getAttribute('data-keywords').includes(category)) {
              const name = lpBtn.textContent.trim();
              if (!selectedLPs.has(name)) toAdd.push(name);
            }
          });

          if (selectedLPs.size + toAdd.length > maxToggleCount) {
            // Do not activate this category; remove the latest chosen category (this one just clicked)
            // and inform the user gently
            showNotification('최대 30개까지만 선택할 수 있습니다. 방금 선택한 카테고리를 해제했습니다.', 'error');
                  return;
                }

          // Activate category and select its LPs
          button.classList.add('active');
          toAdd.forEach(name => {
            selectedLPs.add(name);
            document.querySelectorAll('.lp-button').forEach(lpBtn => {
              if (lpBtn.textContent.trim() === name) lpBtn.classList.add('active');
            });
          });
          if (!selectedCategoriesOrder.includes(category)) {
            selectedCategoriesOrder.push(category);
              }
            } else {
          // Deactivate: remove LPs within the category
          button.classList.remove('active');
          document.querySelectorAll('.lp-button').forEach(lpBtn => {
            if (lpBtn.getAttribute('data-keywords').includes(category)) {
              const name = lpBtn.textContent.trim();
              if (selectedLPs.has(name)) selectedLPs.delete(name);
              lpBtn.classList.remove('active');
            }
          });
          selectedCategoriesOrder = selectedCategoriesOrder.filter(c => c !== category);
          }
      });
    });

    // Search button click handler
    document.getElementById("searchBtn").addEventListener("click", async function () {
      const selectedArray = Array.from(selectedLPs);
      if (selectedArray.length === 0) {
        showNotification("검색할 LP를 선택해주세요.", "error");
        return;
      }
      
      const keyword = document.getElementById('articleSearch').value.trim();
      
      // Save state
      sessionStorage.setItem("selectedLPs", JSON.stringify(selectedArray));
      sessionStorage.setItem("lpScroll", document.getElementById("lpButtons").scrollTop);

      const activeCategories = [];
      document.querySelectorAll('.category-toggle.active').forEach(btn => {
        activeCategories.push(btn.getAttribute('data-category'));
      });
      sessionStorage.setItem('activeCategories', JSON.stringify(activeCategories));

      document.getElementById("loadingSpinner").style.display = 'block';
      
      try {
        const response = await fetch('/lp_keyword_search', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ selected_lps: selectedArray, keyword: keyword })
        });
        
        const data = await response.json();
        
        if (data.success) {
          updateNewsContainer(data.articles);
          updateHeader(selectedArray, keyword);
          attachLikeButtonListeners();
          showNotification(`${data.articles.length}개의 뉴스를 찾았습니다!`, "success");
        } else {
          showNotification(data.message || '검색에 실패했습니다.', "error");
        }
      } catch (error) {
        console.error('Search error:', error);
        showNotification('검색 중 오류가 발생했습니다.', "error");
      } finally {
        document.getElementById("loadingSpinner").style.display = 'none';
      }
    });

    // Pressing Enter in keyword input triggers search (IME-safe)
    (function attachEnterToSearch() {
      const keywordInput = document.getElementById('articleSearch');
      if (!keywordInput) return;
      keywordInput.addEventListener('keydown', function (e) {
        if (e.isComposing) return; // avoid triggering during IME composition
        if (e.key === 'Enter') {
          e.preventDefault();
          const btn = document.getElementById('searchBtn');
          if (btn) btn.click();
        }
      });
    })();
    
    const PAGE_SIZE = 20;
    let allArticles = [];
    let currentPage = 1;

    function renderPagination(totalPages) {
      const ul = document.getElementById('pagination');
      if (!ul) return;
      ul.innerHTML = '';
      if (totalPages <= 1) return;

      const makeItem = (label, page, disabled = false, active = false, ariaLabel = '') => {
        const li = document.createElement('li');
        li.className = 'page-item' + (disabled ? ' disabled' : '') + (active ? ' active' : '');
        const el = document.createElement('a');
        el.className = 'page-link';
        el.href = '#';
        el.innerHTML = label;
        if (ariaLabel) el.setAttribute('aria-label', ariaLabel);
        if (!disabled && !active) {
          el.addEventListener('click', (e) => { e.preventDefault(); renderPage(page); });
        } else {
          el.addEventListener('click', (e) => e.preventDefault());
        }
        li.appendChild(el);
        return li;
      };

      const total = totalPages;
      ul.appendChild(makeItem('&laquo;', 1, currentPage === 1, false, 'First'));
      ul.appendChild(makeItem('&lsaquo;', Math.max(1, currentPage - 1), currentPage === 1, false, 'Previous'));

      let start = Math.max(1, currentPage - 2);
      let end = Math.min(total, start + 4);
      start = Math.max(1, Math.min(start, end - 4));

      for (let p = start; p <= end; p++) {
        ul.appendChild(makeItem(String(p), p, false, p === currentPage));
      }

      ul.appendChild(makeItem('&rsaquo;', Math.min(total, currentPage + 1), currentPage === total, false, 'Next'));
      ul.appendChild(makeItem('&raquo;', total, currentPage === total, false, 'Last'));
    }

    function renderPage(page) {
      const newsContainer = document.getElementById('newsContainer');
      if (!newsContainer) return;
      const total = allArticles.length;
      const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
      currentPage = Math.min(Math.max(1, page), totalPages);
      newsContainer.innerHTML = '';
      
      const start = (currentPage - 1) * PAGE_SIZE;
      const end = Math.min(start + PAGE_SIZE, total);
      const slice = allArticles.slice(start, end);

      slice.forEach((article, idx) => {
        const globalIndex = start + idx + 1;
        const articleCard = document.createElement('div');
        articleCard.className = 'article-card card fade-in';
        articleCard.style.animationDelay = `${idx * 0.03}s`;
        
        articleCard.innerHTML = `
          <div class="card-body">
            <h5 class="card-title">
              <span class="text-muted me-1">${globalIndex}.</span>
              <a href="${article.link}" target="_blank">${article.title}</a>
            </h5>
            <p class="card-text">${article.description}</p>
            <div class="d-flex justify-content-between align-items-center">
              <small class="text-muted">${article.pubDate}</small>
              <button class="like-btn">❤️</button>
            </div>
          </div>
        `;

        const likeBtn = articleCard.querySelector('.like-btn');
        const safeTitle = normalizeText(article.title_plain ? article.title_plain : stripHtml(article.title));
        const safeLink = isValidUrl(article.link) ? article.link : '#';
        likeBtn.dataset.title = safeTitle;
        likeBtn.dataset.link = safeLink;
        newsContainer.appendChild(articleCard);
      });

      attachLikeButtonListeners();
      renderPagination(totalPages);
    }

    function updateNewsContainer(articles) {
      allArticles = Array.isArray(articles) ? articles : [];
      renderPage(1);
    }
    
    function updateHeader(selectedLPs, keyword) {
      const header = document.querySelector('.header h3');
      if (header) {
        const searchText = keyword ? 
          `선택된 LP + 키워드 검색: ${selectedLPs.join(', ')} + "${keyword}"` :
          `선택된 LP 뉴스 검색: ${selectedLPs.join(', ')}`;
        header.textContent = searchText;
      }
    }

    window.addEventListener("pageshow", function () {
      document.getElementById("loadingSpinner").style.display = 'none';
    });

    // Add smooth scrolling and animations
    document.addEventListener('DOMContentLoaded', function() {
      // Add hover effects to LP buttons
      document.querySelectorAll('.lp-button').forEach(btn => {
        btn.addEventListener('mouseenter', function() {
          this.style.transform = 'translateY(-2px) scale(1.02)';
        });
        btn.addEventListener('mouseleave', function() {
          this.style.transform = 'translateY(0) scale(1)';
      });
    });

      // Add smooth transitions to category toggles
      document.querySelectorAll('.category-toggle').forEach(toggle => {
        toggle.addEventListener('click', function() {
          this.style.transform = 'scale(0.95)';
          setTimeout(() => {
            this.style.transform = 'scale(1)';
          }, 150);
        });
      });

      // Add loading animation to search button
      const searchBtn = document.getElementById('searchBtn');
      if (searchBtn) {
        searchBtn.addEventListener('click', function() {
          this.style.transform = 'scale(0.95)';
          setTimeout(() => {
            this.style.transform = 'scale(1)';
          }, 200);
        });
      }
    });


    
    
    function getLikeKey(title, link) {
      if (link && link !== '#') return link;
      return 'ttl:' + (title || '').toLowerCase();
    }

    function isArticleLiked(title, link) {
      const liked = JSON.parse(localStorage.getItem("likedArticles") || "[]");
      const key = getLikeKey(title, link);
      return liked.some(a => getLikeKey(a.title, a.link) === key);
    }

    function toggleLike(title, link) {
      const key = getLikeKey(title, link);
      const liked = JSON.parse(localStorage.getItem("likedArticles") || "[]");
      const idx = liked.findIndex(a => getLikeKey(a.title, a.link) === key);
      if (idx === -1) {
        liked.push({ title: title || 'Untitled', link: link || '#' });
      } else {
        liked.splice(idx, 1);
      }
      localStorage.setItem("likedArticles", JSON.stringify(liked));
      loadLikedArticles();
    }

    // Delegated like handling for dynamically rendered cards
    function attachLikeButtonListeners() {
      const container = document.getElementById('newsContainer');
      if (!container) return;
      container.removeEventListener('click', __likeDelegator, true);
      container.addEventListener('click', __likeDelegator, true);
      // initialize buttons to current like state
      container.querySelectorAll('.like-btn').forEach(btn => {
        const t = (btn.dataset.title || '').toString();
        const l = (btn.dataset.link || '').toString();
        if (isArticleLiked(t, l)) {
          btn.classList.add('btn-success');
          btn.textContent = '❤️ 찜됨';
        } else {
          btn.classList.remove('btn-success');
          btn.textContent = '❤️';
        }
      });
    }

    function __likeDelegator(e) {
      const btn = e.target.closest('.like-btn');
      if (!btn) return;
      e.preventDefault();
      const title = (btn.dataset.title || '').toString();
      const link = (btn.dataset.link || '').toString();
      toggleLike(title, link);
      if (isArticleLiked(title, link)) {
        btn.classList.add('btn-success');
        btn.textContent = '❤️ 찜됨';
      } else {
        btn.classList.remove('btn-success');
        btn.textContent = '❤️';
      }
    }


    function showNotification(message, type = 'info') {
      const notification = document.createElement('div');
      notification.className = `notification notification-${type} slide-in`;
      notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'success' ? 'var(--success-color)' : type === 'error' ? 'var(--danger-color)' : 'var(--primary-color)'};
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 12px;
        box-shadow: var(--shadow-lg);
        z-index: 10000;
        font-weight: 500;
        max-width: 300px;
        backdrop-filter: blur(10px);
      `;
      notification.textContent = message;
      document.body.appendChild(notification);
      
      setTimeout(() => {
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => {
          document.body.removeChild(notification);
        }, 300);
      }, 3000);
    }

    function clearSearch() {
      document.getElementById('articleSearch').value = '';
      selectedLPs.clear();
      document.querySelectorAll('.lp-button.active, .category-toggle.active').forEach(btn => {
        btn.classList.remove('active');
      });
      // Clear persisted UI state so it doesn't restore on reload
      try {
        sessionStorage.removeItem('selectedLPs');
        sessionStorage.removeItem('activeCategories');
        sessionStorage.removeItem('lpScroll');
      } catch (e) {}
      showNotification('검색이 초기화되었습니다.', 'info');
      location.reload();
    }

    function clearLikedArticles() {
      if (confirm("정말 모든 찜한 뉴스를 삭제하시겠습니까?")) {
        localStorage.removeItem('likedArticles');
        loadLikedArticles();
        document.querySelectorAll('.like-btn').forEach(btn => {
          btn.classList.remove('btn-success');
          btn.classList.add('btn-outline-danger');
          btn.textContent = '❤️';
        });
      }
    }

    function loadLikedArticles() {
      const likedList = document.getElementById("likedList");
      likedList.innerHTML = "";
      const likedArticles = JSON.parse(localStorage.getItem("likedArticles") || "[]");

      likedArticles.forEach(article => {
        const li = document.createElement("li");
        li.className = "list-group-item d-flex justify-content-between align-items-center";

        const link = document.createElement("a");
        link.href = article.link;
        link.target = "_blank";
        link.textContent = article.title;

        const deleteBtn = document.createElement("button");
        deleteBtn.className = "btn btn-sm btn-outline-danger";
        deleteBtn.textContent = "X";
        deleteBtn.onclick = function () {
          const updated = likedArticles.filter(a => a.link !== article.link);
          localStorage.setItem("likedArticles", JSON.stringify(updated));
          loadLikedArticles();

          // ✅ Reset the like button in the feed
          const likeBtnInFeed = document.querySelector(`.like-btn[data-link="${CSS.escape(article.link)}"]`);
          if (likeBtnInFeed) {
            likeBtnInFeed.classList.remove("btn-success");
            likeBtnInFeed.classList.add("btn-outline-danger");
            likeBtnInFeed.textContent = "❤️";
          }
        };

        li.appendChild(link);
        li.appendChild(deleteBtn);
        likedList.appendChild(li);
      });
    }

    function openAddLpModal(category) {
      document.getElementById('modalCategory').value = category;
      const modal = new bootstrap.Modal(document.getElementById('addLpModal'));
      modal.show();
    }

    document.getElementById('addLpForm').addEventListener('submit', async function (e) {
      e.preventDefault();

      const name = document.getElementById('lpName').value.trim();
      const eng_name = document.getElementById('lpEngName').value.trim();
      const abbr1 = document.getElementById('lpAbbr1').value.trim();
      const abbr2 = document.getElementById('lpAbbr2').value.trim();
      const category = document.getElementById('modalCategory').value;

      if (!name || !category) return alert("LP 이름과 카테고리는 필수입니다.");

      const newLp = { name, eng_name, abbr1, abbr2, category };

      try {
        const res = await fetch('/add_lp', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(newLp)
        });
        const data = await res.json();
        if (!res.ok || !data.success) {
          alert(data.message || '추가에 실패했습니다.');
          return;
        }
        // Clear any legacy localStorage cache and reload to fetch server-rendered list
        localStorage.removeItem('userAddedLPs');
        location.reload();
      } catch (err) {
        alert('네트워크 오류로 추가하지 못했습니다.');
      }
    });

    function renderUserAddedLPs() {
      const storedLps = JSON.parse(localStorage.getItem('userAddedLPs') || '[]');
      const lpList = document.getElementById('lpButtons');
      const existingCategories = Array.from(lpList.querySelectorAll('.category-label')).map(el => el.textContent.trim());

      storedLps.forEach(lp => {
        if ([...lpList.querySelectorAll('.lp-button')].some(btn => btn.textContent.trim() === lp.name)) return;

        if (!existingCategories.includes(lp.category)) {
          const catDiv = document.createElement('div');
          catDiv.className = 'category-label';
          catDiv.innerHTML = `${lp.category}
            <button class="btn btn-secondary btn-sm ms-2" onclick="openAddLpModal('${lp.category}')">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-plus" viewBox="0 0 16 16">
                <path d="M8 4a.5.5 0 0 1 .5.5v3h3a.5.5 0 0 1 0 1h-3v3a.5.5 0 0 1-1 0v-3h-3a.5.5 0 0 1 0-1h3v-3A.5.5 0 0 1 8 4"/>
              </svg>
            </button>`;
          lpList.appendChild(catDiv);
          existingCategories.push(lp.category);
        }

        const btn = document.createElement('button');
        btn.className = 'btn btn-outline-secondary lp-button';
        btn.textContent = lp.name;
        btn.setAttribute('data-keywords', `${lp.name} ${lp.eng_name} ${lp.abbr1} ${lp.abbr2} ${lp.category}`);
        btn.onclick = function () {
          toggleLP(btn);
        };
        lpList.appendChild(btn);
      });
    }

    window.addEventListener('DOMContentLoaded', () => {
      const stored = JSON.parse(sessionStorage.getItem('selectedLPs') || '[]');
      stored.forEach(name => {
        document.querySelectorAll('.lp-button').forEach(btn => {
          if (btn.textContent.trim() === name) {
            selectedLPs.add(name);
            btn.classList.add('active');
          }
        });
      });

      const savedScroll = sessionStorage.getItem('lpScroll');
      if (savedScroll !== null) {
        document.getElementById('lpButtons').scrollTop = parseInt(savedScroll, 10);
      }

      const storedCategories = JSON.parse(sessionStorage.getItem("activeCategories") || "[]");
      storedCategories.forEach(category => {
        document.querySelectorAll('.category-toggle').forEach(btn => {
          if (btn.getAttribute('data-category') === category) {
            btn.classList.add('active');
          }
        });
      });

      loadLikedArticles();
      // Ensure no legacy client-only LPs remain
      localStorage.removeItem('userAddedLPs');

      const editBtn = document.getElementById('editLpBtn');
      const lpButtonsContainer = document.getElementById('lpButtons');
      if (editBtn && lpButtonsContainer) {
        editBtn.addEventListener('click', () => {
          lpButtonsContainer.classList.toggle('edit-mode');
          editBtn.textContent = lpButtonsContainer.classList.contains('edit-mode') ? '완료' : '편집';
        });
      }

      if (lpButtonsContainer) {
        // Category-level reset buttons
        document.querySelectorAll('.category-reset-btn').forEach(btn => {
          btn.addEventListener('click', () => {
            const cat = btn.getAttribute('data-category');
            if (!cat) return;
            // Unselect all LPs in this category
            document.querySelectorAll(`.lp-button[data-category="${cat}"]`).forEach(lpBtn => {
              const name = lpBtn.textContent.trim();
              if (selectedLPs.has(name)) {
                selectedLPs.delete(name);
              }
              lpBtn.classList.remove('active');
            });
            // Also unmark category toggle if present
            document.querySelectorAll('.category-toggle').forEach(t => {
              if (t.getAttribute('data-category') === cat) {
                t.classList.remove('active');
              }
            });
            showNotification(`${cat} 카테고리 선택이 초기화되었습니다.`, 'info');
          });
        });

        // LP 선택 초기화 버튼
        const resetBtn = document.getElementById('resetLpSelectionBtn');
        if (resetBtn) {
          resetBtn.addEventListener('click', () => {
            selectedLPs.clear();
            document.querySelectorAll('.lp-button.active').forEach(b => b.classList.remove('active'));
            // Also clear active category toggles to avoid auto-selects
            document.querySelectorAll('.category-toggle.active').forEach(btn => btn.classList.remove('active'));
            // Clear persisted selection state immediately
            try {
              sessionStorage.removeItem('selectedLPs');
              sessionStorage.removeItem('activeCategories');
            } catch (e) {}
            showNotification('LP 선택이 초기화되었습니다.', 'info');
          });
        }

        lpButtonsContainer.addEventListener('click', async (ev) => {
          const clicked = ev.target;
          const btn = clicked && clicked.classList.contains('lp-delete-btn')
            ? clicked
            : (clicked && clicked.closest ? clicked.closest('.lp-delete-btn') : null);
          if (!btn || !lpButtonsContainer.contains(btn)) return;
          if (btn.getAttribute('data-deletable') !== 'true') return;
          btn.disabled = true; // prevent double-clicks
          const name = btn.getAttribute('data-name');
          const category = btn.getAttribute('data-category');
          if (!name || !category) { btn.disabled = false; return; }
          if (!confirm(`${name} (${category}) 항목을 삭제하시겠습니까? 정말로 진행하시겠습니까?`)) { btn.disabled = false; return; }
          try {
            const res = await fetch('/delete_lp', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ name, category })
            });
            const data = await res.json().catch(() => ({}));
            if (!res.ok || !data.success) {
              alert(data.message || '삭제에 실패했습니다.');
              btn.disabled = false;
              return;
            }
            location.reload();
          } catch (e) {
            alert('네트워크 오류로 삭제하지 못했습니다.');
            btn.disabled = false;
          }
        });
      }

      // Attach like button listeners for initial articles
      attachLikeButtonListeners();
    });

    window.addEventListener("scroll", () => {
      const scrollY = window.scrollY;
      const minTop = 5;
      const maxTop = 60;
      const newTop = Math.max(minTop, maxTop - scrollY);
      document.documentElement.style.setProperty("--lp-top-offset", `${newTop}px`);
    });

    // LP list text filter
    (function setupLpSearch() {
      const input = document.getElementById('lpSearch');
      if (!input) return;
      function updateVisibility() {
        const query = input.value.trim().toLowerCase();
        const tokens = query.split(/\s+/).filter(Boolean);
        document.querySelectorAll('.lp-item').forEach(item => {
          const btn = item.querySelector('.lp-button');
          const haystack = ((btn && btn.getAttribute('data-keywords')) || '').toLowerCase();
          const matches = tokens.every(t => haystack.includes(t));
          item.style.display = matches ? '' : 'none';
        });
        document.querySelectorAll('.category-label').forEach(label => {
          const cat = label.getAttribute('data-category');
          if (!cat) { label.style.display = ''; return; }
          const anyVisible = Array.from(document.querySelectorAll(`.lp-item .lp-button[data-category="${cat}"]`))
            .some(btn => {
              const li = btn.closest('.lp-item');
              return li && li.style.display !== 'none';
            });
          label.style.display = anyVisible ? '' : 'none';
        });
      }
      input.addEventListener('input', updateVisibility);
      updateVisibility();
    })();
  

    // --- Global delegated listeners for like/save and saved-remove ---
    document.addEventListener('click', (e) => {
      const likeBtn = e.target.closest('[data-role="like-toggle"]');
      if (likeBtn) {
        const key = likeBtn.getAttribute('data-save-key');
        const card = likeBtn.closest('.news-card');
        const title = card?.querySelector('.news-title')?.textContent?.trim() || likeBtn.getAttribute('data-title') || '';
        const link = card?.getAttribute('data-link') || likeBtn.getAttribute('data-link') || '';
        const list = getSaved();
        const idx = list.findIndex(x => x.key === key);
        if (idx >= 0) {
          list.splice(idx, 1);
          setSaved(list);
          updateLikeBtnEl(likeBtn, false);
        } else {
          list.push({ key, title, link });
          setSaved(list);
          updateLikeBtnEl(likeBtn, true);
        }
        try { renderSavedList && renderSavedList(); } catch {}
        return;
      }
      const rmBtn = e.target.closest('[data-role="saved-remove"]');
      if (rmBtn) {
        const key = rmBtn.getAttribute('data-save-key');
        const next = getSaved().filter(x => x.key !== key);
        setSaved(next);
        try { renderSavedList && renderSavedList(); } catch {}
        const originalLike = findLikeBtnByKey(key);
        if (originalLike) updateLikeBtnEl(originalLike, false);
        return;
      }
    });

    function renderSavedList() {
      const el = document.getElementById('savedList');
      if (!el) return;
      const saved = getSaved();
      if (saved.length === 0) {
        el.innerHTML = '<div class="saved-empty">저장한 뉴스가 없습니다.</div>';
        return;
      }
      el.innerHTML = saved.map(s => `
        <div class="saved-row">
          <a class="saved-link" href="${s.link || '#'}" target="_blank" rel="noreferrer noopener">${s.title}</a>
          <button class="saved-remove-btn" data-role="saved-remove" data-save-key="${s.key}">삭제</button>
        </div>
      `).join('');
    }
    

    // Sync like buttons with saved state on any content refresh
    function syncLikeButtonsWithSaved() {
      const savedArr = getSaved();
      const savedSet = new Set(savedArr.map(s => s.key));
      document.querySelectorAll('[data-role="like-toggle"]').forEach(btn => {
        const key = btn.getAttribute('data-save-key');
        updateLikeBtnEl(btn, savedSet.has(key));
      });
    }
    // Run sync after DOM ready and after any major renders
    document.addEventListener('DOMContentLoaded', () => { try { syncLikeButtonsWithSaved(); } catch {} });
</script>
</body>
</html>
'''

def get_naver_news(query):
  print(f"get_naver_news called with: {query}")
  url = "https://openapi.naver.com/v1/search/news.json"
  headers = {
    "X-Naver-Client-Id": NAVER_CLIENT_ID,
    "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
  }
  params = {
    "query": query,
    "display": 50,
    "sort": "date",
  }

  try:
    response = requests.get(url, headers=headers, params=params, verify=False)  
    response.raise_for_status()
    data = response.json()
    items = data.get('items', [])
    
    # Debug: Print the first item to see available fields
    if items:
      print(f"Sample article fields: {list(items[0].keys())}")
    
    return items
  except Exception as e:
    print(f"[ERROR] Failed to fetch Naver News: {e}")
    return []
      
@app.route('/kpasset')
def kpasset():
  return render_template('iframe.html', iframe_url='https://www.kpasset.go.kr')

@app.route('/kofia')
def kofia():
  return render_template('iframe.html', iframe_url='https://www.kofia.or.kr/brd/m_212/list.do')

LP_LIST_FILE = 'lp_list.json'  # legacy; not used when registry persistence is enabled

# Embedded default LP list so no external file is required at deployment
DEFAULT_LP_LIST = [
  {"name": "사학연금", "eng_name": "Teachers Pension", "abbr1": "TP", "abbr2": "KTP", "category": "연기금"},
  {"name": "공무원연금", "eng_name": "Government Employees Pension Service", "abbr1": "GEPS", "category": "연기금"},
  {"name": "미래에셋증권 OCIO 고용기금 EIF", "eng_name": "Mirae Asset Securities Employment Insurance Fund", "abbr1": "Mirae Asset Securities EIF", "category": "연기금"},
  {"name": "미래에셋자산운용 국토부 주택도시기금 MOEL", "eng_name": "Mirae Asset AM Ministry of Employment and Labor", "abbr1": "Mirae Asset AM MOEL", "category": "연기금"},
  {"name": "NH투자증권 국토부 주택도시기금 MOEL", "eng_name": "NH Securities Ministry of Employment and Labor", "abbr1": "NH Securities MOEL", "category": "연기금"},
  {"name": "우정사업본부", "eng_name": "K-Post Insurance", "abbr1": "우체국 보험", "category": "연기금"},
  {"name": "한국교직원공제회", "eng_name": "Korea teachers' Credit Union", "abbr1": "KTCU", "category": "공제회/조합"},
  {"name": "전문건설공제회", "eng_name": "Korea Finance for Construction", "abbr1": "K-FINCO", "category": "공제회/조합"},
  {"name": "건설근로자공제회", "eng_name": "Construction Workers Mutual Aid Association", "abbr1": "CWMA", "category": "공제회/조합"},
  {"name": "행정공제회", "eng_name": "Public Officials Benefit Association", "abbr1": "POBA", "category": "공제회/조합"},
  {"name": "경찰공제회", "eng_name": "The Police Mutual Aid Association", "abbr1": "PMAA", "category": "공제회/조합"},
  {"name": "과학기술인공제회", "eng_name": "Korea Scientists & Engineers Mutual Aid Association", "abbr1": "SEMA", "category": "공제회/조합"},
  {"name": "군인공제회", "eng_name": "Military Mutual Aid Association", "abbr1": "MMAA", "category": "공제회/조합"},
  {"name": "엔지니어링공제조합", "eng_name": "Engineering Guarantee Insurance", "abbr1": "EGI", "category": "공제회/조합"},
  {"name": "소방공제회", "eng_name": "Korea Fire Officials Credit Union", "abbr1": "FOCU", "category": "공제회/조합"},
  {"name": "한국지방재정공제회", "eng_name": "Local Finance Association", "abbr1": "LOFA", "category": "공제회/조합"},
  {"name": "기계설비건설조합", "eng_name": "", "abbr1": "", "category": "공제회/조합"},
  {"name": "새마을금고복지회", "eng_name": "", "abbr1": "", "category": "공제회/조합"},
  {"name": "수협중앙회", "eng_name": "National Federation of Fisheries Cooperatives", "abbr1": "NFFC", "category": "중앙회"},
  {"name": "농협중앙회", "eng_name": "National Agricultural Cooperative Federation", "abbr1": "NACF", "category": "중앙회"},
  {"name": "신협중앙회", "eng_name": "National Credit Union Federation of Korea", "abbr1": "CU", "category": "중앙회"},
  {"name": "중소기업중앙회", "eng_name": "Korea Federation of Small and Medium Business", "abbr1": "K-BIZ", "category": "중앙회"},
  {"name": "산림조합중앙회", "eng_name": "National Foresty Cooperatives Federation", "abbr1": "NFCF", "category": "중앙회"},
  {"name": "코리안리", "eng_name": "KoreanRe", "abbr1": "", "category": "보험사"},
  {"name": "서울보증보험", "eng_name": "Seoul Guarantee Insurance", "abbr1": "SGIC", "category": "보험사"},
  {"name": "NH생명", "eng_name": "NH Life", "abbr1": "", "category": "보험사"},
  {"name": "미래에셋생명", "eng_name": "Mirae Asset Life", "abbr1": "", "category": "보험사"},
  {"name": "라이나생명", "eng_name": "LINA Korea", "abbr1": "", "category": "보험사"},
  {"name": "KDB생명", "eng_name": "KDB Life", "abbr1": "", "category": "보험사"},
  {"name": "교보생명", "eng_name": "Kyobo Life", "abbr1": "", "category": "보험사"},
  {"name": "하나생명", "eng_name": "Hana Life", "abbr1": "", "category": "보험사"},
  {"name": "IM라이프", "eng_name": "IM Life(DGB Life)", "abbr1": "", "category": "보험사"},
  {"name": "한화생명", "eng_name": "Hanwha Life", "abbr1": "", "category": "보험사"},
  {"name": "푸본현대생명", "eng_name": "Fubon Hyundai Life", "abbr1": "", "category": "보험사"},
  {"name": "신한라이프", "eng_name": "Shinhan Life", "abbr1": "", "category": "보험사"},
  {"name": "삼성생명", "eng_name": "Samsung Life", "abbr1": "", "category": "보험사"},
  {"name": "동양생명", "eng_name": "Tong Yang Life", "abbr1": "", "category": "보험사"},
  {"name": "흥국생명", "eng_name": "Heungkuk Life", "abbr1": "", "category": "보험사"},
  {"name": "NH손보", "eng_name": "NH Property & Casualty Insurance", "abbr1": "", "category": "보험사"},
  {"name": "한화손보", "eng_name": "Hanwha General Insurance", "abbr1": "", "category": "보험사"},
  {"name": "MG손보", "eng_name": "MG Insurance", "abbr1": "", "category": "보험사"},
  {"name": "DB손보", "eng_name": "DB Insurance", "abbr1": "DB LDI", "category": "보험사"},
  {"name": "DB생명", "eng_name": "DB Life", "abbr1": "DB LDI", "category": "보험사"},
  {"name": "농협손보", "eng_name": "NH Property & Casualty Insurance", "abbr1": "", "category": "보험사"},
  {"name": "롯데손보", "eng_name": "Lotte Non-Life Insurance", "abbr1": "", "category": "보험사"},
  {"name": "삼성화재", "eng_name": "Smasung Fire & Marine Insurance", "abbr1": "", "category": "보험사"},
  {"name": "흥국화재", "eng_name": "Heungkuk fire & Marine Insurance", "abbr1": "", "category": "보험사"},
  {"name": "메리츠화재", "eng_name": "Meritz Fire & Fire Insurance", "abbr1": "", "category": "보험사"},
  {"name": "현대해상", "eng_name": "Hyundai Marine & Fire Insurance", "abbr1": "", "category": "보험사"},
  {"name": "IBK연금보험", "eng_name": "IBK Insurance", "abbr1": "", "category": "보험사"},
  {"name": "하나손보", "eng_name": "Hana Insurance", "abbr1": "", "category": "보험사"},
  {"name": "ABL생명", "eng_name": "ABL Life Insurance", "abbr1": "", "category": "보험사"},
  {"name": "프리드라이프", "eng_name": "Preedlife", "abbr1": "", "category": "보험사"},
  {"name": "우리은행", "eng_name": "Woori Bank", "abbr1": "", "category": "은행"},
  {"name": "하나은행", "eng_name": "KEB Hana Bank", "abbr1": "", "category": "은행"},
  {"name": "신한은행", "eng_name": "Shinhan Bank", "abbr1": "", "category": "은행"},
  {"name": "DGB은행", "eng_name": "DaeGue Bank(IM Bank)", "abbr1": "", "category": "은행"},
  {"name": "IBK 기업은행", "eng_name": "Industrial Bank of Korea", "abbr1": "IBK", "category": "은행"},
  {"name": "KB은행", "eng_name": "KB Bank", "abbr1": "", "category": "은행"},
  {"name": "NH농협은행", "eng_name": "NH Bank", "abbr1": "", "category": "은행"},
  {"name": "KDB 은행", "eng_name": "Korea Development Bank", "abbr1": "KDB", "category": "은행"},
  {"name": "MG새마을금고", "eng_name": "Korean Federation of Community Credit Cooperatives", "abbr1": "KFCC", "category": "은행"},
  {"name": "삼성증권", "eng_name": "Samsung Securities", "abbr1": "", "category": "증권사"},
  {"name": "NH투자증권", "eng_name": "NH Investment & Securities", "abbr1": "", "category": "증권사"},
  {"name": "신한투자증권", "eng_name": "Shinhan Securities", "abbr1": "", "category": "증권사"},
  {"name": "미래에셋증권", "eng_name": "Mirae Asset Securities", "abbr1": "", "category": "증권사"},
  {"name": "하나증권", "eng_name": "Hana Financial Investment", "abbr1": "", "category": "증권사"},
  {"name": "한국투자증권", "eng_name": "Korea Investment & Securities", "abbr1": "KIS", "category": "증권사"},
  {"name": "KB증권 WM상품부", "eng_name": "KB Securities Wealth Management Business Uni", "abbr1": "", "category": "증권사"},
  {"name": "KB증권", "eng_name": "KB Securities", "abbr1": "", "category": "증권사"},
  {"name": "미래에셋자산운용", "eng_name": "Mirae Asset Global Investments", "abbr1": "", "category": "운용사"},
  {"name": "삼성자산운용", "eng_name": "Samsung Asset Management", "abbr1": "", "category": "운용사"},
  {"name": "신한자산운용", "eng_name": "Shinhan Asset Management", "abbr1": "", "category": "운용사"},
  {"name": "KB자산운용", "eng_name": "KB Asset Management", "abbr1": "", "category": "운용사"},
  {"name": "DB자산운용", "eng_name": "Dongbu Asset Management", "abbr1": "", "category": "운용사"},
  {"name": "삼성SRA자산운용", "eng_name": "Samsung SRA Asset Management", "abbr1": "", "category": "운용사"},
  {"name": "파인스트리트 자산운용", "eng_name": "PineStreet Asset Management", "abbr1": "", "category": "운용사"},
  {"name": "한국투자신탁운용", "eng_name": "Korea Investment Management", "abbr1": "", "category": "운용사"},
  {"name": "NH아문디 자산운용", "eng_name": "", "abbr1": "", "category": "운용사"},
  {"name": "키움자산운용", "eng_name": "", "abbr1": "", "category": "운용사"},
  {"name": "이지스자산운용", "eng_name": "", "abbr1": "", "category": "운용사"},
  {"name": "보고자산운용", "eng_name": "", "abbr1": "", "category": "운용사"},
  {"name": "신한캐피탈", "eng_name": "Shinhan Capital", "abbr1": "", "category": "캐피탈"},
  {"name": "IBK캐피탈", "eng_name": "IBK Capital", "abbr1": "", "category": "캐피탈"},
  {"name": "현대커머셜", "eng_name": "Hyundai Commercial Inc", "abbr1": "", "category": "캐피탈"},
  {"name": "현대카드", "eng_name": "Hyundai Card", "abbr1": "", "category": "캐피탈"},
  {"name": "NH캐피탈", "eng_name": "NongHyup Capital", "abbr1": "", "category": "캐피탈"},
  {"name": "KB캐피탈", "eng_name": "KB Capital", "abbr1": "", "category": "캐피탈"},
  {"name": "성담", "eng_name": "Sungdam", "abbr1": "", "category": "기타"},
  {"name": "KT&G", "eng_name": "Korea Tomorrow & Global Corporation", "abbr1": "KT&G", "category": "기타"},
  {"name": "한국벤처투자", "eng_name": "", "abbr1": "", "category": "기타"},
  {"name": "Company H", "eng_name": "Company H", "abbr1": "", "category": "기타"},
  {"name": "TCK", "eng_name": "Topor and Korea Asset Management", "abbr1": "TCK", "category": "기타"},
  {"name": "교원인베스트", "eng_name": "Kyowon Invest", "abbr1": "", "category": "기타"},
  {"name": "포스텍 재단", "eng_name": "", "abbr1": "", "category": "기타"}
]

# Registry persistence helpers (Windows)
REG_PATH = r"Software\\NewsScraper"
REG_VALUE = "lp_list_json"

def _read_lp_list_from_registry():
    if not HAS_WINREG:
        return None
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH)
        value, _ = winreg.QueryValueEx(key, REG_VALUE)
        winreg.CloseKey(key)
        return json.loads(value)
    except Exception:
        return None

def _write_lp_list_to_registry(items: list) -> bool:
    if not HAS_WINREG:
        return False
    try:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_PATH)
        winreg.SetValueEx(key, REG_VALUE, 0, winreg.REG_SZ, json.dumps(items, ensure_ascii=False))
        winreg.CloseKey(key)
        return True
    except Exception:
        return False

def _sanitize_text(value):
    if value is None:
        return ''
    if not isinstance(value, str):
        return str(value)
    return value.strip()


def sanitize_lp_entry(entry: dict) -> dict:
    return {
        'name': _sanitize_text(entry.get('name', '')),
        'eng_name': _sanitize_text(entry.get('eng_name', '')),
        'abbr1': _sanitize_text(entry.get('abbr1', '')),
        'abbr2': _sanitize_text(entry.get('abbr2', '')),
        'category': _sanitize_text(entry.get('category', '')),
    }


def load_lp_list() -> list:
    # Prefer registry persistence; fallback to embedded defaults
    raw = _read_lp_list_from_registry()
    if not isinstance(raw, list):
        raw = DEFAULT_LP_LIST

    sanitized = [sanitize_lp_entry(item) for item in raw if isinstance(item, dict)]
    # Deduplicate by (name, category) preserving first occurrence
    seen = set()
    unique = []
    for item in sanitized:
        key = (item.get('name', ''), item.get('category', ''))
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def save_lp_list(items: list) -> None:
    # Persist to Windows registry; ignore failures silently
    try:
        _write_lp_list_to_registry(items)
    except Exception:
        pass

def clean_html_content(text, keywords=None, lp_names=None):
    """Clean HTML content by removing tags and unescaping entities, then highlight keywords and LP names"""
    if not text:
        return ""
    
    # First unescape HTML entities
    text = unescape(text)
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Clean up extra whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    # Highlight keywords and LP names if provided
    if keywords or lp_names:
        # Combine all terms to highlight
        terms_to_highlight = []
        if keywords:
            terms_to_highlight.extend(keywords.split())
        if lp_names:
            terms_to_highlight.extend(lp_names)
        
        # Sort by length (longer terms first) to avoid partial matches
        terms_to_highlight.sort(key=len, reverse=True)
        
        # Highlight each term
        for term in terms_to_highlight:
            if term.strip():  # Skip empty terms
                # Use case-insensitive replacement
                pattern = re.compile(re.escape(term), re.IGNORECASE)
                text = pattern.sub(f'<strong>{term}</strong>', text)
    
    return text

def extract_title_from_description(description):
    """Extract a title from the description content"""
    if not description:
        return "No Title"
    
    # Clean HTML tags first
    clean_desc = re.sub(r'<[^>]+>', '', description)
    clean_desc = clean_desc.replace('&quot;', '"').replace('&amp;', '&')
    
    # Take first 100 characters as title
    title = clean_desc[:100].strip()
    if len(clean_desc) > 100:
        title += "..."
    
    return title

@app.route("/", methods=["GET", "POST"])
def index():
  # Load, sanitize, deduplicate, then sort for stable grouping
  lp_list = load_lp_list()

  def category_sort_key(item):
      category = item.get('category', '')
      # Treat any whitespace-variant of '기타' as ETC
      is_etc = 1 if category.strip() == '기타' else 0
      return (is_etc, category, item.get('name', ''))

  lp_list = sorted(lp_list, key=category_sort_key)

  return render_template_string(TEMPLATE,
    LP_LIST=lp_list,
    articles=[],
    selected=""
  )



def search_articles(selected_lps, keyword=''):
    """Helper function to search articles for selected LPs with optional keyword"""
    if not selected_lps:
        return []
    
    combined_articles = []
    for lp_name in selected_lps:
      search_query = f"{lp_name} {keyword}".strip()
      results = get_naver_news(search_query)
      combined_articles.extend(results)
      time.sleep(0.3)  # Rate limiting

    # Remove duplicates and clean HTML content
    seen = set()
    unique_articles = []
    for article in combined_articles:
      # Use API-provided title; clean and highlight later for display
      key = (article.get("title", ""), article.get("link", ""))
      if key not in seen:
        seen.add(key)
        # Prepare plain text (no highlight) and highlighted variants
        plain_title = clean_html_content(article.get('title', ''))
        plain_description = clean_html_content(article.get('description', ''))
        highlighted_title = clean_html_content(article.get('title', ''), keyword, selected_lps)
        highlighted_description = clean_html_content(article.get('description', ''), keyword, selected_lps)

            # Store both plain and highlighted for safe UI usage
        article['title_plain'] = plain_title
        article['description_plain'] = plain_description
        article['title'] = highlighted_title
        article['description'] = highlighted_description
        unique_articles.append(article)
    
    # Sort by publication date (newest first)
    from email.utils import parsedate_to_datetime
    def safe_pub_date(article):
      try:
        return parsedate_to_datetime(article.get("pubDate", ""))
      except:
        return datetime.min

    unique_articles.sort(key=safe_pub_date, reverse=True)
    return unique_articles

@app.route('/lp_keyword_search', methods=['POST'])
def lp_keyword_search():
    """Handle LP + keyword search requests from frontend"""
    data = request.get_json()
    selected_lps = data.get('selected_lps', [])
    keyword = data.get('keyword', '').strip()
    
    if not selected_lps:
        return jsonify({'success': False, 'message': '검색할 LP를 선택해주세요.'})
    
    try:
        articles = search_articles(selected_lps, keyword)
        

        
        return jsonify({
            'success': True,
            'articles': articles,
            'selected_lps': selected_lps,
            'keyword': keyword
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'검색 중 오류가 발생했습니다: {str(e)}'})

@app.route('/add_lp', methods=['POST'])
def add_lp():
    new_lp = request.json or {}
    new_lp = sanitize_lp_entry(new_lp)
    if not new_lp.get('name') or not new_lp.get('category'):
        return jsonify({'success': False, 'message': 'Invalid data'}), 400

    current = load_lp_list()

    if any(lp.get('name') == new_lp.get('name') and lp.get('category') == new_lp.get('category') for lp in current):
        return jsonify({'success': False, 'message': '이미 존재하는 LP입니다.'}), 409

    current.append(new_lp)
    save_lp_list(current)

    return jsonify({'success': True})

@app.route('/delete_lp', methods=['POST'])
def delete_lp():
    payload = request.json or {}
    name = _sanitize_text(payload.get('name'))
    category = _sanitize_text(payload.get('category'))
    if not name or not category:
        return jsonify({'success': False, 'message': 'Invalid data'}), 400

    current = load_lp_list()

    new_current = [lp for lp in current if not (lp.get('name') == name and lp.get('category') == category)]
    if len(new_current) == len(current):
        return jsonify({'success': False, 'message': '대상이 존재하지 않습니다.'}), 404

    save_lp_list(new_current)

    return jsonify({'success': True})
