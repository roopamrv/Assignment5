import nltk
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, TEXT, ID
from whoosh.qparser import QueryParser
import os
from flask import Flask, request, render_template
from werkzeug.utils import secure_filename
from bs4 import BeautifulSoup
from difflib import SequenceMatcher

app = Flask(__name__)

app.secret_key = 'your secret key'

dir_path = os.path.dirname(os.path.realpath(__file__)) + '/index_dir'
UPLOAD_FOLDER = dir_path
# ALLOWED_EXTENSIONS = {'txt'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() 
# in ALLOWED_EXTENSIONS

def preprocess_data(text):
    # Tokenization
    tokens = nltk.word_tokenize(text)

    # Convert to lowercase
    tokens = [token.lower() for token in tokens]

    # Remove punctuation
    tokens = [token for token in tokens if token.isalnum()]

    # Remove stop words
    stop_words = set(stopwords.words('english'))
    tokens = [token for token in tokens if token not in stop_words]

    # Stemming
    stemmer = PorterStemmer()
    tokens = [stemmer.stem(token) for token in tokens]

    return tokens


def create_index(directory_path):
    schema = Schema(doc_id=ID(stored=True, unique=True), content=TEXT(stored=True, vector=True))
    ix = create_in(directory_path, schema)
    writer = ix.writer()

    for file_name in os.listdir(directory_path):
        file_path = os.path.join(directory_path, file_name)
        if os.path.isfile(file_path):
            with open(file_path, 'r', encoding='latin-1') as file:

                lines = file.readlines()

            for line_number, line in enumerate(lines):
                preprocessed_line = preprocess_data(line.strip())
                # print("PREPROCESSED LINE: ", preprocessed_line)
                writer.add_document(doc_id=str(file_name), content=' '.join(preprocessed_line))

    writer.commit()

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return '<h1>No file part</h1>'

    file = request.files['file']
    if file.filename == '':
        return '<h1>No selected file</h1>'

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        create_index("index_dir/")

        return '<h1>Successful</h1>'

    return '<h1>Unsuccessful</h1>'


def get_line_number(doc_id, keyword):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], doc_id)
    line_numbers = []
    lines_sentence = []
    ix = open_dir(app.config['UPLOAD_FOLDER'])
    searcher = ix.searcher()
    query_parser = QueryParser("doc_id", schema=ix.schema)
    parsed_query = query_parser.parse(doc_id)

    results = searcher.search(parsed_query, limit=1)
    
    if results:
        stored_doc = results[0]
        stored_lines = stored_doc['content'].split('\n')

        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

            for line_number, line in enumerate(lines, start=1):
                if keyword.lower() in line.lower():
                    line_numbers.append(line_number)
                    lines_sentence.append(line)

    return line_numbers,lines_sentence



def get_line_text(line):
    soup = BeautifulSoup(line, 'html.parser')
    line_text = soup.get_text(separator=' ')
    return line_text

def process_lines(lines):
    processed_lines = []
    for line in lines:
        line_text = get_line_text(line)
        processed_lines.append(line_text)
    return processed_lines

def search_documents(keyword):
    results = []

    ix = open_dir(app.config['UPLOAD_FOLDER'])
    print("IX: ",ix)
    searcher = ix.searcher()
    query_parser = QueryParser("content", schema=ix.schema)
    parsed_query = query_parser.parse(keyword)
    print("Parser query: ",parsed_query)
    search_results = searcher.search(parsed_query)

    print("inside searched documents")
    print("searched results:", search_results)

    preprocessed_line = []
    for result in search_results:
        print("Result: ",result)
        doc_id = result['doc_id']
        score = result.score
        print("DOC ID: ",doc_id)
        line_number, line= get_line_number(doc_id, keyword)
        
        result = {
            'doc_id': doc_id,
            'score': score,
            'line_number': line_number,
            'line': line
        }
        results.append(result)
    return results



@app.route('/search', methods=['POST'])
def search():
    keyword = str(request.form.get('key'))
    print("KEYWORD: ",keyword)
    results = search_documents(keyword)
    print("RESULTS:  ",results)
    return render_template("result.html", results=results)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8587, debug=True)