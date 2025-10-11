import os
import tempfile
import re
from flask import Flask, render_template_string, request, jsonify, session, send_file
import requests
import json
import uuid
from datetime import datetime
from flask_cors import CORS
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np

app = Flask(__name__)
app.secret_key = 'mata_tutoring_secret_key_2024'
CORS(app)  # Enable CORS for frontend-backend communication

# Global conversation storage
conversations = {}

# Multiple API endpoints untuk fallback
API_CONFIGS = {
    'claude': {
        'url': 'https://api.anthropic.com/v1/messages',
        'models': ['claude-3-5-sonnet-20241022', 'claude-3-sonnet-20240229', 'claude-3-haiku-20240307'],
        'headers_template': {
            'Content-Type': 'application/json',
            'anthropic-version': '2023-06-01'
        }
    },
    'openai': {
        'url': 'https://api.openai.com/v1/chat/completions',
        'models': ['gpt-4o-mini', 'gpt-3.5-turbo'],
        'headers_template': {
            'Content-Type': 'application/json'
        }
    }
}

def create_enhanced_prompt(focus_mode, question, name, subject, grade, level, conversation_history):
    """
    MATA v2.0: Prompt berdasarkan fokus mode yang dipilih user
    """

    # Buat konteks dasar tutor dengan raw string untuk LaTeX
    base_prompt = rf"""Kamu adalah MATA v2.0, asisten belajar cerdas dan adaptif yang membantu {name} belajar {subject} di tingkat {grade}.

🚨 PERINGATAN LATeX CRITICAL - WAJIB DIPATUHI:
- WAJIB gunakan HANYA delimiter \(...\) dan \[...\]
- JANGAN gunakan dolar...dolar atau dolar dolar...dolar dolar - HANYA \( dan \[
- Inline math: \(formula\) (HANYA \( di awal dan \) di akhir)
- Display math: \[formula\] (HANYA \[ di awal dan \] di akhir)
- CONTOH BENAR: \(2x^3 - 3x - 1\), \(\int_0^2 x^2 dx\)
- JIKA MENGGUNAKAN $...$ MAKA JAWABAN AKAN DIREJECT!


KONTEKS SEBELUMNYA:
{conversation_history}

PERTANYAAN SISWA:
{question}

MODE FOKUS YANG DIPILIH: {focus_mode}
"""

    # Tentukan gaya berdasarkan fokus mode
    if focus_mode == "jawab_soal":
        base_prompt += """
MODE: JAWAB SOAL / PROBLEM SOLVER
Ini adalah mode khusus untuk menyelesaikan soal matematika atau perhitungan.

ATURAN KETAT:
- Fokus HANYA pada penyelesaian step-by-step
- Jangan berikan teori panjang atau penjelasan konsep
- Langsung ke solusi praktis dengan langkah logis
- Format jawaban WAJIB:

**Penyelesaian**
**Langkah 1:** [Langkah pertama perhitungan]  
**Langkah 2:** [Langkah berikutnya]  
**Langkah 3:** [Dst bila perlu]

**Jawaban Akhir**
**Hasil:** [Jawaban final dengan satuan jika ada]

🚨 LaTeX syntax WAJIB benar - TIDAK BOLEH ADA ERROR:
  * HANYA gunakan delimiter \(...\) dan \[...\] (JANGAN dolar...dolar atau dolar dolar...dolar dolar)
  * Inline: \(formula\) (HANYA \( di awal dan \) di akhir)
  * Display: \[formula\] (HANYA \[ di awal dan \] di akhir)
  * Subscript: x_1, C_1 (UNDERSCORE _ bukan dolar)
  * Superscript: x^2, x^3 (CARET ^ bukan dolar)
  * CONTOH BENAR: \(2x^3 - 3x - 1\), \(\frac{d}{dx}(x^2) = 2x\)
  * JIKA MENGGUNAKAN $...$ MAKA JAWABAN AKAN DIREJECT!
- Jika ada beberapa cara, pilih yang paling efisien
"""

    elif focus_mode == "penjelasan":
        base_prompt += """
MODE: PENJELASAN KONSEP
Berikan penjelasan mendalam tentang konsep, teori, atau topik yang ditanyakan.

ATURAN:
- Jelaskan konsep dari dasar hingga detail
- Gunakan analogi atau contoh praktis yang mudah dipahami
- Sertakan sejarah atau latar belakang jika relevan
- Hubungkan dengan aplikasi praktis
- Gunakan struktur yang jelas dengan heading
- Sertakan tips atau catatan penting
"""

    elif focus_mode == "analisis":
        base_prompt += """
MODE: ANALISIS MENDALAM
Lakukan analisis komprehensif terhadap topik, soal, atau konsep yang ditanyakan.

ATURAN:
- Analisis dari berbagai sudut pandang
- Identifikasi pola, hubungan, atau karakteristik penting
- Bandingkan dengan konsep terkait jika ada
- Berikan insight atau observasi mendalam
- Diskusikan implikasi atau konsekuensi
- Sertakan contoh atau kasus untuk memperkuat analisis
"""

    else:  # default
        base_prompt += """
MODE: AUTO (SMART DETECTION)
Deteksi otomatis intent dan berikan respons yang sesuai.
"""

    # Normalisasi level
    level = (level or "auto").strip().lower()

    # Tentukan gaya intervensi sesuai level
    if level == "eksplisit":
        base_prompt += """
TINGKAT BANTUAN: EKSPLISIT
- Berikan panduan langkah demi langkah yang sangat detail
- Jelaskan setiap langkah dengan alasan logis
- Gunakan contoh konkret dan hindari istilah teknis rumit
"""

    elif level == "prosedural":
        base_prompt += """
TINGKAT BANTUAN: PROSEDURAL
- Berikan petunjuk tentang metode, rumus, atau strategi
- Jangan langsung selesaikan semua perhitungan
- Dorong siswa mencoba langkah berikutnya
"""

    elif level == "konseptual":
        base_prompt += """
TINGKAT BANTUAN: KONSEPTUAL
- Fokus pada pemahaman konseptual
- Ajukan pertanyaan balik untuk memicu pemikiran
- Hindari memberi jawaban akhir langsung
"""

    elif level == "non_intervensi":
        base_prompt += """
TINGKAT BANTUAN: MINIMAL
- Berikan feedback minimal
- Hanya konfirmasi benar/salah dengan petunjuk singkat
"""

    base_prompt += """
CATATAN UMUM:
- Gunakan bahasa Indonesia yang alami dan mudah dipahami
- Gunakan LaTeX untuk rumus matematika: \(formula\) atau \[formula\]
- Tunjukkan empati dan kesabaran dalam bimbingan
- Sesuaikan kompleksitas dengan tingkat grade siswa

FORMAT HEADING YANG WAJIB DIGUNAKAN:
- Gunakan format sederhana untuk heading:
  * **Judul Utama**
  * **Sub Judul**
  * **Poin Penting**
  * **Solusi/Langkah**
  * **Tips/Peringatan**
🚨 LaTeX/equation WAJIB menggunakan format yang benar - TIDAK BOLEH ADA ERROR:
  * HANYA gunakan delimiter \(...\) dan \[...\] (JANGAN dolar...dolar atau dolar dolar...dolar dolar)
  * Inline math: \(formula\) (HANYA \( di awal dan \) di akhir)
  * Display math: \[formula\] (HANYA \[ di awal dan \] di akhir)
  * Subscript: x_1, x_2 (UNDERSCORE _ bukan dolar)
  * Superscript: x^2, x^3 (CARET ^ bukan dolar)
  * Integral: \int_a^b f(x) dx (tanpa delimiter tambahan)
  * CONTOH BENAR: \(2x^3 - 3x - 1\), \(\int_0^2 x^2 dx\), \(f(x) = x^2 + 3x_1\)
  * JIKA MENGGUNAKAN $...$ MAKA JAWABAN AKAN DIREJECT!
"""

    return base_prompt

def get_conversation_history(session_id, limit=5):
    """Get recent conversation history"""
    if session_id not in conversations:
        return "Ini adalah percakapan baru."
    
    history = conversations[session_id][-limit:]
    formatted_history = []
    
    for entry in history:
        formatted_history.append(f"User: {entry['question']}")
        formatted_history.append(f"AI: {entry['response'][:200]}...")
    
    return '\n'.join(formatted_history) if formatted_history else "Ini adalah percakapan baru."

def sanitize_latex_delimiters(text):
    """
    Normalize LaTeX delimiters in API response
    Convert all $...$ to \(...\) and $$...$$ to \[...\]
    """
    
    # Debug logging
    original_text = text
    dollar_count = text.count('$')
    
    # Convert $$...$$ to \[...\] (display math)
    text = re.sub(r'\$\$([^$]+)\$\$', r'\\[\1\\]', text)
    
    # Convert $...$ to \(...\) (inline math) - but be careful not to convert already processed ones
    text = re.sub(r'(?<!\\)\$([^$\n]+?)(?<!\\)\$', r'\\(\1\\)', text)
    
    # Debug logging
    print(f"🔧 LaTeX Sanitization:")
    print(f"  - Original $ count: {dollar_count}")
    print(f"  - Final $ count: {text.count('$')}")
    print(f"  - Contains \\(: {'\\(formula\\)' in text}")
    print(f"  - Contains \\[: {'\\[formula\\]' in text}")
    
    return text

def save_conversation(session_id, question, response, focus_mode):
    """Save conversation to memory"""
    if session_id not in conversations:
        conversations[session_id] = []
    
    conversations[session_id].append({
        'timestamp': datetime.now().isoformat(),
        'question': question,
        'response': response,
        'focus_mode': focus_mode
    })
    
    if len(conversations[session_id]) > 20:
        conversations[session_id] = conversations[session_id][-20:]

