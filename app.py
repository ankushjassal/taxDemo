from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
from werkzeug.utils import secure_filename
import PyPDF2
import pytesseract
from pdf2image import convert_from_path
import re
import csv
import uuid
from datetime import datetime
from tax_calculator import calculate_tax_comparison
# from gemini_api_client import GeminiClient  # Placeholder for Gemini LLM
import json

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}

app = Flask(__name__, template_folder='templates')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'supersecretkey'  # For flash messages and session

# Utility to check allowed file
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# More flexible patterns for 80C and 80D
FIELD_PATTERNS = {
    'gross_salary': r'(gross salary|total gross|total earnings)[^\d]*(\d+[\d,\.]+)',
    'basic_salary': r'(basic salary|basic pay|basic)[^\d]*(\d+[\d,\.]+)',
    'hra_received': r'(hra received|house rent allowance|hra)[^\d]*(\d+[\d,\.]+)',
    'rent_paid': r'(rent paid|annual rent paid|rent)[^\d]*(\d+[\d,\.]+)',
    'deduction_80c': r'(80c[^\d\n]*[\:₹-]?[^\d\n]*|section 80c[^\d\n]*[\:₹-]?[^\d\n]*|deduction under 80c[^\d\n]*[\:₹-]?[^\d\n]*)(\d+[\d,\.]+)',
    'deduction_80d': r'(80d[^\d\n]*[\:₹-]?[^\d\n]*|section 80d[^\d\n]*[\:₹-]?[^\d\n]*|medical insurance[^\d\n]*[\:₹-]?[^\d\n]*|mediclaim[^\d\n]*[\:₹-]?[^\d\n]*)(\d+[\d,\.]+)',
    'standard_deduction': r'(standard deduction)[^\d]*(\d+[\d,\.]+)',
    'professional_tax': r'(professional tax)[^\d]*(\d+[\d,\.]+)',
    'tds': r'(tds|tax deducted at source)[^\d]*(\d+[\d,\.]+)',
}

def parse_fields_from_text(text):
    data = {}
    for field, pattern in FIELD_PATTERNS.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(len(match.groups())).replace(',', '')
            data[field] = value
        else:
            data[field] = ''
    # Default standard deduction if not found
    if not data['standard_deduction']:
        data['standard_deduction'] = '50000'
    # Default regime
    data['tax_regime'] = 'new'
    return data

# Stub for Gemini LLM structuring (now uses basic parsing)
def structure_data_with_gemini(text):
    return parse_fields_from_text(text)

# Gemini follow-up question (could be dynamic based on user data)
FOLLOWUP_QUESTION = "What are your main financial goals for the coming year? (e.g., buying a house, saving for retirement, children's education, etc.)"

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    with open("debug_log.txt", "a", encoding="utf-8") as f:
        f.write("UPLOAD ROUTE CALLED\n")
    if request.method == 'POST':
        if 'pdf_file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['pdf_file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            with open("debug_log.txt", "a", encoding="utf-8") as f:
                f.write(f"Saved file to: {filepath}\n")
                f.write("Calling extract_text_from_pdf...\n")
            # Extract text from PDF
            text = extract_text_from_pdf(filepath)
            with open("debug_log.txt", "a", encoding="utf-8") as f:
                f.write("extract_text_from_pdf finished.\n")
            # Structure data using Gemini (now basic parsing)
            data = structure_data_with_gemini(text)
            # Optionally, delete the file after extraction (or in next phase)
            # os.remove(filepath)
            return render_template('form.html', **data)
        else:
            flash('Invalid file type. Please upload a PDF.')
            return redirect(request.url)
    return render_template('index.html')

@app.route('/advisor', methods=['GET', 'POST'])
def advisor():
    ai_suggestion = None
    user_answer = ''
    if request.method == 'POST':
        user_answer = request.form.get('user_answer', '')
        # Call Gemini API or stub for personalized suggestions
        ai_suggestion = get_gemini_suggestion(user_answer)
        # Log conversation
        log_ai_conversation(FOLLOWUP_QUESTION, user_answer, ai_suggestion)
    return render_template('ask.html', question=FOLLOWUP_QUESTION, user_answer=user_answer, ai_suggestion=ai_suggestion)

