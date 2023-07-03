import nltk
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, TEXT, ID
from whoosh.qparser import MultifieldParser, QueryParser, Operator
from whoosh.query import Or
import os
from flask import Flask, request, render_template
from werkzeug.utils import secure_filename
from bs4 import BeautifulSoup

app = Flask(__name__)
app.secret_key = 'your secret key'
dir_path = os.path.dirname(os.path.realpath(__file__)) + '/index_dir'
UPLOAD_FOLDER = dir_path
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() 

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


def get_line_numbers(doc_id, keywords):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], doc_id)
    line_numbers = []
    lines_sentence = []
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

        for line_number, line in enumerate(lines, start=1):
            for keyword in keywords:
                if keyword.lower() in line.lower():
                    line_numbers.append(line_number)
                    lines_sentence.append(line.strip())

    return line_numbers, lines_sentence


def get_line_text(line):
    soup = BeautifulSoup(line, 'html.parser')
    line_text = soup.get_text(separator=' ')
    return line_text


def search_documents(keywords):
    results = []

    ix = open_dir(app.config['UPLOAD_FOLDER'])
    searcher = ix.searcher()
    query_parser = QueryParser("content", schema=ix.schema)
    
    # Create a separate query for each keyword and combine them with OR operator
    queries = [query_parser.parse(keyword) for keyword in keywords]
    combined_query = Or(queries)

    search_results = searcher.search(combined_query)

    for result in search_results:
        doc_id = result['doc_id']
        score = result.score
        line_numbers, lines_sentence = get_line_numbers(doc_id, keywords)
        highlight = result.highlights("content", top=1)
        line_text = get_line_text(highlight)

        result = {
            'doc_id': doc_id,
            'score': score,
            'line_numbers': line_numbers,
            'lines_sentence': lines_sentence,
            'highlight': line_text
        }
        results.append(result)

    return results



@app.route('/search', methods=['POST'])
def search():
    keywords = request.form.get('key').split()
    print(keywords)
    results = search_documents(keywords)
    print(results)
    return render_template("result.html", results=results)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8587, debug=True)