def analyze_conversation_for_visualization(session_id):
    """Analisis percakapan untuk menentukan jenis visualisasi yang cocok"""
    if session_id not in conversations or not conversations[session_id]:
        print("🔍 DEBUG: No conversation found for session_id:", session_id)
        return None
    
    conversation = conversations[session_id]
    print(f"🔍 DEBUG: Analyzing conversation with {len(conversation)} entries")
    
    # Topic scoring system (higher score = more relevant)
    topic_scores = {
        'calculus': 0,
        'trigonometry': 0, 
        'function': 0,
        'statistics': 0,
        'geometry': 0,
        'algebra': 0
    }
    
    math_expressions = []
    keywords = []
    all_text = ""
    
    for entry in conversation:
        question = entry['question'].lower()
        response = entry['response'].lower()
        all_text += question + " " + response + " "
        
        print(f"🔍 DEBUG: Question: {question[:100]}...")
        print(f"🔍 DEBUG: Response: {response[:100]}...")
        
        # Calculus topics (highest priority)
        calculus_words = ['integral', 'diferensial', 'turunan', 'kalkulus', 'garis singgung', 'limit', 'derivative', 'integral', 'dx', 'dy', 'f\'(x)', 'd/dx', 'antiderivative']
        for word in calculus_words:
            if word in question + response:
                topic_scores['calculus'] += 2  # Higher weight
                print(f"🔍 DEBUG: Found calculus word: {word}")
        
        # Trigonometry topics
        trig_words = ['trigonometri', 'sin', 'cos', 'tan', 'sinus', 'cosinus', 'tangen', 'radian', 'degree', 'sin(x)', 'cos(x)', 'tan(x)']
        for word in trig_words:
            if word in question + response:
                topic_scores['trigonometry'] += 2
                print(f"🔍 DEBUG: Found trigonometry word: {word}")
        
        # Function topics
        function_words = ['fungsi', 'function', 'persamaan', 'equation', 'f(x)', 'g(x)', 'linear', 'kuadrat', 'eksponensial', 'logaritma']
        for word in function_words:
            if word in question + response:
                topic_scores['function'] += 1
                print(f"🔍 DEBUG: Found function word: {word}")
        
        # Statistics topics
        stats_words = ['statistik', 'data', 'rata-rata', 'mean', 'distribusi', 'grafik', 'histogram', 'probability', 'probabilitas']
        for word in stats_words:
            if word in question + response:
                topic_scores['statistics'] += 2
                print(f"🔍 DEBUG: Found statistics word: {word}")
        
        # Geometry topics
        geometry_words = ['geometri', 'lingkaran', 'segitiga', 'persegi', 'volume', 'luas', 'perimeter', 'keliling', 'sudut', 'angle']
        for word in geometry_words:
            if word in question + response:
                topic_scores['geometry'] += 2
                print(f"🔍 DEBUG: Found geometry word: {word}")
        
        # Algebra topics
        algebra_words = ['matriks', 'matrix', 'vektor', 'vector', 'determinan', 'determinant', 'eigenvalue', 'eigenvector']
        for word in algebra_words:
            if word in question + response:
                topic_scores['algebra'] += 2
                print(f"🔍 DEBUG: Found algebra word: {word}")
        
        # Extract numbers and patterns
        numbers = re.findall(r'-?\d+\.?\d*', question + response)
        if numbers:
            math_expressions.extend(numbers)
        
        # Extract keywords
        words = re.findall(r'\b\w+\b', question + response)
        keywords.extend(words)
    
    # Find the topic with highest score
    best_topic = max(topic_scores.items(), key=lambda x: x[1])
    print(f"🔍 DEBUG: Topic scores: {topic_scores}")
    print(f"🔍 DEBUG: Best topic: {best_topic[0]} with score {best_topic[1]}")
    
    # If no specific topic detected, use function as default
    if best_topic[1] == 0:
        print("🔍 DEBUG: No specific topic detected, using function as default")
        detected_topics = ['function']
    else:
        detected_topics = [best_topic[0]]
    
    return {
        'topics': detected_topics,
        'topic_scores': topic_scores,
        'numbers': [float(x) for x in math_expressions if x.replace('.', '').replace('-', '').isdigit()],
        'keywords': list(set(keywords)),
        'conversation_length': len(conversation),
        'all_text': all_text[:500]  # First 500 chars for debugging
    }

def create_function_visualization():
    """Membuat visualisasi fungsi matematika"""
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10))
    fig.suptitle('Visualisasi Fungsi Matematika', fontsize=16, fontweight='bold')
    
    x = np.linspace(-10, 10, 1000)
    
    # Linear function
    y1 = 2*x + 1
    ax1.plot(x, y1, 'b-', linewidth=2, label='f(x) = 2x + 1')
    ax1.grid(True, alpha=0.3)
    ax1.set_title('Fungsi Linear')
    ax1.set_xlabel('x')
    ax1.set_ylabel('f(x)')
    ax1.legend()
    
    # Quadratic function
    y2 = x**2 - 4*x + 3
    ax2.plot(x, y2, 'r-', linewidth=2, label='f(x) = x² - 4x + 3')
    ax2.grid(True, alpha=0.3)
    ax2.set_title('Fungsi Kuadrat')
    ax2.set_xlabel('x')
    ax2.set_ylabel('f(x)')
    ax2.legend()
    
    # Exponential function
    x_exp = np.linspace(-3, 3, 1000)
    y3 = np.exp(x_exp)
    ax3.plot(x_exp, y3, 'g-', linewidth=2, label='f(x) = eˣ')
    ax3.grid(True, alpha=0.3)
    ax3.set_title('Fungsi Eksponensial')
    ax3.set_xlabel('x')
    ax3.set_ylabel('f(x)')
    ax3.legend()
    
    # Logarithmic function
    x_log = np.linspace(0.1, 10, 1000)
    y4 = np.log(x_log)
    ax4.plot(x_log, y4, 'm-', linewidth=2, label='f(x) = ln(x)')
    ax4.grid(True, alpha=0.3)
    ax4.set_title('Fungsi Logaritma')
    ax4.set_xlabel('x')
    ax4.set_ylabel('f(x)')
    ax4.legend()
    
    plt.tight_layout()
    return fig

def create_calculus_visualization():
    """Membuat visualisasi kalkulus dengan garis singgung"""
    fig, ax = plt.subplots(figsize=(12, 8))
    
    def f(x):
        return 0.5 * x**2 - 2*x + 1
    
    def df(x):
        return x - 2
    
    x = np.linspace(-2, 6, 1000)
    y = f(x)
    
    # Plot fungsi
    ax.plot(x, y, 'b-', linewidth=3, label=r'$f(x) = \frac{1}{2}x^2 - 2x + 1$')
    
    # Titik untuk garis singgung
    x_points = np.linspace(-1, 5, 12)
    colors = plt.cm.viridis(np.linspace(0, 1, len(x_points)))
    
    for i, x0 in enumerate(x_points):
        y0 = f(x0)
        slope = df(x0)
        
        # Garis singgung
        x_tang = np.array([x0 - 1.5, x0 + 1.5])
        y_tang = slope * (x_tang - x0) + y0
        
        ax.plot(x_tang, y_tang, '-', color=colors[i], alpha=0.5, linewidth=1.5)
        ax.plot(x0, y0, 'o', color=colors[i], markersize=6, alpha=0.8)
    
    # Mark titik stasioner
    x_stat = 2.0
    y_stat = f(x_stat)
    ax.plot(x_stat, y_stat, 'r*', markersize=20, label='Titik Stasioner (f\'(x)=0)')
    
    ax.set_xlabel('x', fontsize=13, fontweight='bold')
    ax.set_ylabel('y', fontsize=13, fontweight='bold')
    ax.set_title('Garis Singgung dan Turunan', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='upper left')
    ax.set_xlim(-2, 6)
    ax.set_ylim(-5, 8)
    
    plt.tight_layout()
    return fig

def create_trigonometry_visualization():
    """Membuat visualisasi fungsi trigonometri"""
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10))
    fig.suptitle('Visualisasi Fungsi Trigonometri', fontsize=16, fontweight='bold')
    
    x = np.linspace(-2*np.pi, 2*np.pi, 1000)
    
    # Sine function
    y1 = np.sin(x)
    ax1.plot(x, y1, 'b-', linewidth=2, label='sin(x)')
    ax1.grid(True, alpha=0.3)
    ax1.set_title('Fungsi Sinus')
    ax1.set_xlabel('x (radian)')
    ax1.set_ylabel('sin(x)')
    ax1.legend()
    
    # Cosine function
    y2 = np.cos(x)
    ax2.plot(x, y2, 'r-', linewidth=2, label='cos(x)')
    ax2.grid(True, alpha=0.3)
    ax2.set_title('Fungsi Cosinus')
    ax2.set_xlabel('x (radian)')
    ax2.set_ylabel('cos(x)')
    ax2.legend()
    
    # Tangent function
    y3 = np.tan(x)
    y3[np.abs(y3) > 10] = np.nan  # Remove vertical asymptotes
    ax3.plot(x, y3, 'g-', linewidth=2, label='tan(x)')
    ax3.grid(True, alpha=0.3)
    ax3.set_title('Fungsi Tangen')
    ax3.set_xlabel('x (radian)')
    ax3.set_ylabel('tan(x)')
    ax3.set_ylim(-5, 5)
    ax3.legend()
    
    # Combined
    ax4.plot(x, np.sin(x), 'b-', linewidth=2, label='sin(x)')
    ax4.plot(x, np.cos(x), 'r-', linewidth=2, label='cos(x)')
    ax4.grid(True, alpha=0.3)
    ax4.set_title('Sin & Cos Bersamaan')
    ax4.set_xlabel('x (radian)')
    ax4.set_ylabel('y')
    ax4.legend()
    
    plt.tight_layout()
    return fig

def create_statistics_visualization():
    """Membuat visualisasi statistik"""
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10))
    fig.suptitle('Visualisasi Statistik', fontsize=16, fontweight='bold')
    
    # Sample data
    np.random.seed(42)
    data = np.random.normal(50, 15, 100)
    
    # Histogram
    ax1.hist(data, bins=20, alpha=0.7, color='skyblue', edgecolor='black')
    ax1.set_title('Distribusi Data (Histogram)')
    ax1.set_xlabel('Nilai')
    ax1.set_ylabel('Frekuensi')
    ax1.grid(True, alpha=0.3)
    
    # Box plot
    ax2.boxplot(data)
    ax2.set_title('Box Plot')
    ax2.set_ylabel('Nilai')
    ax2.grid(True, alpha=0.3)
    
    # Line plot of cumulative data
    sorted_data = np.sort(data)
    cumulative = np.arange(1, len(sorted_data) + 1) / len(sorted_data) * 100
    ax3.plot(sorted_data, cumulative, 'g-', linewidth=2)
    ax3.set_title('Distribusi Kumulatif')
    ax3.set_xlabel('Nilai')
    ax3.set_ylabel('Persentil (%)')
    ax3.grid(True, alpha=0.3)
    
    # Statistics summary
    mean_val = np.mean(data)
    median_val = np.median(data)
    std_val = np.std(data)
    
    ax4.text(0.1, 0.8, f'Rata-rata: {mean_val:.2f}', fontsize=12, transform=ax4.transAxes)
    ax4.text(0.1, 0.7, f'Median: {median_val:.2f}', fontsize=12, transform=ax4.transAxes)
    ax4.text(0.1, 0.6, f'Std Dev: {std_val:.2f}', fontsize=12, transform=ax4.transAxes)
    ax4.text(0.1, 0.5, f'Min: {min(data):.2f}', fontsize=12, transform=ax4.transAxes)
    ax4.text(0.1, 0.4, f'Max: {max(data):.2f}', fontsize=12, transform=ax4.transAxes)
    ax4.text(0.1, 0.3, f'Total Data: {len(data)}', fontsize=12, transform=ax4.transAxes)
    ax4.set_title('Ringkasan Statistik')
    ax4.axis('off')
    
    plt.tight_layout()
    return fig

