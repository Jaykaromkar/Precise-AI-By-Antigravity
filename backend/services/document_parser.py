import os
import tempfile
from langchain_community.document_loaders import PyPDFLoader, TextLoader, CSVLoader
try:
    from langchain_community.document_loaders import Docx2txtLoader
except ImportError:
    pass
from langchain_text_splitters import RecursiveCharacterTextSplitter

def parse_and_split_document(file_content: bytes, filename: str):
    file_type = filename.split('.')[-1].lower()
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_type}") as temp_file:
        temp_file.write(file_content)
        temp_filepath = temp_file.name

    try:
        if file_type == 'pdf':
            loader = PyPDFLoader(temp_filepath)
        elif file_type in ['docx', 'doc']:
            try:
                loader = Docx2txtLoader(temp_filepath)
            except NameError:
                raise ImportError("docx2txt is not installed but DOCX file provided.")
        elif file_type == 'txt':
            loader = TextLoader(temp_filepath)
        elif file_type == 'csv':
            loader = CSVLoader(temp_filepath)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
            
        docs = loader.load()
        
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = splitter.split_documents(docs)
        
        for idx, chunk in enumerate(chunks):
            chunk.metadata['chunk_id'] = idx
            chunk.metadata['filename'] = filename
        
        return chunks
    finally:
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)