def get_gemini_suggestion(user_answer):
    # Stub: In real implementation, call Gemini API here
    # For now, return a static suggestion based on answer
    if not user_answer.strip():
        return "Please provide more details about your financial goals."
    # Example: simple logic for demo
    if 'retirement' in user_answer.lower():
        return "Consider maximizing your 80C and NPS contributions for long-term retirement savings."
    if 'house' in user_answer.lower():
        return "Explore tax benefits on home loan principal (80C) and interest (Section 24)."
    if 'education' in user_answer.lower():
        return "Look into Section 80E for education loan interest deduction."
    return "Diversify your investments across tax-saving instruments like ELSS, PPF, and insurance. Review your 80C/80D utilization."

def log_ai_conversation(question, user_answer, ai_suggestion):
    log_entry = {
        "question": question,
        "user_answer": user_answer,
        "ai_suggestion": ai_suggestion
    }
    log_path = 'ai_conversation_log.json'
    try:
        if os.path.exists(log_path):
            with open(log_path, 'r', encoding='utf-8') as f:
                log_data = json.load(f)
        else:
            log_data = []
        log_data.append(log_entry)
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2)
    except Exception as e:
        print('Error logging AI conversation:', e)

def extract_text_from_pdf(pdf_path):
    text = ''
    try:
        # Try PyPDF2 first
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() or ''
        # If text is insufficient, use OCR
        if len(text.strip()) < 50:
            images = convert_from_path(pdf_path)
            for image in images:
                text += pytesseract.image_to_string(image)
    except Exception as e:
        with open("debug_log.txt", "a", encoding="utf-8") as f:
            f.write(f'Error extracting text: {e}\n')
    with open("debug_log.txt", "a", encoding="utf-8") as f:
        f.write('--- Extracted PDF Text Start ---\n')
        f.write(text + '\n')
        f.write('--- Extracted PDF Text End ---\n')
    return text

def save_to_csv(data, tax_result, selected_regime, user_csv='user_financials.csv', tax_csv='tax_comparison.csv'):
    session_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    # Write headers if file does not exist
    if not os.path.exists(user_csv):
        with open(user_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'session_id', 'gross_salary', 'basic_salary', 'hra_received', 'rent_paid',
                'deduction_80c', 'deduction_80d', 'standard_deduction', 'professional_tax', 'tds', 'created_at'
            ])
    if not os.path.exists(tax_csv):
        with open(tax_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'session_id', 'tax_old_regime', 'tax_new_regime', 'best_regime', 'selected_regime', 'created_at'
            ])
    # Save user financials
    with open(user_csv, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            session_id,
            data.get('gross_salary', ''),
            data.get('basic_salary', ''),
            data.get('hra_received', ''),
            data.get('rent_paid', ''),
            data.get('deduction_80c', ''),
            data.get('deduction_80d', ''),
            data.get('standard_deduction', ''),
            data.get('professional_tax', ''),
            data.get('tds', ''),
            now
        ])
    # Save tax comparison
    with open(tax_csv, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            session_id,
            tax_result['tax_old_regime'],
            tax_result['tax_new_regime'],
            tax_result['best_regime'],
            selected_regime,
            now
        ])

@app.route('/review', methods=['POST'])
def review():
    # Collect form data
    fields = [
        'gross_salary', 'basic_salary', 'hra_received', 'rent_paid',
        'deduction_80c', 'deduction_80d', 'standard_deduction',
        'professional_tax', 'tds', 'tax_regime'
    ]
    data = {field: request.form.get(field, '') for field in fields}
    selected_regime = data.get('tax_regime', 'new')
    # Calculate tax
    tax_result = calculate_tax_comparison(data)
    # Save to CSV instead of Supabase
    save_to_csv(data, tax_result, selected_regime)
    # Store results in session for /results
    session['tax_old_regime'] = tax_result['tax_old_regime']
    session['tax_new_regime'] = tax_result['tax_new_regime']
    session['best_regime'] = tax_result['best_regime']
    session['selected_regime'] = selected_regime
    # Render results
    return render_template(
        'results.html',
        tax_old_regime=tax_result['tax_old_regime'],
        tax_new_regime=tax_result['tax_new_regime'],
        best_regime=tax_result['best_regime'],
        selected_regime=selected_regime
    )

@app.route('/results', methods=['GET'])
def results():
    # Check if results are in session
    if not all(k in session for k in ['tax_old_regime', 'tax_new_regime', 'best_regime', 'selected_regime']):
        return redirect(url_for('index'))
    return render_template(
        'results.html',
        tax_old_regime=session['tax_old_regime'],
        tax_new_regime=session['tax_new_regime'],
        best_regime=session['best_regime'],
        selected_regime=session['selected_regime']
    )

if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True) 