def create_geometry_visualization():
    """Membuat visualisasi geometri"""
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10))
    fig.suptitle('Visualisasi Geometri', fontsize=16, fontweight='bold')
    
    # Circle
    theta = np.linspace(0, 2*np.pi, 100)
    x_circle = np.cos(theta)
    y_circle = np.sin(theta)
    ax1.plot(x_circle, y_circle, 'b-', linewidth=2)
    ax1.set_title('Lingkaran (r = 1)')
    ax1.set_xlabel('x')
    ax1.set_ylabel('y')
    ax1.grid(True, alpha=0.3)
    ax1.axis('equal')
    
    # Triangle
    triangle_x = [0, 1, 0.5, 0]
    triangle_y = [0, 0, np.sqrt(3)/2, 0]
    ax2.plot(triangle_x, triangle_y, 'r-', linewidth=2, marker='o')
    ax2.set_title('Segitiga Sama Sisi')
    ax2.set_xlabel('x')
    ax2.set_ylabel('y')
    ax2.grid(True, alpha=0.3)
    ax2.axis('equal')
    
    # Rectangle
    rect_x = [0, 2, 2, 0, 0]
    rect_y = [0, 0, 1, 1, 0]
    ax3.plot(rect_x, rect_y, 'g-', linewidth=2, marker='o')
    ax3.set_title('Persegi Panjang')
    ax3.set_xlabel('x')
    ax3.set_ylabel('y')
    ax3.grid(True, alpha=0.3)
    ax3.axis('equal')
    
    # Parabola
    x_para = np.linspace(-3, 3, 100)
    y_para = x_para**2
    ax4.plot(x_para, y_para, 'm-', linewidth=2)
    ax4.set_title('Parabola y = x²')
    ax4.set_xlabel('x')
    ax4.set_ylabel('y')
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    return fig

def test_api_connection(provider, api_key, model):
    """Test API connection with specific model"""
    try:
        config = API_CONFIGS[provider]
        headers = config['headers_template'].copy()
        
        if provider == 'claude':
            headers['X-API-Key'] = api_key
            payload = {
                'model': model,
                'max_tokens': 10,
                'messages': [{'role': 'user', 'content': 'Hi'}]
            }
        elif provider == 'openai':
            headers['Authorization'] = f'Bearer {api_key}'
            payload = {
                'model': model,
                'max_tokens': 10,
                'messages': [{'role': 'user', 'content': 'Hi'}]
            }
        
        response = requests.post(config['url'], headers=headers, json=payload, timeout=10)
        
        if response.status_code == 200:
            return True, model, None
        else:
            return False, model, f"HTTP {response.status_code}: {response.text[:200]}"
            
    except Exception as e:
        return False, model, str(e)

