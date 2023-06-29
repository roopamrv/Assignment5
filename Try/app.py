import nltk
nltk.download('punkt')
nltk.download('stopwords')
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, TEXT, ID
from whoosh.qparser import QueryParser
import os

# Preprocessing steps
def preprocess(text):
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

# Create index
# def create_index(documents):
#     schema = Schema(content=TEXT(stored=True))
#     ix = create_in("index_dir", schema)
#     writer = ix.writer()

#     for doc_id, doc in enumerate(documents):
#         tokens = preprocess(doc)
#         content = " ".join(tokens)
#         writer.add_document(content=content, doc_id=str(doc_id))

#     writer.commit()

def create_index(file_path):
    # Read the contents of the text file
    with open(file_path, 'r', encoding='utf-8') as file:
        documents = file.readlines()

    # Create the index
    schema = Schema(doc_id=ID(stored=True, unique=True), content=TEXT(stored=True))
    ix = create_in("index_dir", schema)
    writer = ix.writer()

    for doc_id, doc in enumerate(documents):
        writer.add_document(doc_id=str(doc_id), content=doc.strip())

    writer.commit()
    
# Search documents
def search(query):
    ix = open_dir("index_dir")
    searcher = ix.searcher()
    query_parser = QueryParser("content", schema=ix.schema)
    parsed_query = query_parser.parse(query)
    results = searcher.search(parsed_query)

    for result in results:
        doc_id = int(result["doc_id"])
        print(f"Document ID: {doc_id}, Score: {result.score}")

# # Example usage
# documents = [
#     "The quick brown fox jumps over the lazy dog.",
#     "The dog is man's best friend.",
#     "Brown bears are native to North America.",
#     "Foxes are known for their cunning nature."
# ]

create_index("index_dir/gutenberg.org_cache_epub_71049_pg71049.txt")
search("United States")