def make_api_request(provider, api_key, messages):
    """Make API request with conversation history"""
    config = API_CONFIGS.get(provider)
    if not config:
        raise Exception(f"Provider {provider} tidak didukung")
    
    last_error = None
    
    for model in config['models']:
        try:
            headers = config['headers_template'].copy()
            
            if provider == 'claude':
                headers['X-API-Key'] = api_key
                payload = {
                    'model': model,
                    'max_tokens': 4000,
                    'messages': messages
                }
            elif provider == 'openai':
                headers['Authorization'] = f'Bearer {api_key}'
                payload = {
                    'model': model,
                    'max_tokens': 4000,
                    'messages': messages
                }
            
            response = requests.post(config['url'], headers=headers, json=payload, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                
                if provider == 'claude':
                    return result['content'][0]['text'], model
                elif provider == 'openai':
                    return result['choices'][0]['message']['content'], model
            else:
                last_error = f"Model {model}: HTTP {response.status_code} - {response.text[:200]}"
                continue
                
        except Exception as e:
            last_error = f"Model {model}: {str(e)}"
            continue
    
    raise Exception(f"Semua model gagal. Error terakhir: {last_error}")

# HTML Template v2.0 dengan Mode AI dan background putih untuk chat
html_template = '''
<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>MATA v2.0 - Advanced AI Tutoring System</title>
  
  <script>
    window.MathJax = {
      tex: {
        inlineMath: [['\\(', '\\)'], ['$', '$']],  // Support both delimiters as fallback
        displayMath: [['\\[', '\\]'], ['$$', '$$']],  // Support both delimiters as fallback
        processEscapes: true,
        processEnvironments: true,
        processRefs: true,
        packages: {'[+]': ['base', 'ams', 'noerrors', 'noundefined', 'autoload']}
      },
      options: {
        ignoreHtmlClass: 'tex2jax_ignore',
        processHtmlClass: 'tex2jax_process',
        skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre']
      },
      startup: {
        ready: function () {
          MathJax.startup.defaultReady();
          console.log('✅ MathJax is ready and configured!');
        }
      },
      loader: {
        load: ['[tex]/noerrors', '[tex]/noundefined']
      }
    };
  </script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/mathjax/3.2.2/es5/tex-mml-chtml.min.js" 
          onload="console.log('✅ MathJax CDN loaded successfully!')"
          onerror="console.error('❌ MathJax CDN failed to load!')"></script>
  
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { 
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
      background: linear-gradient(to bottom right, #667eea, #764ba2); 
      height: 100vh; 
      overflow: hidden; 
    }
    
    .container { display: flex; height: 100vh; position: relative; }
    
    .particles { position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; z-index: 1; }
    .particle { 
      position: absolute; 
      width: 4px; 
      height: 4px; 
      background: rgba(255,255,255,0.3); 
      border-radius: 50%; 
      animation: float 6s ease-in-out infinite; 
    }
    @keyframes float {
      0%, 100% { transform: translateY(0px) rotate(0deg); opacity: 1; }
      50% { transform: translateY(-20px) rotate(180deg); opacity: 0.8; }
    }
    
    .sidebar {
      width: 280px;
      background: rgba(255,255,255,0.1);
      backdrop-filter: blur(20px);
      border-right: 1px solid rgba(255,255,255,0.2);
      padding: 20px;
      z-index: 10;
      overflow-y: auto;
      transition: transform 0.3s ease-in-out;
      position: relative;
    }
    
    .sidebar.hidden {
      transform: translateX(-100%);
    }
    
    .toggle-sidebar {
      position: fixed;
      top: 20px;
      left: 20px;
      z-index: 1000;
      background: linear-gradient(45deg, #667eea, #764ba2);
      border: none;
      border-radius: 50%;
      width: 45px;
      height: 45px;
      color: white;
      font-size: 18px;
      cursor: pointer;
      box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
      transition: all 0.3s ease;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    
    .toggle-sidebar:hover {
      transform: scale(1.1);
      box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
    }
    
    .toggle-sidebar.sidebar-open {
      left: 300px;
    }
    
    .logo {
      text-align: center;
      color: white;
      font-size: 24px;
      font-weight: bold;
      margin-bottom: 30px;
      text-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }
    /* Mode AI Styles */
    .focus-modes {
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin-bottom: 15px;
    }
    
    .focus-mode {
      padding: 10px;
      border: 1px solid rgba(255,255,255,0.3);
      border-radius: 8px;
      background: rgba(255,255,255,0.1);
      color: white;
      cursor: pointer;
      transition: all 0.3s ease;
      text-align: center;
      font-size: 13px;
      font-weight: 500;
    }
    
    .focus-mode:hover {
      background: rgba(255,255,255,0.2);
      border-color: rgba(255,255,255,0.5);
    }
    
    .focus-mode.active {
      background: linear-gradient(45deg, #667eea, #764ba2);
      border-color: rgba(255,255,255,0.6);
      box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
    }
    
    .feature-buttons {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }
    
    .feature-btn {
      padding: 8px;
      border: 1px solid rgba(255,255,255,0.3);
      border-radius: 6px;
      background: rgba(255,255,255,0.1);
      color: white;
      cursor: pointer;
      transition: all 0.3s ease;
      text-align: center;
      font-size: 11px;
      font-weight: 500;
    }
    
    .feature-btn:hover {
      background: rgba(255,255,255,0.2);
      transform: translateY(-1px);
    }
    
    .form-group {
      margin-bottom: 15px;
    }
    
    .form-group label {
      display: block;
      color: rgba(255,255,255,0.9);
      margin-bottom: 5px;
      font-size: 13px;
    }
    
    .form-group input,
    .form-group select,
    .form-group textarea {
      width: 100%;
      padding: 10px;
      border: 1px solid rgba(255,255,255,0.3);
      border-radius: 8px;
      background: rgba(255,255,255,0.1);
      color: white;
      font-size: 14px;
      backdrop-filter: blur(10px);
    }
    
    .form-group input::placeholder,
    .form-group textarea::placeholder {
      color: rgba(255,255,255,0.6);
    }
    
    .form-group input:focus,
    .form-group select:focus,
    .form-group textarea:focus {
      outline: none;
      border-color: rgba(255,255,255,0.6);
      background: rgba(255,255,255,0.2);
    }
    
    .form-group select option {
      background: #2a2a2a;
      color: white;
    }
    
    .btn {
      width: 100%;
      padding: 12px;
      border: none;
      border-radius: 8px;
      background: linear-gradient(45deg, #667eea, #764ba2);
      color: white;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.3s ease;
      font-size: 14px;
      margin-bottom: 10px;
    }
    
    .btn:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    }
    
    .btn.btn-secondary {
      background: linear-gradient(45deg, #6c757d, #495057);
    }
    
    .btn.btn-secondary:hover {
      box-shadow: 0 4px 12px rgba(108, 117, 125, 0.4);
    }
    
    /* Accordion Menu Styles */
    .menu-section {
      margin-bottom: 15px;
      background: rgba(255,255,255,0.1);
      border-radius: 12px;
      backdrop-filter: blur(10px);
      border: 1px solid rgba(255,255,255,0.2);
      overflow: hidden;
      transition: all 0.3s ease;
    }
    
    .menu-header {
      padding: 15px;
      cursor: pointer;
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: rgba(255,255,255,0.05);
      transition: all 0.3s ease;
      user-select: none;
    }
    
    .menu-header:hover {
      background: rgba(255,255,255,0.1);
    }
    
    .menu-header.active {
      background: rgba(255,255,255,0.15);
    }
    
    .menu-title {
      color: white;
      font-size: 14px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 1px;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    
    .menu-arrow {
      color: rgba(255,255,255,0.7);
      font-size: 16px;
      transition: transform 0.3s ease;
    }
    
    .menu-header.active .menu-arrow {
      transform: rotate(180deg);
    }
    
    .menu-content {
      max-height: 0;
      overflow: hidden;
      transition: max-height 0.3s ease;
      padding: 0 15px;
    }
    
    .menu-content.active {
      max-height: 1000px;
      padding: 15px;
    }

    
    .main-content {
      flex: 1;
      display: flex;
      flex-direction: column;
      position: relative;
      z-index: 10;
    }
    
    .header {
      padding: 20px 30px;
      text-align: center;
      color: white;
      background: rgba(255,255,255,0.1);
      backdrop-filter: blur(20px);
      border-bottom: 1px solid rgba(255,255,255,0.2);
    }
    
    .header h1 {
      font-size: 28px;
      font-weight: 700;
      margin-bottom: 8px;
      text-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }
    
    .header p {
      font-size: 16px;
      opacity: 0.9;
    }
    
    .chat-container {
      flex: 1;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      background: white; /* WHITE BACKGROUND FOR CHAT AREA */
    }
    
    .chat-history {
      flex: 1;
      overflow-y: auto;
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 15px;
      background: white; /* WHITE BACKGROUND */
    }
    
    .chat-history::-webkit-scrollbar {
      width: 6px;
    }
    
    .chat-history::-webkit-scrollbar-track {
      background: #f1f1f1;
      border-radius: 3px;
    }
    
    .chat-history::-webkit-scrollbar-thumb {
      background: #ccc;
      border-radius: 3px;
    }
    
    .chat-history::-webkit-scrollbar-thumb:hover {
      background: #999;
    }
    
    .user-message,
    .ai-message {
      max-width: 85%;
      padding: 15px 20px;
      border-radius: 18px;
      backdrop-filter: blur(20px);
      box-shadow: 0 4px 15px rgba(0,0,0,0.1);
      animation: slideIn 0.3s ease-out;
    }
    
    @keyframes slideIn {
      from { opacity: 0; transform: translateY(20px); }
      to { opacity: 1; transform: translateY(0); }
    }
    
    .user-message {
      align-self: flex-end;
      background: linear-gradient(135deg, #667eea, #764ba2);
      color: white;
      margin-left: auto;
    }
    
    .ai-message {
      align-self: flex-start;
      background: linear-gradient(135deg, #f8f9fa, #e9ecef);
      color: #333;
      border: 1px solid #dee2e6;
    }
    
    .ai-message strong {
      color: #667eea;
    }
    
    .loading {
      display: none;
      align-items: center;
      justify-content: center;
      padding: 20px;
      background: rgba(255,255,255,0.9);
      margin: 10px 20px;
      border-radius: 12px;
      color: #333;
      gap: 15px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }
    
    .loading.show {
      display: flex;
    }
    
    .spinner {
      width: 20px;
      height: 20px;
      border: 2px solid #e9ecef;
      border-top: 2px solid #667eea;
      border-radius: 50%;
      animation: spin 1s linear infinite;
    }
    
    @keyframes spin {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }
    
    .input-area {
      padding: 20px;
      background: rgba(255,255,255,0.95);
      border-top: 1px solid #dee2e6;
      display: flex;
      gap: 15px;
      align-items: flex-end;
    }
    
    .input-container {
      flex: 1;
    }
    
    .question-input {
      width: 100%;
      padding: 15px 20px;
      border: 1px solid #dee2e6;
      border-radius: 25px;
      background: white;
      color: #333;
      font-size: 16px;
      resize: none;
      transition: all 0.3s ease;
      font-family: inherit;
      line-height: 1.4;
      min-height: 50px;
      max-height: 120px;
    }
    
    .question-input::placeholder {
      color: #6c757d;
    }
    
    .question-input:focus {
      outline: none;
      border-color: #667eea;
      box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
    
    .send-btn {
      background: linear-gradient(45deg, #667eea, #764ba2);
      border: none;
      border-radius: 50%;
      width: 50px;
      height: 50px;
      color: white;
      font-size: 18px;
      cursor: pointer;
      transition: all 0.3s ease;
      box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
      display: flex;
      align-items: center;
      justify-content: center;
    }
    
    .send-btn:hover {
      transform: scale(1.1);
      box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
    }
    
    .send-btn:active {
      transform: scale(0.95);
    }
    
    .error-popup {
      position: fixed;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%) scale(0);
      background: rgba(220, 53, 69, 0.95);
      color: white;
      padding: 25px;
      border-radius: 12px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.3);
      z-index: 10000;
      max-width: 400px;
      width: 90%;
      backdrop-filter: blur(20px);
      border: 1px solid rgba(255,255,255,0.2);
      transition: all 0.3s ease;
    }
    
    .error-popup.show {
      transform: translate(-50%, -50%) scale(1);
    }
    
    .error-title {
      font-size: 18px;
      font-weight: bold;
      margin-bottom: 10px;
    }
    
    .error-message {
      margin-bottom: 15px;
      line-height: 1.5;
    }
    
    .error-close {
      background: rgba(255,255,255,0.2);
      border: none;
      color: white;
      padding: 8px 16px;
      border-radius: 6px;
      cursor: pointer;
      float: right;
    }
    
    .error-close:hover {
      background: rgba(255,255,255,0.3);
    }
    
    .provider-info {
      background: rgba(255,255,255,0.1);
      padding: 10px;
      border-radius: 6px;
      font-size: 12px;
      color: rgba(255,255,255,0.8);
      margin-top: 5px;
      line-height: 1.4;
    }
    
    .conversation-stats {
      background: rgba(255,255,255,0.1);
      padding: 10px;
      border-radius: 8px;
      font-size: 12px;
      color: rgba(255,255,255,0.9);
      line-height: 1.5;
    }
    
    .mode-indicator {
      display: inline-block;
      padding: 3px 8px;
      border-radius: 12px;
      font-size: 11px;
      font-weight: 600;
      margin-left: 10px;
      text-transform: uppercase;
      background: rgba(102, 126, 234, 0.2);
      color: #667eea;
      border: 1px solid rgba(102, 126, 234, 0.4);
    }
    
    @media (max-width: 768px) {
      .sidebar {
        width: 100%;
        height: auto;
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        transform: translateY(100%);
        transition: transform 0.3s ease;
        z-index: 1000;
        max-height: 70vh;
      }
      
      .sidebar.hidden {
        transform: translateY(100%);
      }
      
      .sidebar:not(.hidden) {
        transform: translateY(0);
      }
      
      .toggle-sidebar {
        bottom: 20px;
        top: auto;
        left: 50%;
        transform: translateX(-50%);
      }
      
      .toggle-sidebar.sidebar-open {
        left: 50%;
        transform: translateX(-50%);
        bottom: 20px;
      }
      
      .feature-buttons {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <div class="container">
    <div id="particles" class="particles"></div>
    
    <button class="toggle-sidebar" id="toggleSidebar">☰</button>
    
    <div class="sidebar">
      <div class="logo">MATA v2.0</div>
      
      <!-- Mode AI Section -->
      <div class="menu-section">
        <div class="menu-header active" onclick="toggleMenu('modeAi')">
          <div class="menu-title">
            <span>AI</span>
            Mode AI
          </div>
          <div class="menu-arrow">▼</div>
        </div>
        <div class="menu-content active" id="modeAi">
          <div class="form-group">
            <label>Fokus</label>
            <div class="focus-modes">
              <div class="focus-mode active" data-mode="penjelasan">
                Penjelasan Konsep
              </div>
              <div class="focus-mode" data-mode="jawab_soal">
                Jawab Soal
              </div>
              <div class="focus-mode" data-mode="analisis">
                Analisis Mendalam
              </div>
            </div>
          </div>
          
          <div class="form-group">
            <label>Fitur Tambahan</label>
            <div class="feature-buttons">
              <div class="feature-btn" onclick="showFeatureInfo('visualisasi')">
                Visualisasi
              </div>
              <div class="feature-btn" onclick="showFeatureInfo('animasi')">
                Animasi Interaktif
              </div>
              <div class="feature-btn" onclick="generateProblem()">
                Generate Soal
              </div>
              <div class="feature-btn" onclick="showFeatureInfo('referensi')">
                Referensi
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Learning Profile Section -->
      <div class="menu-section">
        <div class="menu-header" onclick="toggleMenu('learningProfile')">
          <div class="menu-title">
            <span>User</span>
            Learning Profile
          </div>
          <div class="menu-arrow">▼</div>
        </div>
        <div class="menu-content" id="learningProfile">
          <div class="form-group">
            <label>Student Name</label>
            <input type="text" id="userName" placeholder="Your Name" value="Siswa">
          </div>
          <div class="form-group">
            <label>Subject</label>
            <select id="subject">
              <option value="Matematika">Matematika</option>
              <option value="Fisika">Fisika</option>
              <option value="Kimia">Kimia</option>
              <option value="Biologi">Biologi</option>
              <option value="Bahasa Indonesia">Bahasa Indonesia</option>
              <option value="Bahasa Inggris">Bahasa Inggris</option>
            </select>
          </div>
          <div class="form-group">
            <label>Grade Level</label>
            <select id="grade">
              <option value="SD">SD (Elementary)</option>
              <option value="SMP">SMP (Middle School)</option>
              <option value="SMA">SMA (High School)</option>
              <option value="Kuliah">Kuliah (University)</option>
            </select>
          </div>
          <div class="form-group">
            <label>Learning Mode</label>
            <select id="brainLevel">
              <option value="auto">Auto (Smart Detection)</option>
              <option value="eksplisit">Explicit (Detailed Steps)</option>
              <option value="prosedural">Procedural (Methods Only)</option>
              <option value="konseptual">Conceptual (Understanding)</option>
              <option value="non_intervensi">⚡ Minimal (Brief Feedback)</option>
            </select>
          </div>
        </div>
      </div>
      
      <!-- Configuration Section -->
      <div class="menu-section">
        <div class="menu-header" onclick="toggleMenu('configuration')">
          <div class="menu-title">
            <span>⚙️</span>
            Configuration
          </div>
          <div class="menu-arrow">▼</div>
        </div>
        <div class="menu-content" id="configuration">
          <div class="form-group">
            <label>AI Provider</label>
            <select id="apiProvider">
              <option value="claude">Anthropic Claude</option>
              <option value="openai">OpenAI GPT</option>
            </select>
          </div>
          <div class="form-group">
            <label>API Key</label>
            <input type="password" id="apiKey" placeholder="sk-ant-api03-...">
            <div class="provider-info" id="providerInfo">
              Masukkan API key dari <strong>Anthropic Console</strong><br>Format: sk-ant-api03-...
            </div>
          </div>
          
          <div class="form-group">
            <label>Session Info</label>
            <div class="conversation-stats" id="conversationStats">
              Exchanges: 0<br>
              Memory: Active<br>
              🆔 Session: New
            </div>
          </div>
          
          <div class="form-group">
            <label>Actions</label>
            <button class="btn" id="saveSettingsBtn">Save Settings</button>
            <button class="btn" id="testApiBtn">Test API</button>
            <button class="btn btn-secondary" id="resetChatBtn">Clear Chat</button>
            <button class="btn btn-secondary" id="resetApiBtn">Reset Settings</button>
          </div>
        </div>
      </div>
    </div>
    
    <div class="main-content">
      <div class="header">
        <h1>MATA v2.0 - Advanced AI Tutoring System</h1>
        <p>Enhanced with Explicit Mode Selection & Advanced Features</p>
      </div>
      
      <div class="chat-container">
        <div class="chat-history" id="chatHistory">
          <div class="ai-message">
            <strong>MATA v2.0 AI Tutor siap membantu!</strong><br><br>
            
            ✨ <strong>Fitur Baru v2.0:</strong><br>
            <strong>Mode AI Eksplisit</strong> - Pilih fokus: Penjelasan, Jawab Soal, atau Analisis<br>
            <strong>Interface Baru</strong> - Background chat putih dengan balloon ungu yang elegan<br>
            <strong>Fitur Tambahan</strong> - Visualisasi, Animasi, Generate Soal, Referensi<br><br>
            
            <strong>Cara Menggunakan:</strong><br>
            1. Pilih <strong>Mode Fokus</strong> di sidebar kiri sesuai kebutuhan<br>
            2. Ketik pertanyaan atau soal Anda<br>
            3. AI akan merespons sesuai mode yang dipilih<br><br>
            
            <strong>Memory Active</strong> - Saya ingat konteks percakapan<br>
            <strong>Auto-Structured</strong> - Respons terstruktur sesuai mode<br><br>
            
            <strong>Pilih mode dan mulai belajar!</strong>
          </div>
        </div>
        
        <div class="loading" id="loading">
          <div class="spinner"></div>
          <div>Processing with AI intelligence...</div>
        </div>
        
        <div class="input-area">
          <div class="input-container">
            <textarea 
              id="questionInput" 
              class="question-input" 
              placeholder="Ketik pertanyaan Anda di sini... (Mode saat ini akan menentukan gaya jawaban)"
              rows="2"
            ></textarea>
          </div>
          <button class="send-btn" id="sendBtn">➤</button>
        </div>
      </div>
    </div>
  </div>

  <div class="error-popup" id="errorPopup">
    <div class="error-title">❌ Error</div>
    <div class="error-message" id="errorMessage"></div>
    <button class="error-close" onclick="hideError()">Tutup</button>
  </div>

  <script>
    let chatHistory = [];
    let sessionId = null;
    let conversationCount = 0;
    let currentFocusMode = 'penjelasan';
    
    function generateSessionId() {
      return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    function updateConversationStats() {
      const statsDiv = document.getElementById('conversationStats');
      statsDiv.innerHTML = `Exchanges: ${conversationCount}<br>Memory: Active<br>Session: ${sessionId ? sessionId.substr(-8) : 'New'}`;
    }
    
    function createParticles() {
      const particlesContainer = document.getElementById('particles');
      for (let i = 0; i < 50; i++) {
        const particle = document.createElement('div');
        particle.className = 'particle';
        particle.style.left = Math.random() * 100 + '%';
        particle.style.top = Math.random() * 100 + '%';
        particle.style.animationDelay = Math.random() * 6 + 's';
        particle.style.animationDuration = (Math.random() * 4 + 4) + 's';
        particlesContainer.appendChild(particle);
      }
    }

    function toggleSidebar() {
      const sidebar = document.querySelector('.sidebar');
      const toggleBtn = document.getElementById('toggleSidebar');
      
      sidebar.classList.toggle('hidden');
      
      if (sidebar.classList.contains('hidden')) {
        toggleBtn.classList.remove('sidebar-open');
        toggleBtn.innerHTML = '☰';
        toggleBtn.style.left = '20px';
      } else {
        toggleBtn.classList.add('sidebar-open');
        toggleBtn.innerHTML = '✕';
        toggleBtn.style.left = '300px';
      }
    }

    function toggleMenu(menuId) {
      const menuContent = document.getElementById(menuId);
      const menuHeader = menuContent.previousElementSibling;
      
      // Toggle current menu
      menuContent.classList.toggle('active');
      menuHeader.classList.toggle('active');
      
      // Optional: Auto-collapse other menus (uncomment if you want accordion behavior)
      // const allMenus = document.querySelectorAll('.menu-content');
      // const allHeaders = document.querySelectorAll('.menu-header');
      // allMenus.forEach((menu, index) => {
      //   if (menu !== menuContent) {
      //     menu.classList.remove('active');
      //     allHeaders[index].classList.remove('active');
      //   }
      // });
    }

    function selectFocusMode(mode) {
      currentFocusMode = mode;
      
      // Update UI
      document.querySelectorAll('.focus-mode').forEach(el => {
        el.classList.remove('active');
      });
      
      document.querySelector(`[data-mode="${mode}"]`).classList.add('active');
      
      // Update placeholder
      const input = document.getElementById('questionInput');
      switch(mode) {
        case 'jawab_soal':
          input.placeholder = 'Masukkan soal matematika yang ingin diselesaikan...';
          break;
        case 'penjelasan':
          input.placeholder = 'Tanyakan konsep atau topik yang ingin dijelaskan...';
          break;
        case 'analisis':
          input.placeholder = 'Masukkan topik yang ingin dianalisis secara mendalam...';
          break;
      }
    }

    function showFeatureInfo(feature) {
      let message = '';
      switch(feature) {
        case 'visualisasi':
          message = 'Fitur Visualisasi akan menghasilkan grafik, diagram, atau chart untuk membantu pemahaman visual dari konsep yang sedang dipelajari.';
          break;
        case 'animasi':
          message = 'Fitur Animasi Interaktif akan membuat animasi step-by-step untuk menjelaskan proses atau konsep kompleks secara visual dan interaktif.';
          break;
        case 'referensi':
          message = 'Fitur Referensi akan menyediakan sumber bacaan tambahan, link, atau material referensi yang relevan dengan topik yang sedang dipelajari.';
          break;
      }
      alert(message);
    }

    function generateProblem() {
      const subject = document.getElementById('subject').value;
      const grade = document.getElementById('grade').value;
      
      // Add generate problem message
      addMessage(`Tolong buatkan soal ${subject} untuk tingkat ${grade}`, 'user');
      
      // Set mode to problem solving for the response
      const originalMode = currentFocusMode;
      currentFocusMode = 'jawab_soal';
      
      // Call API to generate problem
      sendQuestionToAPI(`Buatkan 1 soal ${subject} tingkat ${grade} beserta penyelesaiannya yang detail`);
      
      // Reset mode
      currentFocusMode = originalMode;
    }

    function updateProviderInfo() {
      const provider = document.getElementById('apiProvider').value;
      const infoDiv = document.getElementById('providerInfo');
      
      if (provider === 'claude') {
        infoDiv.innerHTML = 'Masukkan API key dari <strong>Anthropic Console</strong><br>Format: sk-ant-api03-...';
      } else if (provider === 'openai') {
        infoDiv.innerHTML = 'Masukkan API key dari <strong>OpenAI Platform</strong><br>Format: sk-proj-...';
      }
    }

    function showError(message) {
      document.getElementById('errorMessage').innerHTML = message;
      document.getElementById('errorPopup').classList.add('show');
    }

    function hideError() {
      document.getElementById('errorPopup').classList.remove('show');
    }

    function saveSettings() {
      const settings = {
        apiProvider: document.getElementById('apiProvider').value,
        apiKey: document.getElementById('apiKey').value,
        userName: document.getElementById('userName').value,
        brainLevel: document.getElementById('brainLevel').value,
        subject: document.getElementById('subject').value,
        grade: document.getElementById('grade').value,
        focusMode: currentFocusMode
      };
      
      localStorage.setItem('mataSettings', JSON.stringify(settings));
      alert('✅ Pengaturan berhasil disimpan!');
    }

    function loadSettings() {
      const savedSettings = localStorage.getItem('mataSettings');
      if (savedSettings) {
        const settings = JSON.parse(savedSettings);
        document.getElementById('apiProvider').value = settings.apiProvider || 'claude';
        document.getElementById('apiKey').value = settings.apiKey || '';
        document.getElementById('userName').value = settings.userName || 'Siswa';
        document.getElementById('brainLevel').value = settings.brainLevel || 'auto';
        document.getElementById('subject').value = settings.subject || 'Matematika';
        document.getElementById('grade').value = settings.grade || 'Kuliah';
        
        if (settings.focusMode) {
          selectFocusMode(settings.focusMode);
        }
        
        updateProviderInfo();
      }
    }

    function resetSettings() {
      if (confirm('Yakin ingin menghapus semua pengaturan?')) {
        localStorage.removeItem('mataSettings');
        location.reload();
      }
    }

    function resetChat() {
      if (confirm('Yakin ingin menghapus riwayat chat?')) {
        chatHistory = [];
        conversationCount = 0;
        sessionId = generateSessionId();
        updateConversationStats();
        
        const chatHistoryDiv = document.getElementById('chatHistory');
        chatHistoryDiv.innerHTML = `
          <div class="ai-message">
            <strong>Chat history cleared! Starting fresh conversation...</strong><br>
            Silakan mulai dengan pertanyaan baru!
          </div>
        `;
      }
    }

    async function testAPI() {
      const apiProvider = document.getElementById('apiProvider').value;
      const apiKey = document.getElementById('apiKey').value;
      
      if (!apiKey) {
        showError('Masukkan API key terlebih dahulu!');
        return;
      }

      try {
        document.getElementById('loading').classList.add('show');
        
        const response = await fetch('/test-api', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            api_provider: apiProvider,
            api_key: apiKey
          })
        });

        const result = await response.json();
        document.getElementById('loading').classList.remove('show');

        if (result.success) {
          alert('✅ API connection berhasil!\\nModel: ' + result.model);
        } else {
          showError('❌ API test gagal: ' + result.error);
        }
      } catch (error) {
        document.getElementById('loading').classList.remove('show');
        showError('❌ Error: ' + error.message);
      }
    }

    async function sendQuestion() {
      const questionInput = document.getElementById('questionInput');
      const question = questionInput.value.trim();
      
      if (!question) {
        showError('Masukkan pertanyaan terlebih dahulu!');
        return;
      }

      addMessage(question, 'user');
      questionInput.value = '';
      questionInput.style.height = 'auto';
      
      await sendQuestionToAPI(question);
    }

    async function sendQuestionToAPI(question) {
      const apiProvider = document.getElementById('apiProvider').value;
      const apiKey = document.getElementById('apiKey').value;
      const userName = document.getElementById('userName').value;
      const brainLevel = document.getElementById('brainLevel').value;
      const subject = document.getElementById('subject').value;
      const grade = document.getElementById('grade').value;

      if (!apiKey) {
        showError('⚠️ API key belum diatur!\\nSilakan masuk ke pengaturan dan isi API key terlebih dahulu.');
        return;
      }

      document.getElementById('loading').classList.add('show');

      try {
        const response = await fetch('/ask-enhanced', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            api_provider: apiProvider,
            api_key: apiKey,
            name: userName,
            level: brainLevel,
            subject: subject,
            grade: grade,
            question: question,
            focus_mode: currentFocusMode,
            session_id: sessionId
          })
        });

        const result = await response.json();
        document.getElementById('loading').classList.remove('show');

        if (result.success) {
          addMessage(result.answer, 'ai', result.focus_mode, result.model_used);
          conversationCount++;
          updateConversationStats();
        } else {
          showError('❌ Error: ' + result.error + (result.error_details ? '<br><br><small>' + result.error_details + '</small>' : ''));
        }
      } catch (error) {
        document.getElementById('loading').classList.remove('show');
        showError('❌ Network error: ' + error.message + '<br><br><small>Periksa koneksi internet Anda.</small>');
      }
    }

    function addMessage(message, sender, focusMode = null, model = null) {
      const chatHistory = document.getElementById('chatHistory');
      const messageDiv = document.createElement('div');
      messageDiv.className = sender + '-message';
      
      if (sender === 'user') {
        messageDiv.innerHTML = `<strong>Anda:</strong><br><br>${message.replace(/\\n/g, '<br>')}`;
      } else {
        const modeClass = focusMode ? `mode-${focusMode}` : '';
        const indicator = focusMode ? `<span class="mode-indicator">${focusMode}</span>` : '';
        
        // Protect LaTeX delimiters from replace operations
        const latexPlaceholders = {};
        let messageWithPlaceholders = message;
        
        // Find and protect LaTeX content
        const latexPatterns = [
          /\\([^\\]+)\\/g,  // \(...\)
          /\\[([^\\]+)\\]/g,  // \[...\]
          /\$([^$]+)\$/g,     // $...$
          /\$\$([^$]+)\$\$/g  // $$...$$
        ];
        
        let placeholderIndex = 0;
        latexPatterns.forEach(pattern => {
          messageWithPlaceholders = messageWithPlaceholders.replace(pattern, (match) => {
            const placeholder = `__LATEX_PLACEHOLDER_${placeholderIndex++}__`;
            latexPlaceholders[placeholder] = match;
            return placeholder;
          });
        });
        
        // Now apply formatting to non-LaTeX content
        let formattedMessage = messageWithPlaceholders
          .replace(/\\n/g, '<br>')
          .replace(/\\*\\*(.*?)\\*\\*/g, '<strong>$1</strong>')
          .replace(/\\*(.*?)\\*/g, '<em>$1</em>')
          .replace(/^## (.*$)/gim, '<h3 style="color: #667eea; margin: 15px 0 10px 0; font-size: 18px;">$1</h3>')
          .replace(/^### (.*$)/gim, '<h4 style="color: #333; margin: 12px 0 8px 0; font-size: 16px;">$1</h4>')
          .replace(/^- (.*$)/gim, '<li style="margin: 5px 0;">$1</li>')
          .replace(/(<li.*<\\/li>)/s, '<ul style="margin: 10px 0; padding-left: 20px;">$1</ul>');
        
        // Restore LaTeX content
        Object.keys(latexPlaceholders).forEach(placeholder => {
          formattedMessage = formattedMessage.replace(new RegExp(placeholder, 'g'), latexPlaceholders[placeholder]);
        });
        
        // Debug logging
        console.log('🔍 DEBUG: Message formatting:');
        console.log('  - Original message length:', message.length);
        console.log('  - LaTeX placeholders found:', Object.keys(latexPlaceholders).length);
        console.log('  - Final formatted message length:', formattedMessage.length);
        
        messageDiv.innerHTML = `<strong>AI Tutor:</strong>${indicator}<br><br>${formattedMessage}`;
      }
      
      chatHistory.appendChild(messageDiv);
      chatHistory.scrollTop = chatHistory.scrollHeight;
      
      if (window.MathJax) {
        MathJax.typesetPromise([messageDiv]).catch(function (err) {
          console.log('MathJax typeset failed: ' + err.message);
        });
      }
    }

    function handleKeyPress(event) {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendQuestion();
      }
    }

    function setupEventListeners() {
      document.getElementById('toggleSidebar').addEventListener('click', toggleSidebar);
      document.getElementById('apiProvider').addEventListener('change', updateProviderInfo);
      document.getElementById('saveSettingsBtn').addEventListener('click', saveSettings);
      document.getElementById('testApiBtn').addEventListener('click', testAPI);
      document.getElementById('resetApiBtn').addEventListener('click', resetSettings);
      document.getElementById('resetChatBtn').addEventListener('click', resetChat);
      document.getElementById('sendBtn').addEventListener('click', sendQuestion);
      document.getElementById('questionInput').addEventListener('keypress', handleKeyPress);
      
      // Focus mode selection
      document.querySelectorAll('.focus-mode').forEach(mode => {
        mode.addEventListener('click', function() {
          selectFocusMode(this.dataset.mode);
        });
      });
    }

    function initApp() {
      console.log('Initializing MATA v2.0...');
      sessionId = generateSessionId();
      createParticles();
      loadSettings();
      setupEventListeners();
      updateProviderInfo();
      updateConversationStats();
      console.log('✅ MATA v2.0 System ready!');
    }

    window.addEventListener('DOMContentLoaded', function() {
      setTimeout(initApp, 500);
    });
  </script>
</body>
</html>
'''

@app.route('/')
def index():
    # Serve login page first
    import os
    file_path = os.path.join(os.path.dirname(__file__), 'login.html')
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/login.html')
def login():
    # Serve login page
    import os
    file_path = os.path.join(os.path.dirname(__file__), 'login.html')
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/app')
def app_page():
    # Serve main application
    import os
    file_path = os.path.join(os.path.dirname(__file__), 'index.html')
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/api/test-api', methods=['POST'])
def test_api():
    try:
        data = request.get_json()
        provider = data.get('api_provider', 'claude')
        api_key = data.get('api_key')
        
        if not api_key:
            return jsonify({'success': False, 'error': 'API key diperlukan'})
        
        config = API_CONFIGS.get(provider)
        if not config:
            return jsonify({'success': False, 'error': f'Provider {provider} tidak didukung'})
        
        for model in config['models']:
            success, tested_model, error = test_api_connection(provider, api_key, model)
            if success:
                return jsonify({
                    'success': True, 
                    'model': tested_model,
                    'provider': provider
                })
        
        return jsonify({
            'success': False, 
            'error': f'Semua model gagal. Error terakhir: {error}'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Test error: {str(e)}'})

@app.route('/api/ask-enhanced', methods=['POST'])
def ask_enhanced():
    try:
        data = request.get_json()
        api_provider = data.get('api_provider', 'claude')
        api_key = data.get('api_key')
        name = data.get('name', 'Siswa')
        level = data.get('level', 'auto')
        subject = data.get('subject', 'Matematika')
        grade = data.get('grade', 'Kuliah')
        question = data.get('question', '')
        focus_mode = data.get('focus_mode', 'penjelasan')
        session_id = data.get('session_id')
        
        if not api_key or not question:
            return jsonify({
                'success': False, 
                'error': 'API key dan pertanyaan harus diisi',
                'error_details': 'Pastikan API key sudah dimasukkan di pengaturan dan pertanyaan tidak kosong'
            })
        
        print(f"Focus Mode Selected: {focus_mode}")
        
        conversation_history = get_conversation_history(session_id)
        
        prompt = create_enhanced_prompt(focus_mode, question, name, subject, grade, level, conversation_history)
        
        # Debug logging untuk prompt yang dikirim ke API
        print(f"\n🔍 DEBUG: Prompt yang dikirim ke API:")
        print(f"Focus Mode: {focus_mode}")
        print(f"Question: {question[:100]}...")
        print(f"Prompt LaTeX delimiters check:")
        print(f"  - Contains \\(: {'\\(formula\\)' in prompt}")
        print(f"  - Contains \\[: {'\\[formula\\]' in prompt}")
        print(f"  - Contains $: {'$' in prompt}")
        print(f"  - Prompt length: {len(prompt)} characters")
        print(f"  - Last 200 chars: {prompt[-200:]}")
        
        messages = [{'role': 'user', 'content': prompt}]
        
        if session_id in conversations and len(conversations[session_id]) > 0:
            recent_history = conversations[session_id][-3:]
            for entry in recent_history:
                messages.insert(-1, {'role': 'user', 'content': entry['question']})
                messages.insert(-1, {'role': 'assistant', 'content': entry['response'][:500]})
        
        answer, used_model = make_api_request(api_provider, api_key, messages)
        
        # Sanitize LaTeX delimiters in response
        print(f"\n🔧 DEBUG: API Response before sanitization:")
        print(f"  - Response length: {len(answer)}")
        print(f"  - Contains $: {'$' in answer}")
        print(f"  - Contains \\(: {'\\(formula\\)' in answer}")
        print(f"  - Contains \\[: {'\\[formula\\]' in answer}")
        print(f"  - RAW API RESPONSE:")
        print(f"    '{answer}'")
        print(f"  - RAW API RESPONSE (repr):")
        print(f"    {repr(answer)}")
        
        sanitized_answer = sanitize_latex_delimiters(answer)
        
        print(f"\n🔧 DEBUG: API Response after sanitization:")
        print(f"  - Sanitized response length: {len(sanitized_answer)}")
        print(f"  - Contains $: {'$' in sanitized_answer}")
        print(f"  - Contains \\(: {'\\(formula\\)' in sanitized_answer}")
        print(f"  - Contains \\[: {'\\[formula\\]' in sanitized_answer}")
        
        save_conversation(session_id, question, sanitized_answer, focus_mode)
        
        return jsonify({
            'success': True, 
            'answer': sanitized_answer,  # Use sanitized answer
            'focus_mode': focus_mode,
            'model_used': used_model,
            'provider': api_provider,
            'conversation_length': len(conversations.get(session_id, []))
        })
        
    except requests.exceptions.Timeout:
        return jsonify({
            'success': False, 
            'error': 'Request timeout - coba lagi',
            'error_details': 'Koneksi ke API terlalu lama. Periksa koneksi internet dan coba lagi.'
        })
    except requests.exceptions.RequestException as e:
        return jsonify({
            'success': False, 
            'error': f'Connection error: {str(e)}',
            'error_details': 'Masalah koneksi jaringan. Periksa koneksi internet Anda.'
        })
    except Exception as e:
        error_msg = str(e)
        
        if 'api key' in error_msg.lower():
            detailed_error = 'API key tidak valid atau tidak memiliki akses. Periksa kembali API key Anda.'
        elif 'model' in error_msg.lower():
            detailed_error = 'Model AI tidak tersedia. Coba ganti provider atau periksa subscription Anda.'
        elif 'quota' in error_msg.lower() or 'billing' in error_msg.lower():
            detailed_error = 'Quota API habis atau billing bermasalah. Periksa account API Anda.'
        else:
            detailed_error = error_msg
        
        return jsonify({
            'success': False, 
            'error': f'Server error: {error_msg}',
            'error_details': detailed_error
        })

@app.route('/api/generate-visualization', methods=['POST'])
def generate_visualization():
    """Generate matplotlib visualization based on conversation context"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        if not session_id or session_id not in conversations:
            return jsonify({
                'success': False, 
                'error': 'Session tidak ditemukan atau belum ada percakapan'
            })
        
        # Analisis percakapan untuk menentukan visualisasi yang cocok
        analysis = analyze_conversation_for_visualization(session_id)
        
        if not analysis:
            return jsonify({
                'success': False, 
                'error': 'Tidak dapat menganalisis percakapan'
            })
        
        print(f"🔍 DEBUG: Analysis result: {analysis}")
        print(f"🔍 DEBUG: Detected topics: {analysis['topics']}")
        
        # Tentukan jenis visualisasi berdasarkan topik
        visualization_type = "General Math"
        description = "Visualisasi matematis umum"
        
        try:
            # Prioritize based on detected topics
            if 'calculus' in analysis['topics']:
                fig = create_calculus_visualization()
                visualization_type = "Kalkulus"
                description = "Visualisasi konsep kalkulus: garis singgung dan turunan"
            elif 'trigonometry' in analysis['topics']:
                fig = create_trigonometry_visualization()
                visualization_type = "Trigonometri"
                description = "Visualisasi fungsi trigonometri: sinus, kosinus, dan tangen"
            elif 'statistics' in analysis['topics']:
                fig = create_statistics_visualization()
                visualization_type = "Statistik"
                description = "Visualisasi statistik: histogram, box plot, dan distribusi data"
            elif 'geometry' in analysis['topics']:
                fig = create_geometry_visualization()
                visualization_type = "Geometri"
                description = "Visualisasi geometri: lingkaran, segitiga, persegi, dan parabola"
            elif 'function' in analysis['topics']:
                fig = create_function_visualization()
                visualization_type = "Fungsi Matematika"
                description = "Visualisasi berbagai jenis fungsi: linear, kuadrat, eksponensial, dan logaritma"
            else:
                fig = create_function_visualization()
                visualization_type = "Fungsi Matematika"
                description = "Visualisasi default - berbagai jenis fungsi matematika"
            
            # Simpan gambar
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'visualization_{session_id[-8:]}_{timestamp}.png'
            filepath = os.path.join('static', filename)
            
            # Buat folder static jika belum ada
            os.makedirs('static', exist_ok=True)
            
            fig.savefig(filepath, dpi=150, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            plt.close(fig)
            
            return jsonify({
                'success': True,
                'image_path': f'/static/{filename}',
                'visualization_type': visualization_type,
                'description': description,
                'topics_detected': analysis['topics'],
                'data_points': len(analysis['numbers'])
            })
            
        except Exception as viz_error:
            # Fallback jika ada error dalam pembuatan visualisasi
            print(f"Visualization error: {viz_error}")
            fig = create_function_visualization()
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'visualization_fallback_{timestamp}.png'
            filepath = os.path.join('static', filename)
            os.makedirs('static', exist_ok=True)
            fig.savefig(filepath, dpi=150, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            plt.close(fig)
            
            return jsonify({
                'success': True,
                'image_path': f'/static/{filename}',
                'visualization_type': 'Fungsi Matematika (Fallback)',
                'description': 'Visualisasi fallback - fungsi matematika dasar',
                'topics_detected': [],
                'data_points': 0
            })
        
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': f'Error generating visualization: {str(e)}'
        })

@app.route('/static/<filename>')
def serve_static(filename):
    """Serve static files (visualizations)"""
    try:
        return send_file(os.path.join('static', filename))
    except Exception as e:
        return jsonify({'error': f'File not found: {str(e)}'}), 404

@app.route('/api/generate-visualization-popup', methods=['POST'])
def generate_visualization_popup():
    """Generate visualization and return popup URL"""
    try:
        data = request.get_json()
        api_provider = data.get('api_provider', 'claude')
        api_key = data.get('api_key')
        name = data.get('name', 'Siswa')
        subject = data.get('subject', 'Matematika')
        grade = data.get('grade', 'Kuliah')
        session_id = data.get('session_id', str(uuid.uuid4()))
        
        if not api_key:
            return jsonify({'success': False, 'error': 'API key required'})
        
        # Get conversation context
        conversation_context = conversations.get(session_id, [])
        context_text = "Ini adalah percakapan baru."
        if conversation_context:
            context_lines = []
            for entry in conversation_context[-6:]:  # Last 6 conversations
                context_lines.append(f"User: {entry['question']}")
                context_lines.append(f"AI: {entry['response'][:300]}...")  # Truncate for context
            context_text = "\n".join(context_lines)
        
        # Create visualization prompt
        if conversation_context and conversation_context != "Ini adalah percakapan baru.":
            recent_questions = [line for line in context_text.split('\n') if line.startswith('User:')]
            if recent_questions:
                latest_question = recent_questions[-1].replace('User: ', '').strip()
                context_analysis = f"""
KONTEKS PEMBICARAAN SEBELUMNYA:
{context_text}

TUGAS SPESIFIK: Buatkan visualisasi tentang "{latest_question}"

Berdasarkan konteks di atas, buatkan visualisasi HTML5 yang relevan dengan topik: "{latest_question}"
"""
            else:
                context_analysis = f"""
KONTEKS PEMBICARAAN SEBELUMNYA:
{context_text}

Berdasarkan konteks di atas, identifikasi topik/materi yang sedang dibahas dan buatkan visualisasi yang relevan.
"""
        else:
            context_analysis = f"""
Karena ini adalah percakapan baru, buatkan visualisasi {subject} tingkat {grade} yang umum dan fundamental.
"""
        
        prompt = f"""Kamu adalah MATA v2.0, asisten belajar yang membuat visualisasi interaktif.

{context_analysis}

🚨 ATURAN KHUSUS UNTUK VISUALISASI - WAJIB DIPATUHI:
- JANGAN berikan penjelasan, deskripsi, atau teks apapun
- HANYA generate PURE HTML5/CSS/JavaScript code
- Langsung mulai dengan <!DOCTYPE html>
- Format: Complete HTML document dengan <html>, <head>, <body>
- Include <title> dalam <head>
- Pastikan code bisa langsung dijalankan di browser
- JANGAN ada markdown, penjelasan, atau text lain
- JANGAN gunakan code fence (```)
- JANGAN ada kata-kata seperti "Berikut adalah visualisasi..."
- LANGSUNG HTML CODE SAJA!

CONTOH HTML5 VISUALIZATION (WAJIB DIIKUTI):

CONTOH 1 - Canvas untuk Grafik Fungsi:
<!DOCTYPE html>
<html>
<head><title>Function Graph</title></head>
<body>
<canvas id="function-graph" width="400" height="300" style="border: 1px solid #ccc; background: white;"></canvas>
<script>
const canvas = document.getElementById('function-graph');
const ctx = canvas.getContext('2d');
ctx.beginPath();
ctx.moveTo(50, 250);
ctx.lineTo(350, 50);
ctx.strokeStyle = '#e74c3c';
ctx.lineWidth = 2;
ctx.stroke();
ctx.fillText('f(x) = x²', 300, 40);
</script>
</body>
</html>

CONTOH 2 - SVG untuk Diagram Geometri:
<!DOCTYPE html>
<html>
<head><title>Geometry Diagram</title></head>
<body>
<svg width="400" height="300" style="border: 1px solid #ccc;">
<circle cx="200" cy="150" r="80" fill="none" stroke="#3498db" stroke-width="2"/>
<line x1="120" y1="150" x2="280" y2="150" stroke="#e74c3c" stroke-width="2"/>
<text x="200" y="140" text-anchor="middle" font-size="14">Radius = 80</text>
</svg>
</body>
</html>

WAJIB: Gunakan salah satu format di atas dan sesuaikan dengan topik yang dibahas!"""

        messages = [{'role': 'user', 'content': prompt}]
        
        answer, used_model = make_api_request(api_provider, api_key, messages)
        
        # Debug logging
        print(f"\n🔧 DEBUG: Popup Visualization API Response:")
        print(f"  - Response length: {len(answer)}")
        print(f"  - Contains DOCTYPE: {'<!DOCTYPE' in answer}")
        print(f"  - Contains <html>: {'<html>' in answer}")
        
        # Extract pure HTML code
        html_content = None
        if answer.strip().startswith('<!DOCTYPE html>'):
            html_content = answer.strip()
            print(f"✅ Pure HTML code detected!")
        else:
            # Try to extract HTML from response
            html_match = re.search(r'<!DOCTYPE html>.*</html>', answer, re.DOTALL)
            if html_match:
                html_content = html_match.group(0).strip()
                print(f"✅ HTML extracted from response!")
            else:
                print(f"❌ No HTML code found in response")
                return jsonify({
                    'success': False,
                    'error': 'AI did not generate valid HTML code'
                })
        
        # Generate unique filename for serving
        file_id = str(uuid.uuid4())[:8]
        filename = f"visualization_{file_id}.html"
        
        # Save to a permanent location for serving
        permanent_path = os.path.join(os.path.dirname(__file__), 'temp_visualizations', filename)
        os.makedirs(os.path.dirname(permanent_path), exist_ok=True)
        
        with open(permanent_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Save conversation
        save_conversation(session_id, f"Generate popup visualisasi {subject} tingkat {grade}", html_content, 'penjelasan')
        
        print(f"✅ Visualization saved as: {filename}")
        
        return jsonify({
            'success': True,
            'popup_url': f'http://localhost:8090/temp_visualizations/{filename}',
            'filename': filename,
            'model_used': used_model
        })
        
    except Exception as e:
        print(f"❌ Error in popup visualization: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error generating popup visualization: {str(e)}'
        })

@app.route('/temp_visualizations/<filename>')
def serve_visualization(filename):
    """Serve visualization HTML files"""
    try:
        file_path = os.path.join(os.path.dirname(__file__), 'temp_visualizations', filename)
        if os.path.exists(file_path):
            return send_file(file_path)
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/cleanup-visualization/<filename>', methods=['DELETE'])
def cleanup_visualization(filename):
    """Clean up visualization file"""
    try:
        file_path = os.path.join(os.path.dirname(__file__), 'temp_visualizations', filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"🗑️ Cleaned up visualization file: {filename}")
            return jsonify({'success': True, 'message': f'File {filename} deleted'})
        else:
            return jsonify({'success': False, 'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def cleanup_old_visualizations():
    """Clean up visualization files older than 1 hour"""
    try:
        temp_dir = os.path.join(os.path.dirname(__file__), 'temp_visualizations')
        if not os.path.exists(temp_dir):
            return
        
        current_time = datetime.now()
        for filename in os.listdir(temp_dir):
            if filename.endswith('.html'):
                file_path = os.path.join(temp_dir, filename)
                file_time = datetime.fromtimestamp(os.path.getctime(file_path))
                if (current_time - file_time).seconds > 3600:  # 1 hour
                    os.remove(file_path)
                    print(f"🗑️ Auto-cleaned old visualization: {filename}")
    except Exception as e:
        print(f"❌ Error in auto-cleanup: {str(e)}")

@app.route('/api/generate-problem', methods=['POST'])
def generate_problem():
    """Generate a problem based on conversation context and subject/grade"""
    try:
        data = request.get_json()
        api_provider = data.get('api_provider', 'claude')
        api_key = data.get('api_key')
        name = data.get('name', 'Siswa')
        subject = data.get('subject', 'Matematika')
        grade = data.get('grade', 'Kuliah')
        session_id = data.get('session_id')
        
        if not api_key:
            return jsonify({
                'success': False, 
                'error': 'API key diperlukan'
            })
        
        # Get conversation context for personalized problem generation
        conversation_context = get_conversation_history(session_id, limit=10)
        
        # Analyze conversation to extract topic/theme
        context_analysis = ""
        if conversation_context and conversation_context != "Ini adalah percakapan baru.":
            context_analysis = f"""
KONTEKS PEMBICARAAN SEBELUMNYA:
{conversation_context}

Berdasarkan konteks di atas, identifikasi topik/materi yang sedang dibahas dan buatkan soal yang relevan.
"""
        else:
            context_analysis = f"""
Karena ini adalah percakapan baru, buatkan soal {subject} tingkat {grade} yang umum dan fundamental.
"""
        
        # Create enhanced problem generation prompt
        prompt = f"""Kamu adalah MATA v2.0, asisten belajar yang membantu {name} belajar {subject} di tingkat {grade}.

{context_analysis}

TUGAS: Buatkan 1 soal {subject} tingkat {grade} yang relevan dengan konteks pembicaraan.

ATURAN KETAT:
- HANYA buat soal, TIDAK ada penyelesaian atau jawaban
- Soal harus sesuai dengan tingkat {grade}
- Soal harus relevan dengan topik yang sedang dibahas
- Gunakan format yang terstruktur dan jelas
- Sertakan prakata yang personal dan memotivasi

FORMAT JAWABAN WAJIB:
**Prakata Motivasi**
Baiklah {name}, untuk menambah pemahaman Anda dalam materi [nama_topik], saya berikan soal lainnya ya. Coba kerjakan soal berikut ini:

**Soal**
[Soal yang akan dibuat - HANYA soal, tidak ada jawaban]

**Petunjuk**
- Kerjakan dengan teliti
- Jika kesulitan, coba pikirkan langkah-langkah yang sudah kita pelajari sebelumnya
- Jangan ragu untuk bertanya jika ada yang tidak jelas

🚨 PERINGATAN LATeX CRITICAL - WAJIB DIPATUHI:
- WAJIB gunakan HANYA delimiter \(...\) dan \[...\]
- JANGAN gunakan dolar...dolar atau dolar dolar...dolar dolar - HANYA \( dan \[
- Inline math: \(formula\) (HANYA \( di awal dan \) di akhir)
- Display math: \[formula\] (HANYA \[ di awal dan \] di akhir)
- CONTOH BENAR: \(2x^3 - 3x - 1\), \(\int_0^2 x^2 dx\)
- JIKA MENGGUNAKAN $...$ MAKA JAWABAN AKAN DIREJECT!"""

        messages = [{'role': 'user', 'content': prompt}]
        
        answer, used_model = make_api_request(api_provider, api_key, messages)
        
        # Sanitize LaTeX delimiters in response
        sanitized_answer = sanitize_latex_delimiters(answer)
        
        save_conversation(session_id, f"Generate soal {subject} tingkat {grade} (contextual)", sanitized_answer, 'jawab_soal')
        
        return jsonify({
            'success': True, 
            'answer': sanitized_answer,
            'focus_mode': 'jawab_soal',
            'model_used': used_model,
            'provider': api_provider
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error generating problem: {str(e)}'
        })

@app.route('/api/conversation-stats', methods=['GET'])
def get_conversation_stats():
    """Get conversation statistics"""
    session_id = request.args.get('session_id')
    
    if session_id and session_id in conversations:
        return jsonify({
            'success': True,
            'conversation_count': len(conversations[session_id]),
            'session_id': session_id
        })
    else:
        return jsonify({
            'success': True,
            'conversation_count': 0,
            'session_id': session_id or 'new'
        })

@app.route('/api/clear-conversation', methods=['POST'])
def clear_conversation():
    """Clear conversation history"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        if session_id and session_id in conversations:
            del conversations[session_id]
        
        return jsonify({
            'success': True,
            'message': 'Conversation cleared successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error clearing conversation: {str(e)}'
        })

@app.route('/api/debug/latex', methods=['POST'])
def debug_latex():
    """Debug LaTeX processing endpoint"""
    try:
        data = request.get_json()
        text = data.get('text', '')
        
        # Test LaTeX delimiter detection
        import re
        
        # Find all LaTeX patterns
        inline_latex = re.findall(r'\$([^$]+)\$', text)
        display_latex = re.findall(r'\$\$([^$]+)\$\$', text)
        new_inline_latex = re.findall(r'\\\(([^)]+)\\\)', text)
        new_display_latex = re.findall(r'\\\[([^\]]+)\\\]', text)
        
        # Test sanitization
        sanitized = sanitize_latex_delimiters(text)
        
        return jsonify({
            'success': True,
            'debug_info': {
                'original_text': text,
                'sanitized_text': sanitized,
                'patterns_found': {
                    'inline_$': inline_latex,
                    'display_$$': display_latex,
                    'inline_\\(...\\)': new_inline_latex,
                    'display_\\[...\\]': new_display_latex
                },
                'counts': {
                    'dollar_signs_original': text.count('$'),
                    'dollar_signs_sanitized': sanitized.count('$'),
                    'backslash_parens': sanitized.count('\\('),
                    'backslash_brackets': sanitized.count('\\['),
                }
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Debug error: {str(e)}'
        })

@app.route('/api/debug/raw-response', methods=['POST'])
def debug_raw_response():
    """Debug raw API response endpoint"""
    try:
        data = request.get_json()
        api_provider = data.get('api_provider', 'claude')
        api_key = data.get('api_key')
        question = data.get('question', 'Test question')
        focus_mode = data.get('focus_mode', 'penjelasan')
        
        if not api_key:
            return jsonify({'success': False, 'error': 'API key required'})
        
        # Generate prompt
        prompt = create_enhanced_prompt(focus_mode, question, "Test User", "Matematika", "SMA", "auto", "No history")
        messages = [{'role': 'user', 'content': prompt}]
        
        # Make API request
        answer, used_model = make_api_request(api_provider, api_key, messages)
        
        return jsonify({
            'success': True,
            'debug_info': {
                'question': question,
                'focus_mode': focus_mode,
                'model_used': used_model,
                'raw_response': answer,
                'raw_response_repr': repr(answer),
                'response_length': len(answer),
                'contains_dollar': '$' in answer,
                'contains_backslash_parens': '\\(' in answer,
                'contains_backslash_brackets': '\\[' in answer,
                'dollar_count': answer.count('$'),
                'backslash_parens_count': answer.count('\\('),
                'backslash_brackets_count': answer.count('\\['),
                'character_by_character': [char for char in answer if char in '$\\()[]']
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Debug error: {str(e)}'
        })

@app.route('/api/debug/prompt', methods=['POST'])
def debug_prompt():
    """Debug prompt generation endpoint"""
    try:
        data = request.get_json()
        focus_mode = data.get('focus_mode', 'penjelasan')
        question = data.get('question', 'Test question')
        name = data.get('name', 'Test User')
        subject = data.get('subject', 'Matematika')
        grade = data.get('grade', 'Kuliah')
        level = data.get('level', 'auto')
        
        # Generate prompt
        prompt = create_enhanced_prompt(focus_mode, question, name, subject, grade, level, "No conversation history")
        
        return jsonify({
            'success': True,
            'debug_info': {
                'focus_mode': focus_mode,
                'question': question,
                'prompt_length': len(prompt),
                'prompt_preview': prompt[:500] + '...' if len(prompt) > 500 else prompt,
                'latex_delimiters_check': {
                    'contains_backslash_parens': '\\(' in prompt,
                    'contains_backslash_brackets': '\\[' in prompt,
                    'contains_dollar': '$' in prompt,
                    'backslash_parens_count': prompt.count('\\('),
                    'backslash_brackets_count': prompt.count('\\['),
                    'dollar_count': prompt.count('$')
                }
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Debug error: {str(e)}'
        })

@app.route('/api/debug/visualization-context', methods=['POST'])
def debug_visualization_context():
    """Debug visualization context analysis"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({
                'success': False,
                'error': 'session_id required'
            })
        
        analysis = analyze_conversation_for_visualization(session_id)
        
        return jsonify({
            'success': True,
            'debug_info': {
                'session_id': session_id,
                'analysis': analysis,
                'conversations_available': list(conversations.keys()),
                'session_exists': session_id in conversations,
                'conversation_length': len(conversations.get(session_id, []))
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Debug error: {str(e)}'
        })

if __name__ == '__main__':
    print("🚀 Starting MATA v2.5 Advanced AI Tutoring System...")
    print("📍 Frontend: http://localhost:8090")
    print("📍 Backend API: http://localhost:8090/api/")
    print("🔧 Debug Endpoints:")
    print("   📊 LaTeX Debug: POST http://localhost:8090/api/debug/latex")
    print("   📝 Prompt Debug: POST http://localhost:8090/api/debug/prompt")
    print("   🔍 Raw Response Debug: POST http://localhost:8090/api/debug/raw-response")
    print("🎨 Feature Endpoints:")
    print("   📈 Visualization: POST http://localhost:8090/api/generate-visualization")
    print("   📈 Popup Visualization: POST http://localhost:8090/api/generate-visualization-popup")
    print("   📝 Problem Generation: POST http://localhost:8090/api/generate-problem")
    print("✨ Features:")
    print("   🧠 Explicit Mode AI Selection (Penjelasan, Jawab Soal, Analisis)")
    print("   🎨 Stable Frontend with Backend API")
    print("   🔧 Advanced Feature Buttons (Visualisasi, Animasi, Generate Soal, Referensi)")
    print("   💾 Enhanced Conversation Memory")
    print("   📋 Mode-Based Structured Output")
    print("   🔄 Multiple API Provider Support")
    print("   📱 Mobile-Responsive Design")
    print("   ⚡ Upgradable AI Integration")
    print("   🔍 Enhanced LaTeX Processing with Debug Tools")
    print("   🛠️ MathJax with Multiple Delimiter Support")
    print("   🔧 LaTeX Sanitization & Protection")
    print("   🎯 Popup Visualization System")
    print("   🗑️ Auto-cleanup for temporary files")
    print("✅ System ready with comprehensive LaTeX debugging!")
    
    # Clean up old visualization files on startup
    cleanup_old_visualizations()
    
    # Get port from environment variable (for Railway/Heroku) or use default
    port = int(os.environ.get('PORT', 8090))
    # Disable debug mode in production
    debug_mode = os.environ.get('FLASK_ENV') != 'production'
    
    app.run(host='0.0.0.0', port=port, debug=debug_mode)